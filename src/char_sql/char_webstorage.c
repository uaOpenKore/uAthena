// Copyright (c) uAthena / bornrok.com
// [webstorage] Item requests from the web site (S. 2026-11-23): the site never writes the item tables; it puts a
// request into `web_storage_request` and the char-server carries it out when nothing in the game holds those items
// in memory, so a site action can neither duplicate nor lose an item (Doc/web_storage.md).
//
// Containers: inventory (char), cart (char, needs a cart), storage (Kafra, the account), guild_storage (the char's
// guild). Operations: move (src -> dst), add (a new item into dst: a site shop), remove (from src).
// A request runs only when
//  - the account is not on the server at all (in game, at the character select, an autotrade shop), when it
//    touches the char's inventory/cart or the account's storage: the map-server keeps those in memory then, and
//    no failed save of the account is pending here;
//  - nobody has the guild storage open, when it touches it: guild_storage_lock (inter_athena.conf) must be on, so
//    that the char-server knows it and a map-server reads the guild storage from the database on every open.
// Otherwise it waits (status 0) up to web_storage_wait seconds, then is refused (status 2, result says why).
// The source rows are taken first and the destination written after (a crash in between loses the items rather
// than duplicating them; the log line before has everything to put them back).
#include "../common/cbasetypes.h"
#include "../common/mmo.h"
#include "../common/timer.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "../common/sqlarchive.h"
#include "char.h"
#include "inter.h"
#include "itemdb.h"
#include "int_storage.h"
#include "char_webstorage.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// char.c / int_storage.c
int char_archive_account_busy(int account_id);
int char_webstorage_account_flush(int account_id);
int inter_guild_storage_ready(int guild_id);
int inter_storage_ready(int account_id);

static int ws_enabled = 1;
static int ws_interval = 3;    // seconds between runs
static int ws_batch = 20;      // requests per run
static int ws_wait = 600;      // seconds a busy request waits before it is refused
static bool ws_table = false;
static bool ws_autotrade = false; // the autotrade_shop table is there

int char_webstorage_config(const char* w1, const char* w2)
{
	if (strcmpi(w1, "web_storage") == 0) ws_enabled = atoi(w2);
	else if (strcmpi(w1, "web_storage_interval") == 0) ws_interval = atoi(w2);
	else if (strcmpi(w1, "web_storage_batch") == 0) ws_batch = atoi(w2);
	else if (strcmpi(w1, "web_storage_wait") == 0) ws_wait = atoi(w2);
	else return 0;
	return 1;
}

enum { C_NONE = -1, C_INV = 0, C_CART, C_STOR, C_GSTOR };
static const char* cont_names[] = { "inventory", "cart", "storage", "guild_storage" };
static int cont_of(const char* s)
{
	int i;
	if (s == NULL || !s[0])
		return C_NONE;
	for (i = 0; i < 4; i++)
		if (!strcmp(s, cont_names[i]))
			return i;
	return -2; // unknown name
}
static const char* cont_table(int c)
{
	return c == C_INV ? inventory_db : c == C_CART ? cart_db : c == C_STOR ? storage_db : guild_storage_db;
}
static const char* cont_owner_col(int c)
{
	return c == C_STOR ? "account_id" : c == C_GSTOR ? "guild_id" : "char_id";
}
static int cont_max(int c)
{
	return c == C_INV ? MAX_INVENTORY : c == C_CART ? MAX_CART : c == C_STOR ? MAX_STORAGE : MAX_GUILD_STORAGE;
}

static long long ws_ll(const char* q, long long def)
{
	MYSQL_RES* res;
	MYSQL_ROW row;
	long long v = def;
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return def;
	if ((row = mysql_fetch_row(res)) != NULL && row[0])
		v = strtoll(row[0], NULL, 10);
	mysql_free_result(res);
	return v;
}

