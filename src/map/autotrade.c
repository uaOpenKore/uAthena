// Autotrade shops that survive a server restart (S. 2026-11-21).
//
// The map-server keeps every autotrade shop in at_db (char_id -> where it stands, its title, what it sells: cart
// slot, item id, amount, price) and writes each change at once: the autotrade_shop / autotrade_item tables (SQL,
// natural keys, no auto-increment) or save/autotrade.txt (TXT). The goods stay in the cart; a shop row only
// points at cart slots, so nothing exists twice. A shop is kept until it is sold out, closed, or its owner logs
// in; a shutdown or a crash keeps it. At start-up every kept shop is loaded "pending" and brought back one by
// one: the char-server loads the character without a login (0x2b25 -> 0x2b26), the map-server logs it in on the
// null session (fd 0) like an @autotrade one, and reopens the shop with what the cart still holds. At a clean
// shutdown the storage is rewritten from at_db, pending shops included. Autotraders are not online: the
// char-server is told (0x2b27) and keeps them out of char.online, its counts and the login-server.
#include "../common/cbasetypes.h"
#include "../common/db.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "../common/socket.h"
#include "../common/strlib.h"
#include "../common/timer.h"
#include "../common/mapindex.h"
#include "../common/lock.h"
#include "autotrade.h"
#include "map.h"
#include "chrif.h"
#include "clif.h"
#include "itemdb.h"
#include "pc.h"
#include "unit.h"
#include "vending.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct at_item {
	short slot;            // cart index
	int nameid;
	unsigned short amount;
	unsigned int price;
};

struct at_shop {
	int char_id, account_id, sex;
	char map[MAP_NAME_LENGTH_EXT];
	short x, y;
	unsigned char dir;
	char title[MESSAGE_SIZE];
	time_t opened;
	int count;
	struct at_item items[MAX_VENDING];
	bool pending;          // loaded at start-up, not brought back yet
	t_tick asked;          // when its character was asked from the char-server; 0 = not yet
	bool loading;          // its character came and is logging in (the shop opens in autotrade_restore_loaded)
	t_tick retry_at;       // the char-server said "busy": not asked again before this tick; 0 = no wait
	int busy;              // how many times it said so
};

static struct dbt* at_db = NULL;     // char_id -> struct at_shop
static bool at_on = false;      // the storage is there (SQL: the tables exist)
static bool at_final = false;   // shutting down: leaving autotraders keep their shop
static int at_inflight = 0;     // restore requests waiting for their 0x2b26
#define AT_RESTORE_MS 10        // the restore pipeline is topped up every 10 ms...
#define AT_WINDOW 20            // ...to this many requests at once (the char-server loads one character per request)
#define AT_REPLY_MS 15000       // a request without an answer for this long is given up (the shop stays kept)
#define AT_BUSY_MS 30000        // the account still in use (a map-server that went down): asked again this much later,
#define AT_BUSY_TRIES 30        // ...this many times (15 minutes); then the shop stays kept for the next start

#ifdef TXT_ONLY
static char autotrade_txt[] = "save/autotrade.txt";
#endif

static struct at_shop* at_get(int char_id) { return (struct at_shop*)idb_get(at_db, char_id); }