void char_webstorage_init(void)
{
	char q[2048];
	if (!ws_enabled)
		return;
	snprintf(q, sizeof(q),
		"CREATE TABLE IF NOT EXISTS `web_storage_request` ("
		" `id` INT UNSIGNED NOT NULL AUTO_INCREMENT, `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,"
		" `account_id` INT UNSIGNED NOT NULL DEFAULT '0', `char_id` INT UNSIGNED NOT NULL DEFAULT '0',"
		" `op` VARCHAR(8) NOT NULL DEFAULT 'move', `src` VARCHAR(16) NOT NULL DEFAULT '', `dst` VARCHAR(16) NOT NULL DEFAULT '',"
		" `nameid` INT NOT NULL DEFAULT '0', `amount` INT NOT NULL DEFAULT '1', `identify` TINYINT NOT NULL DEFAULT '1',"
		" `refine` TINYINT UNSIGNED NOT NULL DEFAULT '0', `attribute` TINYINT UNSIGNED NOT NULL DEFAULT '0',"
		" `card0` SMALLINT NOT NULL DEFAULT '0', `card1` SMALLINT NOT NULL DEFAULT '0', `card2` SMALLINT NOT NULL DEFAULT '0', `card3` SMALLINT NOT NULL DEFAULT '0',"
		" `note` VARCHAR(255) NOT NULL DEFAULT '', `status` TINYINT NOT NULL DEFAULT '0', `result` VARCHAR(255) NOT NULL DEFAULT '',"
		" `done_at` DATETIME NULL, PRIMARY KEY (`id`), KEY `status` (`status`), KEY `account_id` (`account_id`)"
		") ENGINE=InnoDB");
	ws_table = sqlarc_query(&mysql_handle, q) != 0;
	if (!ws_table) {
		ShowError("[WEBSTORAGE] the table web_storage_request could not be made: web requests are off.\n");
		return;
	}
	ws_autotrade = sqlarc_table_exists(&mysql_handle, "autotrade_shop") != 0;
	add_timer_func_list(char_webstorage_timer, "char_webstorage_timer");
	add_timer_interval(gettick() + 10*1000, char_webstorage_timer, 0, 0, (ws_interval > 0 ? ws_interval : 3) * 1000);
	ShowStatus("[WEBSTORAGE] web item requests: every %d s, up to %d, busy ones wait %d s.\n", ws_interval, ws_batch, ws_wait);
}

struct ws_req {
	int id, account_id, char_id, op, src, dst, nameid, amount, identify, refine, attribute, card[4], age;
	char note[256];
};
enum { OP_MOVE, OP_ADD, OP_REMOVE };

static void ws_finish(const struct ws_req* r, int status, const char* result)
{
	char q[768], esc[520];
	mysql_real_escape_string(&mysql_handle, esc, result, (unsigned long)strnlen(result, 255));
	snprintf(q, sizeof(q), "UPDATE `web_storage_request` SET `status` = '%d', `result` = '%s', `done_at` = NOW() WHERE `id` = '%d' AND `status` = '0'",
		status, esc, r->id);
	sqlarc_query(&mysql_handle, q);
	ShowInfo("[WEBSTORAGE] req=%d %s aid=%d cid=%d %s->%s item=%d x%d refine=%d cards=%d,%d,%d,%d: %s%s\n", r->id,
		r->op == OP_MOVE ? "move" : r->op == OP_ADD ? "add" : "remove", r->account_id, r->char_id,
		r->src >= 0 ? cont_names[r->src] : "-", r->dst >= 0 ? cont_names[r->dst] : "-", r->nameid, r->amount, r->refine,
		r->card[0], r->card[1], r->card[2], r->card[3], status == 1 ? "done" : "REFUSED ", status == 1 ? "" : result);
}

static bool ws_stackable(int nameid)
{
	int t = itemdb_type(nameid);
	return !(t == IT_WEAPON || t == IT_ARMOR || t == IT_PETEGG || t == IT_PETARMOR);
}

// owner condition of a container: "`char_id` = '5'"
static void ws_owner(char* buf, size_t size, int c, int char_id, int account_id, int guild_id)
{
	snprintf(buf, size, "`%s` = '%d'", cont_owner_col(c), c == C_STOR ? account_id : c == C_GSTOR ? guild_id : char_id);
}

// the item's identity in a container (not its amount)
static void ws_match(char* buf, size_t size, const struct ws_req* r)
{
	snprintf(buf, size, "`nameid` = '%d' AND `identify` = '%d' AND `refine` = '%d' AND `attribute` = '%d' AND `card0` = '%d' AND `card1` = '%d'"
		" AND `card2` = '%d' AND `card3` = '%d'", r->nameid, r->identify, r->refine, r->attribute, r->card[0], r->card[1], r->card[2], r->card[3]);
}

// 1 = the container can take the item (slots, stack size); `why` says otherwise.
static int ws_fits(const struct ws_req* r, int c, const char* owner, const char* match, bool stack, char* why, size_t wsize)
{
	char q[1024];
	long long rows, have;
	snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s` WHERE %s", cont_table(c), owner);
	rows = ws_ll(q, -1);
	if (rows < 0) { snprintf(why, wsize, "database error"); return 0; }
	if (stack) {
		snprintf(q, sizeof(q), "SELECT COALESCE(MAX(`amount`),-1) FROM `%s` WHERE %s AND %s%s", cont_table(c), owner, match,
			c == C_INV ? " AND `equip` = 0" : "");
		have = ws_ll(q, -1);
		if (have >= 0 && have + r->amount <= MAX_AMOUNT)
			return 1; // onto the stack that is there
		if (have >= 0) { snprintf(why, wsize, "the stack in %s would exceed %d", cont_names[c], MAX_AMOUNT); return 0; }
		if (rows + 1 > cont_max(c)) { snprintf(why, wsize, "%s is full (%d slots)", cont_names[c], cont_max(c)); return 0; }
		return 1;
	}
	if (rows + r->amount > cont_max(c)) { snprintf(why, wsize, "%s has no room for %d more items (%d slots)", cont_names[c], r->amount, cont_max(c)); return 0; }
	return 1;
}

// Put the item into a container (after the source has given it up).
static int ws_put(const struct ws_req* r, int c, const char* owner_col_val_sql, const char* owner, const char* match, bool stack)
{
	char q[1536];
	int i;
	if (stack) {
		snprintf(q, sizeof(q), "SELECT `id` FROM `%s` WHERE %s AND %s%s ORDER BY `id` LIMIT 1", cont_table(c), owner, match, c == C_INV ? " AND `equip` = 0" : "");
		i = (int)ws_ll(q, 0);
		if (i > 0) {
			snprintf(q, sizeof(q), "UPDATE `%s` SET `amount` = `amount` + %d WHERE `id` = '%d'", cont_table(c), r->amount, i);
			return sqlarc_query(&mysql_handle, q);
		}
	}
	for (i = 0; i < (stack ? 1 : r->amount); i++) {
		snprintf(q, sizeof(q), "INSERT INTO `%s` (%s,`nameid`,`amount`,`identify`,`refine`,`attribute`,`card0`,`card1`,`card2`,`card3`) VALUES (%s,'%d','%d','%d','%d','%d','%d','%d','%d','%d')",
			cont_table(c), (c == C_STOR ? "`account_id`" : c == C_GSTOR ? "`guild_id`" : "`char_id`"), owner_col_val_sql,
			r->nameid, stack ? r->amount : 1, r->identify, r->refine, r->attribute, r->card[0], r->card[1], r->card[2], r->card[3]);
		if (!sqlarc_query(&mysql_handle, q))
			return 0;
	}
	return 1;
}

// Take the item out of a container. 1 = taken; `why` says otherwise.
static int ws_take(const struct ws_req* r, int c, const char* owner, const char* match, char* why, size_t wsize)
{
	char q[1536];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int ids[MAX_GUILD_STORAGE], amts[MAX_GUILD_STORAGE], n = 0, i, left;
	long long total = 0;
	// equipped (inventory) and rental items stay where they are
	snprintf(q, sizeof(q), "SELECT `id`, `amount` FROM `%s` WHERE %s AND %s%s%s ORDER BY `id`", cont_table(c), owner, match,
		c == C_INV ? " AND `equip` = 0" : "", " AND `expire_time` = 0");
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL) {
		snprintf(why, wsize, "database error");
		return 0;
	}
	while ((row = mysql_fetch_row(res)) != NULL && n < MAX_GUILD_STORAGE) {
		ids[n] = atoi(row[0]); amts[n] = atoi(row[1]);
		total += amts[n++];
	}
	mysql_free_result(res);
	if (total < r->amount) {
		snprintf(why, wsize, "%s has only %lld of that item (not equipped, not rented)", cont_names[c], total);
		return 0;
	}
	for (i = 0, left = r->amount; i < n && left > 0; i++) {
		if (amts[i] <= left) {
			snprintf(q, sizeof(q), "DELETE FROM `%s` WHERE `id` = '%d'", cont_table(c), ids[i]);
			left -= amts[i];
		} else {
			snprintf(q, sizeof(q), "UPDATE `%s` SET `amount` = `amount` - %d WHERE `id` = '%d'", cont_table(c), left, ids[i]);
			left = 0;
		}
		if (!sqlarc_query(&mysql_handle, q)) {
			snprintf(why, wsize, "database error while taking the item (%d of %d left untaken)", left, r->amount);
			return 0;
		}
	}
	return 1;
}

// 1 = done or refused (finished), 0 = busy (try again later)
static int ws_run(struct ws_req* r)
{
	char q[1024], owner_src[96], owner_dst[96], match[512], why[256] = "", val[32];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int acc = 0, guild = 0, option = 0, i;
	bool stack, touch_acc = false, touch_guild = false;
	struct item_data* id;

	if (r->op < 0) { ws_finish(r, 2, "unknown op (move, add, remove)"); return 1; }
	if (r->src == -2 || r->dst == -2) { ws_finish(r, 2, "unknown container (inventory, cart, storage, guild_storage)"); return 1; }
	if ((r->op == OP_MOVE && (r->src < 0 || r->dst < 0 || r->src == r->dst)) || (r->op == OP_ADD && r->dst < 0) || (r->op == OP_REMOVE && r->src < 0)) {
		ws_finish(r, 2, "src/dst do not fit the op"); return 1;
	}
	if (r->amount < 1 || r->amount > MAX_AMOUNT) { ws_finish(r, 2, "bad amount"); return 1; }
	id = itemdb_search(r->nameid);
	if (r->nameid <= 0 || id == NULL || !id->name[0] || !strcmp(id->name, "UNKNOWN_ITEM")) { ws_finish(r, 2, "no such item"); return 1; }
	stack = ws_stackable(r->nameid);
	if (!stack && r->amount > 100) { ws_finish(r, 2, "at most 100 non-stackable items in one request"); return 1; }
	if (stack && (r->refine || r->attribute)) { ws_finish(r, 2, "a stackable item has no refine/attribute"); return 1; }

	snprintf(q, sizeof(q), "SELECT `account_id`, `guild_id`, `option` FROM `%s` WHERE `char_id` = '%d'", char_db, r->char_id);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return 0;
	if ((row = mysql_fetch_row(res)) != NULL) { acc = atoi(row[0]); guild = atoi(row[1]); option = atoi(row[2]); }
	mysql_free_result(res);
	if (row == NULL) { ws_finish(r, 2, "no such character"); return 1; }
	if (acc != r->account_id) { ws_finish(r, 2, "the character is not on this account"); return 1; }
	for (i = 0; i < 2; i++) {
		int c = i == 0 ? r->src : r->dst;
		if (c < 0) continue;
		if (c == C_GSTOR) touch_guild = true; else touch_acc = true;
		if (c == C_GSTOR && guild <= 0) { ws_finish(r, 2, "the character is in no guild"); return 1; }
		if (c == C_CART && !(option & (0x08|0x80|0x100|0x200|0x400))) { ws_finish(r, 2, "the character has no cart"); return 1; }
	}
	if (touch_guild) {
		snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s` WHERE `guild_id` = '%d' AND `char_id` = '%d'", guild_member_db, guild, r->char_id);
		if (ws_ll(q, 0) != 1) { ws_finish(r, 2, "the character is not a member of its guild"); return 1; }
	}
	// busy: the game holds these items in memory
	if (touch_acc && (char_archive_account_busy(r->account_id) || !char_webstorage_account_flush(r->account_id) || !inter_storage_ready(r->account_id))) {
		snprintf(why, sizeof(why), "busy: the account is on the server (in game, at the character select or an autotrade shop)");
		goto busy;
	}
	// a kept autotrade shop sells from the cart even while it is not on the server (between a map-server's start and
	// the shop's restore): its account waits until the shop is closed
	if (touch_acc && ws_autotrade) {
		snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `autotrade_shop` WHERE `account_id` = '%d'", r->account_id);
		if (ws_ll(q, 1) != 0) {
			snprintf(why, sizeof(why), "busy: the account has an autotrade shop open");
			goto busy;
		}
	}
	if (touch_guild) {
		int g = inter_guild_storage_ready(guild);
		if (g < 0) { ws_finish(r, 2, "guild_storage_lock is off in inter_athena.conf: guild storage requests are not possible"); return 1; }
		if (g == 0) { snprintf(why, sizeof(why), "busy: the guild storage is open in the game"); goto busy; }
	}

	ws_match(match, sizeof(match), r);
	if (r->src >= 0) ws_owner(owner_src, sizeof(owner_src), r->src, r->char_id, r->account_id, guild);
	if (r->dst >= 0) {
		ws_owner(owner_dst, sizeof(owner_dst), r->dst, r->char_id, r->account_id, guild);
		if (!ws_fits(r, r->dst, owner_dst, match, stack, why, sizeof(why))) { ws_finish(r, 2, why); return 1; }
	}
	sqlarc_query(&mysql_handle, "START TRANSACTION");
	if (r->src >= 0 && !ws_take(r, r->src, owner_src, match, why, sizeof(why))) {
		sqlarc_query(&mysql_handle, "ROLLBACK");
		ws_finish(r, 2, why);
		return 1;
	}
	if (r->dst >= 0) {
		snprintf(val, sizeof(val), "'%d'", r->dst == C_STOR ? r->account_id : r->dst == C_GSTOR ? guild : r->char_id);
		if (!ws_put(r, r->dst, val, owner_dst, match, stack)) {
			sqlarc_query(&mysql_handle, "ROLLBACK");
			ShowError("[WEBSTORAGE] req=%d: the item could not be written to %s (rolled back where the tables allow it; check %s).\n",
				r->id, cont_names[r->dst], r->src >= 0 ? cont_names[r->src] : "-");
			ws_finish(r, 2, "database error while writing the item");
			return 1;
		}
	}
	sqlarc_query(&mysql_handle, "COMMIT");
	ws_finish(r, 1, "done");
	return 1;