//------------------------------------------------------------------------------------------------------------
// storage
//------------------------------------------------------------------------------------------------------------
#ifndef TXT_ONLY
static bool at_query(const char* q)
{
	if (mysql_query(&mmysql_handle, q)) {
		ShowSQL("DB error - %s\n", mysql_error(&mmysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, q);
		return false;
	}
	return true;
}

static bool at_table_exists(const char* name)
{
	MYSQL_RES* res;
	bool found = false;
	sprintf(tmp_sql, "SHOW TABLES LIKE '%s'", name);
	if (!at_query(tmp_sql) || (res = mysql_store_result(&mmysql_handle)) == NULL)
		return false;
	found = mysql_fetch_row(res) != NULL;
	mysql_free_result(res);
	return found;
}

static void at_write_rows(struct at_shop* s)
{
	char title[MESSAGE_SIZE * 2 + 1], *p;
	int i;
	jstrescapecpy(title, s->title);
	sprintf(tmp_sql, "REPLACE INTO `autotrade_shop` (`char_id`,`account_id`,`sex`,`map`,`x`,`y`,`dir`,`title`,`opened`) "
		"VALUES ('%d','%d','%d','%s','%d','%d','%d','%s',FROM_UNIXTIME(%ld))",
		s->char_id, s->account_id, s->sex, s->map, s->x, s->y, s->dir, title, (long)s->opened);
	at_query(tmp_sql);
	sprintf(tmp_sql, "DELETE FROM `autotrade_item` WHERE `char_id`='%d'", s->char_id);
	at_query(tmp_sql);
	if (s->count <= 0)
		return;
	p = tmp_sql + sprintf(tmp_sql, "INSERT INTO `autotrade_item` (`char_id`,`cart_slot`,`nameid`,`amount`,`price`) VALUES ");
	for (i = 0; i < s->count; i++)
		p += sprintf(p, "%s('%d','%d','%d','%u','%u')", i ? "," : "", s->char_id, s->items[i].slot, s->items[i].nameid,
			s->items[i].amount, s->items[i].price);
	at_query(tmp_sql);
}
#else
static int at_write_file_sub(DBKey key, void* data, va_list ap)
{
	struct at_shop* s = (struct at_shop*)data;
	FILE* fp = va_arg(ap, FILE*);
	int i;
	char title[MESSAGE_SIZE];
	// the title is the last field of its line: tabs and line breaks would break the format
	for (i = 0; i < MESSAGE_SIZE && s->title[i]; i++)
		title[i] = (s->title[i] == '\t' || s->title[i] == '\n' || s->title[i] == '\r') ? ' ' : s->title[i];
	title[i < MESSAGE_SIZE ? i : MESSAGE_SIZE - 1] = '\0';
	fprintf(fp, "S\t%d\t%d\t%d\t%s\t%d\t%d\t%d\t%ld\t%s\n", s->char_id, s->account_id, s->sex, s->map, s->x, s->y, s->dir,
		(long)s->opened, title);
	for (i = 0; i < s->count; i++)
		fprintf(fp, "I\t%d\t%d\t%d\t%u\t%u\n", s->char_id, s->items[i].slot, s->items[i].nameid, s->items[i].amount,
			s->items[i].price);
	return 0;
}

static void at_write_file(void)
{
	int lock;
	FILE* fp = lock_fopen(autotrade_txt, &lock);
	if (fp == NULL) {
		ShowWarning("[AUTOTRADE] cannot write %s\n", autotrade_txt);
		return;
	}
	at_db->foreach(at_db, at_write_file_sub, fp);
	lock_fclose(fp, autotrade_txt, &lock);
}
#endif

// A shop changed (or is new): write it.
static void at_store(struct at_shop* s)
{
	if (!at_on)
		return;
#ifndef TXT_ONLY
	at_write_rows(s);
#else
	at_write_file();
#endif
}

// A shop is gone: forget it and remove it from the storage.
static void at_remove(int char_id, const char* why)
{
	struct at_shop* s = at_get(char_id);
	if (s == NULL)
		return;
	ShowInfo("[AUTOTRADE] shop of cid=%d removed (%s)\n", char_id, why);
	idb_remove(at_db, char_id);
	if (!at_on)
		return;
#ifndef TXT_ONLY
	sprintf(tmp_sql, "DELETE FROM `autotrade_item` WHERE `char_id`='%d'", char_id);
	at_query(tmp_sql);
	sprintf(tmp_sql, "DELETE FROM `autotrade_shop` WHERE `char_id`='%d'", char_id);
	at_query(tmp_sql);
#else
	at_write_file();
#endif
}

static struct at_shop* at_new(int char_id)
{
	struct at_shop* s = (struct at_shop*)aCalloc(1, sizeof(struct at_shop));
	s->char_id = char_id;
	idb_put(at_db, char_id, s);
	return s;
}

// The kept shops of the storage, all pending.
static int at_load(void)
{
	int n = 0;
#ifndef TXT_ONLY
	MYSQL_RES* res;
	MYSQL_ROW row;
	struct at_shop* s;
	if (!at_query("SELECT `char_id`,`account_id`,`sex`,`map`,`x`,`y`,`dir`,`title`,UNIX_TIMESTAMP(`opened`) FROM `autotrade_shop`") ||
		(res = mysql_store_result(&mmysql_handle)) == NULL)
		return 0;
	while ((row = mysql_fetch_row(res)) != NULL) {
		s = at_new(atoi(row[0]));
		s->account_id = atoi(row[1]);
		s->sex = atoi(row[2]);
		safestrncpy(s->map, row[3], sizeof(s->map));
		s->x = atoi(row[4]);
		s->y = atoi(row[5]);
		s->dir = atoi(row[6]);
		safestrncpy(s->title, row[7] ? row[7] : "", sizeof(s->title));
		s->opened = row[8] ? (time_t)strtoll(row[8], NULL, 10) : 0;
		s->pending = true;
		n++;
	}
	mysql_free_result(res);
	if (!at_query("SELECT `char_id`,`cart_slot`,`nameid`,`amount`,`price` FROM `autotrade_item` ORDER BY `char_id`,`cart_slot`") ||
		(res = mysql_store_result(&mmysql_handle)) == NULL)
		return n;
	while ((row = mysql_fetch_row(res)) != NULL) {
		if ((s = at_get(atoi(row[0]))) == NULL || s->count >= MAX_VENDING)
			continue;
		s->items[s->count].slot = atoi(row[1]);
		s->items[s->count].nameid = atoi(row[2]);
		s->items[s->count].amount = (unsigned short)atoi(row[3]);
		s->items[s->count].price = (unsigned int)strtoul(row[4], NULL, 10);
		s->count++;
	}
	mysql_free_result(res);
#else
	char line[512], mapname[MAP_NAME_LENGTH_EXT], title[MESSAGE_SIZE];
	int cid, aid, sex, x, y, dir, slot, nameid;
	unsigned int amount, price;
	long opened;
	struct at_shop* s;
	FILE* fp = fopen(autotrade_txt, "r");
	if (fp == NULL)
		return 0;
	while (fgets(line, sizeof(line), fp)) {
		title[0] = '\0';
		if (sscanf(line, "S\t%d\t%d\t%d\t%15[^\t]\t%d\t%d\t%d\t%ld\t%79[^\r\n]", &cid, &aid, &sex, mapname, &x, &y, &dir, &opened, title) >= 8) {
			s = at_new(cid);
			s->account_id = aid; s->sex = sex; safestrncpy(s->map, mapname, sizeof(s->map));
			s->x = x; s->y = y; s->dir = dir; s->opened = (time_t)opened;
			safestrncpy(s->title, title, sizeof(s->title));
			s->pending = true;
			n++;
		} else if (sscanf(line, "I\t%d\t%d\t%d\t%u\t%u", &cid, &slot, &nameid, &amount, &price) == 5) {
			if ((s = at_get(cid)) == NULL || s->count >= MAX_VENDING)
				continue;
			s->items[s->count].slot = slot; s->items[s->count].nameid = nameid;
			s->items[s->count].amount = (unsigned short)amount; s->items[s->count].price = price;
			s->count++;
		}
	}
	fclose(fp);
#endif
	return n;
}

// The shop as the session holds it now.
static void at_from_sd(struct at_shop* s, struct map_session_data* sd)
{
	int i, n = 0;
	s->account_id = sd->status.account_id;
	s->sex = sd->status.sex;
	safestrncpy(s->map, mapindex_id2name(sd->mapindex), sizeof(s->map));
	s->x = sd->bl.x;
	s->y = sd->bl.y;
	s->dir = (unsigned char)unit_getdir(&sd->bl);
	safestrncpy(s->title, sd->message, sizeof(s->title));
	for (i = 0; i < sd->vend_num && i < MAX_VENDING; i++) {
		short slot = sd->vending[i].index;
		if (sd->vending[i].amount < 1 || slot < 0 || slot >= MAX_CART || sd->status.cart[slot].nameid <= 0)
			continue;
		s->items[n].slot = slot;
		s->items[n].nameid = sd->status.cart[slot].nameid;
		s->items[n].amount = sd->vending[i].amount;
		s->items[n].price = sd->vending[i].value;
		n++;
	}
	s->count = n;
	s->pending = false;
}

//------------------------------------------------------------------------------------------------------------
// the shop's life
//------------------------------------------------------------------------------------------------------------
void autotrade_open(struct map_session_data* sd)
{
	struct at_shop* s;
	if (sd->vender_id == 0)
		return;
	chrif_autotrade_notonline(sd); // not online, but the char-server keeps the character taken
	if ((s = at_get(sd->status.char_id)) == NULL) {
		s = at_new(sd->status.char_id);
		s->opened = time(NULL);
	}
	at_from_sd(s, sd);
	at_store(s);
	ShowInfo("[AUTOTRADE] shop of '%s' (cid=%d) kept: %d item(s) on %s %d,%d\n", sd->status.name, sd->status.char_id,
		s->count, s->map, s->x, s->y);
}

void autotrade_sold(struct map_session_data* sd)
{
	struct at_shop* s = at_get(sd->status.char_id);
	if (s == NULL || s->pending)
		return;
	at_from_sd(s, sd);
	at_store(s);
}

// A character logs in on its own: a kept shop of it that is not back yet is dropped (the owner is playing).
void autotrade_owner_login(struct map_session_data* sd)
{
	struct at_shop* s = at_get(sd->status.char_id);
	if (s != NULL && s->pending && !s->asked)
		at_remove(sd->status.char_id, "the owner logged in");
}

void autotrade_quit(struct map_session_data* sd)
{
	if (at_final)
		return; // a shutdown: the shop stays kept
	if (at_get(sd->status.char_id) != NULL && !at_get(sd->status.char_id)->pending)
		at_remove(sd->status.char_id, sd->vender_id ? "the owner logged in" : "sold out or closed");
}

//------------------------------------------------------------------------------------------------------------
// restore
//------------------------------------------------------------------------------------------------------------
struct at_restore_round { t_tick tick; int asked, inflight, pending, timed_out; int ids[AT_WINDOW]; int n; };

static int at_restore_sub(DBKey key, void* data, va_list ap)
{
	struct at_shop* s = (struct at_shop*)data;
	struct at_restore_round* r = va_arg(ap, struct at_restore_round*);
	if (!s->pending || s->loading)
		return 0;
	if (s->asked) {
		if (DIFF_TICK(r->tick, s->asked) < AT_REPLY_MS) {
			r->inflight++;
			return 0;
		}
		ShowWarning("[AUTOTRADE] no answer for cid=%d from the char-server: kept, tried again at the next start\n", s->char_id);
		s->pending = false; // not this run; it stays in the storage
		r->timed_out++;
		return 0;
	}
	r->pending++;
	if (s->retry_at && DIFF_TICK(s->retry_at, r->tick) > 0)
		return 0; // waiting for the account to be free
	if (r->n < AT_WINDOW)
		r->ids[r->n++] = s->char_id;
	return 0;
}

static int at_restore_timer(int tid, t_tick tick, intptr_t id, intptr_t data)
{
	struct at_restore_round r;
	struct at_shop* s;
	int i;
	static bool announced = false;
	if (announced || !chrif_isconnected())
		return 0;
	memset(&r, 0, sizeof(r));
	r.tick = tick;
	at_db->foreach(at_db, at_restore_sub, &r);
	at_inflight = r.inflight;
	for (i = 0; i < r.n && at_inflight < AT_WINDOW; i++) {
		if ((s = at_get(r.ids[i])) == NULL)
			continue;
		if (map_id2sd(s->account_id) != NULL) { // the owner (or another char of the account) is already in
			at_remove(r.ids[i], "the account is online");
			continue;
		}
		s->asked = tick;
		at_inflight++;
		chrif_autotrade_load(s->account_id, s->char_id, s->sex);
	}
	if (r.pending == 0 && r.inflight == 0 && !announced) {
		announced = true;
		ShowStatus("[AUTOTRADE] restore done.\n");
	}
	return 0;
}

void autotrade_restore_start(void)
{
	static bool started = false;
	int n;
	if (started || !at_on)
		return;
	started = true;
	n = at_load();
	if (n > 0)
		ShowStatus("[AUTOTRADE] %d kept shop(s) to bring back.\n", n);
	add_timer_func_list(at_restore_timer, "at_restore_timer");
	add_timer_interval(gettick() + AT_RESTORE_MS, at_restore_timer, 0, 0, AT_RESTORE_MS);
}

// 0x2b26 <len>.W <account id>.L <char id>.L <ok>.B <mmo_charstatus>
void autotrade_restore_ack(int fd)
{
	int aid = RFIFOL(fd,4), cid = RFIFOL(fd,8), ok = RFIFOB(fd,12);
	struct at_shop* s = at_get(cid);
	struct mmo_charstatus st;
	struct map_session_data* sd;

	if (s == NULL || !s->pending || !s->asked)
		return;
	s->asked = 0;
	if (ok == 2) { // the account is still in use (S. 2026-11-24: removed outright after a map-server crash before)
		if (++s->busy > AT_BUSY_TRIES) {
			ShowWarning("[AUTOTRADE] shop of cid=%d: account %d still in use after %d tries -- kept for the next start\n",
				cid, aid, AT_BUSY_TRIES);
			s->pending = false; // not this run; it stays in the storage
			return;
		}
		s->retry_at = gettick() + AT_BUSY_MS;
		ShowInfo("[AUTOTRADE] shop of cid=%d: account %d in use, asking again in %d s (try %d)\n", cid, aid,
			AT_BUSY_MS / 1000, s->busy);
		return;
	}
	s->loading = true;
	if (ok != 1 || RFIFOW(fd,2) != 13 + sizeof(struct mmo_charstatus)) {
		at_remove(cid, ok == 1 ? "bad answer" : "the char-server has no such character");
		return;
	}
	if (map_id2sd(aid) != NULL) {
		at_remove(cid, "the account is online");
		return;
	}
	memcpy(&st, RFIFOP(fd,13), sizeof(st));
	st.last_point.map = mapindex_name2id(s->map); // the shop's place
	st.last_point.x = s->x;
	st.last_point.y = s->y;
	st.sex = s->sex;

	CREATE(sd, TBL_PC, 1);
	sd->fd = 0; // the null session, like an @autotrade one
	sd->packet_ver = clif_default_packet_ver();
	pc_setnewpc(sd, aid, cid, 0, 0, s->sex, 0);
	sd->state.autotrade = 1;
	sd->state.at_restoring = 1; // the shop opens in autotrade_restore_loaded, once the registries are in
	if (pc_authok(sd, 0, 0, &st)) {
		at_remove(cid, "could not log the character in");
		map_quit(sd);
		return;
	}
}

// pc_reg_received of a restored autotrader: on the map, and the shop opens again.
void autotrade_restore_loaded(struct map_session_data* sd)
{
	struct at_shop* s = at_get(sd->status.char_id);
	int i, n = 0;
	sd->state.at_restoring = 0;
	sd->state.connect_new = 1;
	clif_parse_LoadEndAck(0, sd); // there is no client: put it on the map as its LoadEndAck would
	if (s == NULL) {
		map_quit(sd);
		return;
	}
	for (i = 0; i < s->count; i++) {
		struct at_item* it = &s->items[i];
		struct item* c;
		if (it->slot < 0 || it->slot >= MAX_CART)
			continue;
		c = &sd->status.cart[it->slot];
		if (c->nameid != it->nameid || c->amount < 1 || c->expire_time ||
			!itemdb_cantrade(c, pc_isGM(sd), pc_isGM(sd)))
			continue; // the cart changed while the server was down: that item is not sold any more
		sd->vending[n].index = it->slot;
		sd->vending[n].amount = it->amount > c->amount ? c->amount : it->amount;
		sd->vending[n].value = it->price;
		n++;
	}
	if (n == 0) {
		ShowInfo("[AUTOTRADE] shop of '%s' (cid=%d) not reopened: nothing of it left in the cart\n", sd->status.name, sd->status.char_id);
		s->pending = false;
		at_remove(sd->status.char_id, "nothing left to sell");
		map_quit(sd);
		return;
	}
	sd->vend_num = n;
	sd->vender_id = sd->bl.id;
	safestrncpy(sd->message, s->title, MESSAGE_SIZE);
	unit_setdir(&sd->bl, s->dir);
	clif_showvendingboard(&sd->bl, sd->message, 0);
	at_from_sd(s, sd); // what is really sold now (s->pending = false)
	at_store(s);
	chrif_autotrade_notonline(sd);
	ShowInfo("[AUTOTRADE] shop of '%s' (cid=%d) back on %s %d,%d with %d item(s)\n", sd->status.name, sd->status.char_id,
		s->map, s->x, s->y, n);
}

//------------------------------------------------------------------------------------------------------------
// init / final
//------------------------------------------------------------------------------------------------------------
void do_init_autotrade(void)
{
	at_db = db_alloc(__FILE__, __LINE__, DB_INT, DB_OPT_RELEASE_DATA, sizeof(int));
#ifndef TXT_ONLY
	at_on = at_table_exists("autotrade_shop") && at_table_exists("autotrade_item");
	if (!at_on)
		ShowWarning("[AUTOTRADE] keeping autotrade shops over a restart is OFF: the tables `autotrade_shop`/`autotrade_item` "
			"are missing (run sql-files/upgrade_2026-11-21_autotrade.sql).\n");
#else
	at_on = true;
#endif
}

static int at_refresh_sub(DBKey key, void* data, va_list ap)
{
	struct map_session_data* sd = (struct map_session_data*)data;
	struct at_shop* s;
	if (sd->state.autotrade && sd->vender_id && (s = at_get(sd->status.char_id)) != NULL)
		at_from_sd(s, sd);
	return 0;
}

static int at_count_sub(DBKey key, void* data, va_list ap)
{
	struct at_shop* s = (struct at_shop*)data;
	int* shops = va_arg(ap, int*);
	int* items = va_arg(ap, int*);
	(*shops)++;
	*items += s->count;
#ifndef TXT_ONLY
	at_write_rows(s);
#endif
	return 0;
}

// A clean shutdown: the storage is rewritten from the shops as they are now (pending ones included), so a
// change that did not reach it is not lost, and nothing else is left in it.
void do_final_autotrade(void)
{
	int shops = 0, items = 0;
	at_final = true;
	if (at_db == NULL)
		return;
	if (at_on) {
		map_foreachpc(at_refresh_sub);
#ifndef TXT_ONLY
		at_query("DELETE FROM `autotrade_item`");
		at_query("DELETE FROM `autotrade_shop`");
#endif
		at_db->foreach(at_db, at_count_sub, &shops, &items);
#ifdef TXT_ONLY
		at_write_file();
#endif
		ShowStatus("[AUTOTRADE] saved %d shop%s, %d item%s\n", shops, shops == 1 ? "" : "s", items, items == 1 ? "" : "s");
	}
}

void do_final_autotrade_db(void)
{
	if (at_db)
		at_db->destroy(at_db, NULL);
	at_db = NULL;
}