busy:
	if (r->age >= ws_wait)
		ws_finish(r, 2, why);
	else { // still waiting: the site can show why
		char q2[512], esc[520];
		mysql_real_escape_string(&mysql_handle, esc, why, (unsigned long)strnlen(why, 255));
		snprintf(q2, sizeof(q2), "UPDATE `web_storage_request` SET `result` = '%s' WHERE `id` = '%d' AND `status` = '0'", esc, r->id);
		sqlarc_query(&mysql_handle, q2);
	}
	return 0;
}

int char_webstorage_timer(int tid, t_tick tick, intptr_t id, intptr_t data)
{
	char q[512];
	MYSQL_RES* res;
	MYSQL_ROW row;
	struct ws_req reqs[64];
	int n = 0, i, lim = ws_batch < 64 ? ws_batch : 64;

	if (!ws_table || !ws_enabled)
		return 0;
	snprintf(q, sizeof(q), "SELECT `id`,`account_id`,`char_id`,`op`,`src`,`dst`,`nameid`,`amount`,`identify`,`refine`,`attribute`,"
		"`card0`,`card1`,`card2`,`card3`,TIMESTAMPDIFF(SECOND,`created_at`,NOW()),`note` FROM `web_storage_request` WHERE `status` = '0' ORDER BY `id` LIMIT %d", lim);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return 0;
	while ((row = mysql_fetch_row(res)) != NULL && n < lim) {
		struct ws_req* r = &reqs[n++];
		memset(r, 0, sizeof(*r));
		r->id = atoi(row[0]); r->account_id = atoi(row[1]); r->char_id = atoi(row[2]);
		r->op = !strcmp(row[3], "move") ? OP_MOVE : !strcmp(row[3], "add") ? OP_ADD : !strcmp(row[3], "remove") ? OP_REMOVE : -1;
		r->src = cont_of(row[4]); r->dst = cont_of(row[5]);
		r->nameid = atoi(row[6]); r->amount = atoi(row[7]); r->identify = atoi(row[8]); r->refine = atoi(row[9]); r->attribute = atoi(row[10]);
		for (i = 0; i < 4; i++) r->card[i] = atoi(row[11 + i]);
		r->age = row[15] ? atoi(row[15]) : 0;
		snprintf(r->note, sizeof(r->note), "%s", row[16] ? row[16] : "");
	}
	mysql_free_result(res);
	for (i = 0; i < n; i++)
		ws_run(&reqs[i]);
	return 0;
}
