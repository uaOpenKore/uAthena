// Copyright (c) uAthena / bornrok.com
// [archive] Inactive accounts move into the archive tables, and come back on a login (S. 2026-11-22).
//
// Archiving (a timer, char_athena.conf account_archive_*): a player account (id >= START_ACCOUNT_NUM, not a
// server account) that has not logged in for account_archive_days -- or never did and was registered that long
// ago (login.created; no date = an account from before the column) -- and is not on this server now (in game,
// at the character select, an autotrade shop) is copied with its characters into arc_<table> (sqlarchive.h),
// then taken out of the live tables the way a character deletion does it: it leaves its party, a guild master's
// guild is broken (S.: no hand-over), a spouse is divorced, other players' friend lists drop it. GM and banned
// accounts too. Mode 1 only reports what it would archive.
//
// arc_index keeps one row per archiving: state 0 = copying (a crash: the copy is thrown away and done again),
// 1 = archived (a crash while removing: the removal is finished from the same copy), 2 = restored,
// 3 = restoring (a crash there is left for an admin: never restored twice).
//
// Restoring: the login-server finds a login name that is not in `login` in `arc_login`; with the right password it
// puts the account row back under a new account id and writes it to arc_login.arc_new_aid. When that account
// reaches the character select, char_archive_restore() brings its characters back -- new character, pet and
// homunculus ids, no guild, party or spouse -- with their items, skills, variables, quests, achievements and the
// account's storage, and rewrites the maker / pet ids in the restored items. Archived login names and character
// names stay taken (the registration and the character creation check the archive).
#include "../common/cbasetypes.h"
#include "../common/mmo.h"
#include "../common/timer.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "../common/sqlarchive.h"
#include "char.h"
#include "inter.h"
#include "int_guild.h"
#include "int_party.h"
#include "int_homun.h"
#include "int_mercenary.h"
#include "int_storage.h"
#include "char_archive.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

extern char login_db[256];
extern bool char_gm_read;
extern int login_server_port;
extern char login_server_ip[32], login_server_id[32], login_server_pw[32], login_server_db[32], default_codepage[32];
// The login database: the char-server's own login-DB connection when it reads the GM levels from it, else one
// of the archive's own (the `login` table may be in another database).
static MYSQL arc_login_mysql;
static MYSQL* LH = NULL;
extern char friend_db[256];
extern char hotkey_db[256];
extern int log_char;
// char.c
int char_archive_account_busy(int account_id);
void char_archive_forget_char(int char_id);
void char_read_fame_list(void);
int char_send_fame_list(int fd);

static int archive_mode = 1;        // 0 = off, 1 = report only, 2 = archive
static int archive_days = 365;
static int archive_hour = 5;        // local hour the runs happen in; -1 = any hour
static int archive_batch = 10;      // accounts per run
static int archive_interval = 60;   // seconds between runs
static int archive_report_day = -1; // mode 1 reports once a day
static bool login_has_created = false;
static bool archive_ready = false;

// Tables of the character database archived per character (WHERE char_id IN ...), and per account.
static const char* char_tables[] = { NULL /*char*/, NULL /*inventory*/, NULL /*cart*/, NULL /*skill*/, NULL /*memo*/,
	"hotkey", "friends", NULL /*quest*/, "achievement" };
#define N_CHAR_TABLES (int)(sizeof(char_tables) / sizeof(char_tables[0]))
static void archive_table_names(void)
{
	char_tables[0] = char_db; char_tables[1] = inventory_db; char_tables[2] = cart_db; char_tables[3] = skill_db;
	char_tables[4] = memo_db; char_tables[5] = hotkey_db; char_tables[6] = friend_db; char_tables[7] = quest_db;
}

int char_archive_config(const char* w1, const char* w2)
{
	if (strcmpi(w1, "account_archive_mode") == 0) archive_mode = atoi(w2);
	else if (strcmpi(w1, "account_archive_days") == 0) archive_days = atoi(w2);
	else if (strcmpi(w1, "account_archive_hour") == 0) archive_hour = atoi(w2);
	else if (strcmpi(w1, "account_archive_batch") == 0) archive_batch = atoi(w2);
	else if (strcmpi(w1, "account_archive_interval") == 0) archive_interval = atoi(w2);
	else return 0;
	return 1;
}

static int q_int(MYSQL* h, const char* q, int def)
{
	MYSQL_RES* res;
	MYSQL_ROW row;
	int v = def;
	if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL)
		return def;
	if ((row = mysql_fetch_row(res)) != NULL && row[0])
		v = atoi(row[0]);
	mysql_free_result(res);
	return v;
}

static void arc_where(char* buf, size_t size, int arc_no, const char* more)
{
	snprintf(buf, size, "`arc_no` = '%d'%s%s", arc_no, more ? " AND " : "", more ? more : "");
}

// Every archive table of the character database, plus arc_login: throw away one archiving's rows.
static void archive_drop_rows(int arc_no)
{
	char t[300], w[64];
	int i;
	static const char* other[] = { NULL /*storage*/, NULL /*reg*/, NULL /*pet*/, "homunculus", "skill_homunculus" };
	other[0] = storage_db; other[1] = reg_db; other[2] = pet_db;
	arc_where(w, sizeof(w), arc_no, NULL);
	for (i = 0; i < N_CHAR_TABLES; i++) {
		snprintf(t, sizeof(t), "arc_%s", char_tables[i]);
		sqlarc_delete(&mysql_handle, t, w);
	}
	for (i = 0; i < (int)(sizeof(other) / sizeof(other[0])); i++) {
		snprintf(t, sizeof(t), "arc_%s", other[i]);
		sqlarc_delete(&mysql_handle, t, w);
	}
	snprintf(t, sizeof(t), "arc_%s", login_db);
	sqlarc_delete(LH, t, w);
}

void char_archive_init(void)
{
	char q[1024], t[300];
	struct sqlarc_cols c;
	int i, ok = 1;
	static const char* other[] = { NULL, NULL, NULL, "homunculus", "skill_homunculus" };

	archive_table_names();
	if (char_gm_read)
		LH = &lmysql_handle;
	else {
		my_bool reconnect = 1;
		mysql_init(&arc_login_mysql);
		mysql_options(&arc_login_mysql, MYSQL_OPT_RECONNECT, &reconnect);
		if (!mysql_real_connect(&arc_login_mysql, login_server_ip, login_server_id, login_server_pw, login_server_db, login_server_port, NULL, 0)) {
			ShowError("[ARCHIVE] no connection to the login database (%s): archiving and restoring are off.\n", mysql_error(&arc_login_mysql));
			return;
		}
		LH = &arc_login_mysql;
		if (default_codepage[0]) {
			snprintf(q, sizeof(q), "SET NAMES %s", default_codepage);
			sqlarc_query(LH, q);
		}
	}
	other[0] = storage_db; other[1] = reg_db; other[2] = pet_db;
	login_has_created = sqlarc_get_cols(LH, login_db, &c) > 0 && sqlarc_has_col(&c, "created");

	snprintf(q, sizeof(q),
		"CREATE TABLE IF NOT EXISTS `arc_index` ("
		" `arc_no` INT UNSIGNED NOT NULL AUTO_INCREMENT, `account_id` INT UNSIGNED NOT NULL DEFAULT '0',"
		" `userid` VARCHAR(255) NOT NULL DEFAULT '', `lastlogin` VARCHAR(24) NOT NULL DEFAULT '',"
		" `archived_at` DATETIME NULL, `state` TINYINT NOT NULL DEFAULT '0', `new_aid` INT UNSIGNED NOT NULL DEFAULT '0',"
		" `restored_at` DATETIME NULL, `chars` VARCHAR(1024) NOT NULL DEFAULT '',"
		" PRIMARY KEY (`arc_no`), KEY `account_id` (`account_id`), KEY `userid` (`userid`), KEY `state` (`state`)"
		") ENGINE=InnoDB");
	ok &= sqlarc_query(&mysql_handle, q);
	for (i = 0; i < N_CHAR_TABLES; i++)
		if (sqlarc_table_exists(&mysql_handle, char_tables[i]))
			ok &= sqlarc_ensure(&mysql_handle, char_tables[i]);
	for (i = 0; i < (int)(sizeof(other) / sizeof(other[0])); i++)
		if (sqlarc_table_exists(&mysql_handle, other[i]))
			ok &= sqlarc_ensure(&mysql_handle, other[i]);
	ok &= sqlarc_ensure(LH, login_db);
	snprintf(t, sizeof(t), "arc_%s", login_db);
	if (ok && sqlarc_get_cols(LH, t, &c) > 0 && !sqlarc_has_col(&c, "arc_new_aid")) {
		snprintf(q, sizeof(q), "ALTER TABLE `%s` ADD COLUMN `arc_new_aid` INT UNSIGNED NOT NULL DEFAULT '0', ADD KEY `arc_new_aid` (`arc_new_aid`), ADD KEY `arc_userid` (`userid`)", t);
		ok &= sqlarc_query(LH, q);
	}
	archive_ready = ok != 0;
	if (!archive_ready)
		ShowError("[ARCHIVE] the archive tables could not be made: archiving and restoring are off.\n");
	if (archive_ready && archive_mode > 0 && archive_days > 0) {
		add_timer_func_list(char_archive_timer, "char_archive_timer");
		add_timer_interval(gettick() + 30*1000, char_archive_timer, 0, 0, (archive_interval > 0 ? archive_interval : 60) * 1000);
	}
	ShowStatus("[ARCHIVE] account archive: mode %d (%s), %d days, hour %d, %d accounts every %d s%s.\n", archive_mode,
		archive_mode == 2 ? "archive" : archive_mode == 1 ? "report only" : "off", archive_days, archive_hour,
		archive_batch, archive_interval, login_has_created ? "" : " (no login.created: never-logged-in accounts count as old)");
}

// The account's characters, for the log / arc_index ("Name/class/level, ...") and the id list ("1,2,3").
static int archive_chars(int account_id, char* names, size_t nsize, char* ids, size_t isize)
{
	char q[600];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int n = 0;
	size_t pn = 0, pi = 0;
	names[0] = ids[0] = '\0';
	snprintf(q, sizeof(q), "SELECT `char_id`,`name`,`class`,`base_level` FROM `%s` WHERE `account_id` = '%d'", char_db, account_id);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return -1;
	while ((row = mysql_fetch_row(res)) != NULL) {
		if (pn < nsize)
			pn += snprintf(names + pn, nsize - pn, "%s%s/%s/%s", n ? ", " : "", row[1], row[2], row[3]);
		if (pi < isize)
			pi += snprintf(ids + pi, isize - pi, "%s%s", n ? "," : "", row[0]);
		n++;
	}
	mysql_free_result(res);
	if (pn >= nsize) names[nsize - 1] = '\0';
	return n;
}

// Copy one account into the archive under arc_no. 1 = all copied.
static int archive_copy(int arc_no, int account_id, const char* ids)
{
	char w[2048], t[300], more[1536], ov[16];
	const char* over[] = { "arc_no", ov, NULL };
	int i;
	snprintf(ov, sizeof(ov), "'%d'", arc_no);

	snprintf(t, sizeof(t), "arc_%s", login_db);
	snprintf(w, sizeof(w), "`account_id` = '%d'", account_id);
	if (sqlarc_copy(LH, t, login_db, w, over, 0) < 0) return 0;
	snprintf(t, sizeof(t), "arc_%s", storage_db);
	if (sqlarc_copy(&mysql_handle, t, storage_db, w, over, 0) < 0) return 0;
	if (ids[0])
		snprintf(w, sizeof(w), "`account_id` = '%d' OR `char_id` IN (%s)", account_id, ids);
	snprintf(t, sizeof(t), "arc_%s", reg_db);
	if (sqlarc_copy(&mysql_handle, t, reg_db, w, over, 0) < 0) return 0;
	if (!ids[0])
		return 1;
	snprintf(w, sizeof(w), "`char_id` IN (%s)", ids);
	for (i = 0; i < N_CHAR_TABLES; i++) {
		snprintf(t, sizeof(t), "arc_%s", char_tables[i]);
		if (sqlarc_copy(&mysql_handle, t, char_tables[i], w, over, 0) < 0) return 0;
	}
	snprintf(t, sizeof(t), "arc_%s", pet_db);
	if (sqlarc_copy(&mysql_handle, t, pet_db, w, over, 0) < 0) return 0;
	if (sqlarc_copy(&mysql_handle, "arc_homunculus", "homunculus", w, over, 0) < 0) return 0;
	snprintf(more, sizeof(more), "`homun_id` IN (SELECT `homun_id` FROM `homunculus` WHERE `char_id` IN (%s))", ids);
	if (sqlarc_copy(&mysql_handle, "arc_skill_homunculus", "skill_homunculus", more, over, 0) < 0) return 0;
	return 1;
}

// Take one character out of the live tables (after its copy): what delete_char_sql does, without the pets and the
// homunculus going for good (they are in the archive). Returns its fame (> 0: the rankings are read again).
static int archive_remove_char(int account_id, int char_id)
{
	char q[512], w[64];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int party_id = 0, guild_id = 0, partner_id = 0, hom_id = 0, fame = 0, i;

	snprintf(q, sizeof(q), "SELECT `party_id`,`guild_id`,`partner_id`,`homun_id`,`fame` FROM `%s` WHERE `char_id` = '%d'", char_db, char_id);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return 0;
	if ((row = mysql_fetch_row(res)) != NULL) {
		party_id = atoi(row[0]); guild_id = atoi(row[1]); partner_id = atoi(row[2]); hom_id = atoi(row[3]); fame = atoi(row[4]);
	}
	mysql_free_result(res);
	if (row == NULL)
		return 0;

	if (partner_id) { // divorce: the spouse keeps playing alone (and loses the rings, as on a deletion)
		unsigned char buf[10];
		snprintf(q, sizeof(q), "UPDATE `%s` SET `partner_id` = '0' WHERE `char_id` = '%d'", char_db, partner_id);
		sqlarc_query(&mysql_handle, q);
		snprintf(q, sizeof(q), "DELETE FROM `%s` WHERE (`nameid` = '%d' OR `nameid` = '%d') AND `char_id` = '%d'", inventory_db, WEDDING_RING_M, WEDDING_RING_F, partner_id);
		sqlarc_query(&mysql_handle, q);
		WBUFW(buf,0) = 0x2b12;
		WBUFL(buf,2) = char_id;
		WBUFL(buf,6) = partner_id;
		mapif_sendall(buf, 10);
	}
	if (party_id)
		inter_party_leave(party_id, account_id, char_id);
	if (guild_id) {
		snprintf(q, sizeof(q), "SELECT 1 FROM `%s` WHERE `guild_id` = '%d' AND `char_id` = '%d'", guild_db, guild_id, char_id);
		if (q_int(&mysql_handle, q, 0) == 1)
			mapif_parse_BreakGuild(0, guild_id); // S. 2026-11-22: the master goes -> the guild is broken
		else
			inter_guild_leave(guild_id, account_id, char_id);
	}
	mercenary_owner_delete(char_id);
	if (hom_id)
		inter_delete_homunculus(hom_id);
	snprintf(q, sizeof(q), "DELETE FROM `homunculus` WHERE `char_id` = '%d'", char_id); // one no longer linked to the character
	sqlarc_query(&mysql_handle, q);
	snprintf(w, sizeof(w), "`friend_id` = '%d'", char_id); // other players' friend lists
	sqlarc_delete(&mysql_handle, friend_db, w);
	snprintf(w, sizeof(w), "`char_id` = '%d'", char_id);
	sqlarc_delete(&mysql_handle, pet_db, w);
	sqlarc_delete(&mysql_handle, scdata_db, w);
	sqlarc_delete(&mysql_handle, reg_db, w);
	for (i = N_CHAR_TABLES - 1; i >= 0; i--) // the char row (index 0) last
		sqlarc_delete(&mysql_handle, char_tables[i], w);
	char_archive_forget_char(char_id);
	return fame;
}

// Archive one account. 1 = archived, 0 = skipped / failed (tried again on a later run).
static int archive_account(int account_id, const char* userid, const char* lastlogin)
{
	char q[4096], names[1024], ids[1024], esc_uid[512], esc_names[2100];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int arc_no = 0, state = -1, nchars, fame = 0;

	if (char_archive_account_busy(account_id))
		return 0;
	snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `autotrade_shop` WHERE `account_id` = '%d'", account_id);
	if (sqlarc_table_exists(&mysql_handle, "autotrade_shop") && q_int(&mysql_handle, q, 1) != 0)
		return 0; // an autotrade shop is open (S.: offline players only)

	snprintf(q, sizeof(q), "SELECT `arc_no`,`state` FROM `arc_index` WHERE `account_id` = '%d' AND `state` IN (0,1) ORDER BY `arc_no` DESC LIMIT 1", account_id);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return 0;
	if ((row = mysql_fetch_row(res)) != NULL) { arc_no = atoi(row[0]); state = atoi(row[1]); }
	mysql_free_result(res);
	if (state == 0) { // an earlier copy did not finish: start over
		archive_drop_rows(arc_no);
		snprintf(q, sizeof(q), "DELETE FROM `arc_index` WHERE `arc_no` = '%d'", arc_no);
		sqlarc_query(&mysql_handle, q);
		state = -1;
	}
	if ((nchars = archive_chars(account_id, names, sizeof(names), ids, sizeof(ids))) < 0)
		return 0;
	if (state != 1) {
		mysql_real_escape_string(&mysql_handle, esc_uid, userid, (unsigned long)strnlen(userid, 255));
		mysql_real_escape_string(&mysql_handle, esc_names, names, (unsigned long)strlen(names));
		snprintf(q, sizeof(q), "INSERT INTO `arc_index` (`account_id`,`userid`,`lastlogin`,`archived_at`,`state`,`chars`) VALUES ('%d','%s','%s',NOW(),'0','%s')",
			account_id, esc_uid, lastlogin, esc_names);
		if (!sqlarc_query(&mysql_handle, q))
			return 0;
		arc_no = (int)mysql_insert_id(&mysql_handle);
		if (!archive_copy(arc_no, account_id, ids)) {
			ShowError("[ARCHIVE] aid=%d: the copy failed, the account stays (tried again later).\n", account_id);
			return 0;
		}
		snprintf(q, sizeof(q), "UPDATE `arc_index` SET `state` = '1' WHERE `arc_no` = '%d'", arc_no);
		if (!sqlarc_query(&mysql_handle, q))
			return 0;
	}
	// removal: the copy is complete; the login row goes last, so a crash before it finishes on a later run
	if (ids[0]) {
		char* p = ids;
		while (*p) {
			int cid = atoi(p);
			fame += archive_remove_char(account_id, cid);
			while (*p && *p != ',') p++;
			if (*p == ',') p++;
		}
	}
	inter_storage_delete(account_id);
	snprintf(q, sizeof(q), "`account_id` = '%d'", account_id);
	sqlarc_delete(&mysql_handle, reg_db, q);
	sqlarc_delete(&mysql_handle, scdata_db, q);
	sqlarc_delete(LH, login_db, q);
	if (fame > 0) {
		char_read_fame_list();
		char_send_fame_list(-1);
	}
	ShowInfo("[ARCHIVE] archived aid=%d userid='%s' lastlogin=%s chars=%d [%s] arc_no=%d\n", account_id, userid, lastlogin, nchars, names, arc_no);
	return 1;
}

int char_archive_timer(int tid, t_tick tick, intptr_t id, intptr_t data)
{
	char q[2048], cond[512];
	MYSQL_RES* res;
	MYSQL_ROW row;
	time_t now = time(NULL);
	struct tm* lt = localtime(&now);
	int done = 0, found = 0;

	if (!archive_ready || archive_mode <= 0 || archive_days <= 0)
		return 0;
	if (archive_hour >= 0 && lt->tm_hour != archive_hour)
		return 0;
	if (archive_mode == 1 && archive_report_day == lt->tm_yday)
		return 0;
	if (login_has_created)
		snprintf(cond, sizeof(cond), "(`lastlogin` > '0000-00-00 00:00:00' AND `lastlogin` < NOW() - INTERVAL %d DAY"
			" OR `lastlogin` = '0000-00-00 00:00:00' AND (`created` IS NULL OR `created` < NOW() - INTERVAL %d DAY))", archive_days, archive_days);
	else
		snprintf(cond, sizeof(cond), "`lastlogin` < NOW() - INTERVAL %d DAY", archive_days);
	snprintf(q, sizeof(q), "SELECT `account_id`,`userid`,`lastlogin` FROM `%s` WHERE `account_id` >= '%d' AND `sex` <> 'S' AND %s"
		" ORDER BY `lastlogin`, `account_id` LIMIT %d", login_db, START_ACCOUNT_NUM, cond, archive_batch * 4 + 4);
	if (!sqlarc_query(LH, q) || (res = mysql_store_result(LH)) == NULL)
		return 0;
	if (archive_mode == 1) {
		char names[1024], ids[1024];
		archive_report_day = lt->tm_yday;
		snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s` WHERE `account_id` >= '%d' AND `sex` <> 'S' AND %s", login_db, START_ACCOUNT_NUM, cond);
		ShowInfo("[ARCHIVE] report (mode 1, nothing is moved): %d accounts older than %d days would be archived.\n",
			q_int(LH, q, -1) /* res stays valid: q_int stores its own result */, archive_days);
		while ((row = mysql_fetch_row(res)) != NULL && found < archive_batch) {
			int aid = atoi(row[0]);
			int n = archive_chars(aid, names, sizeof(names), ids, sizeof(ids));
			ShowInfo("[ARCHIVE] would archive aid=%d userid='%s' lastlogin=%s chars=%d [%s]%s\n", aid, row[1], row[2], n, names,
				char_archive_account_busy(aid) ? " (online now: skipped)" : "");
			found++;
		}
		mysql_free_result(res);
		return 0;
	}
	{
		// the rows first: archiving queries the same connection
		int aids[64];
		char uids[64][NAME_LENGTH*2], lasts[64][24];
		int n = 0, i;
		while ((row = mysql_fetch_row(res)) != NULL && n < 64) {
			aids[n] = atoi(row[0]);
			snprintf(uids[n], sizeof(uids[n]), "%s", row[1]);
			snprintf(lasts[n], sizeof(lasts[n]), "%s", row[2]);
			n++;
		}
		mysql_free_result(res);
		for (i = 0; i < n && done < archive_batch; i++)
			done += archive_account(aids[i], uids[i], lasts[i]);
	}
	return 0;
}

// --- restore ---------------------------------------------------------------------------------------------------

struct arc_map { int old_id, new_id; };

// Rewrite the maker (card0 0x00FF/0x00FE, card2|card3<<16) and pet egg (card0 0xFF00, card1|card2<<16) ids of the
// restored items in `table` WHERE <owner>, by row id (one pass over the original values: an old id can equal
// another restored row's new id).
static void restore_card_ids(const char* table, const char* owner, const struct arc_map* chars, int nc, const struct arc_map* pets, int np)
{
	char q[512];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int ids[2048], c0[2048], c1[2048], c2[2048], c3[2048], n = 0, i, k;

	if (nc == 0 && np == 0)
		return;
	snprintf(q, sizeof(q), "SELECT `id`,`card0`,`card1`,`card2`,`card3` FROM `%s` WHERE %s AND `card0` IN (255,254,-256)", table, owner);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return;
	while ((row = mysql_fetch_row(res)) != NULL && n < 2048) {
		ids[n] = atoi(row[0]); c0[n] = atoi(row[1]); c1[n] = atoi(row[2]); c2[n] = atoi(row[3]); c3[n] = atoi(row[4]);
		n++;
	}
	mysql_free_result(res);
	for (i = 0; i < n; i++) {
		int lo, hi;
		if (c0[i] == -256) { // pet egg
			int pid = (c1[i] & 0xFFFF) | ((c2[i] & 0xFFFF) << 16);
			for (k = 0; k < np && pets[k].old_id != pid; k++)
				;
			if (k == np) continue;
			sqlarc_split_id(pets[k].new_id, &lo, &hi);
			snprintf(q, sizeof(q), "UPDATE `%s` SET `card1` = '%d', `card2` = '%d' WHERE `id` = '%d'", table, lo, hi, ids[i]);
		} else { // forged / brewed: the maker
			int cid = (c2[i] & 0xFFFF) | ((c3[i] & 0xFFFF) << 16);
			for (k = 0; k < nc && chars[k].old_id != cid; k++)
				;
			if (k == nc) continue;
			sqlarc_split_id(chars[k].new_id, &lo, &hi);
			snprintf(q, sizeof(q), "UPDATE `%s` SET `card2` = '%d', `card3` = '%d' WHERE `id` = '%d'", table, lo, hi, ids[i]);
		}
		sqlarc_query(&mysql_handle, q);
	}
}

// A free character name for a restored character whose name was taken meanwhile (a GM rename, the web site).
static void restore_free_name(const char* name, char* out, size_t size)
{
	char q[600], esc[NAME_LENGTH*2+1], base[NAME_LENGTH];
	int i;
	snprintf(out, size, "%s", name);
	for (i = 0; i < 100; i++) {
		jstrescapecpy(esc, out);
		snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s` WHERE `name` = '%s'", char_db, esc);
		if (q_int(&mysql_handle, q, 1) == 0)
			return;
		snprintf(base, sizeof(base) - 3, "%s", name);
		snprintf(out, size, "%s_%d", base, i + 1);
	}
}

void char_archive_restore(int account_id)
{
	char q[1024], t[300], w[256], ov_cid[16], ov_aid[16], ov_name[NAME_LENGTH*2+3], ov_no[16];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int arc_no = 0, nc = 0, np = 0, i;
	struct arc_map chars[MAX_CHARS], homs[MAX_CHARS], pets[64];
	int char_pet[MAX_CHARS], char_hom[MAX_CHARS];
	char cnames[MAX_CHARS][NAME_LENGTH];
	int nh = 0;

	if (!archive_ready)
		return;
	snprintf(t, sizeof(t), "arc_%s", login_db);
	snprintf(q, sizeof(q), "SELECT `arc_no` FROM `%s` WHERE `arc_new_aid` = '%d' LIMIT 1", t, account_id);
	if ((arc_no = q_int(LH, q, 0)) <= 0)
		return;
	snprintf(q, sizeof(q), "SELECT `state` FROM `arc_index` WHERE `arc_no` = '%d'", arc_no);
	if (q_int(&mysql_handle, q, -1) != 1) {
		ShowError("[ARCHIVE] aid=%d: arc_no=%d is not in the archived state (a restore broke off?): not restored again, see arc_index.\n", account_id, arc_no);
		return;
	}
	snprintf(q, sizeof(q), "UPDATE `arc_index` SET `state` = '3', `new_aid` = '%d' WHERE `arc_no` = '%d'", account_id, arc_no);
	if (!sqlarc_query(&mysql_handle, q))
		return;
	snprintf(ov_aid, sizeof(ov_aid), "'%d'", account_id);
	snprintf(ov_no, sizeof(ov_no), "%d", arc_no);

	snprintf(q, sizeof(q), "SELECT `char_id`,`name`,`pet_id`,`homun_id` FROM `arc_%s` WHERE `arc_no` = '%d' ORDER BY `char_num`", char_db, arc_no);
	if (!sqlarc_query(&mysql_handle, q) || (res = mysql_store_result(&mysql_handle)) == NULL)
		return;
	while ((row = mysql_fetch_row(res)) != NULL && nc < MAX_CHARS) {
		chars[nc].old_id = atoi(row[0]);
		snprintf(cnames[nc], NAME_LENGTH, "%s", row[1]);
		char_pet[nc] = atoi(row[2]);
		char_hom[nc] = atoi(row[3]);
		nc++;
	}
	mysql_free_result(res);

	for (i = 0; i < nc; i++) {
		char name[NAME_LENGTH], esc[NAME_LENGTH*2+1], more[96];
		const char* over_char[] = { "account_id", ov_aid, "name", ov_name, "guild_id", "0", "party_id", "0", "partner_id", "0",
			"online", "0", "pet_id", "0", "homun_id", "0", "father", "0", "mother", "0", "child", "0", NULL };
		const char* over_cid[] = { "char_id", ov_cid, NULL };
		const char* over_reg[] = { "char_id", ov_cid, "account_id", ov_aid, NULL };
		const char* over_pet[] = { "char_id", ov_cid, "account_id", ov_aid, NULL };
		int k, cid;
		restore_free_name(cnames[i], name, sizeof(name));
		jstrescapecpy(esc, name);
		snprintf(ov_name, sizeof(ov_name), "'%s'", esc);
		snprintf(more, sizeof(more), "`char_id` = '%d'", chars[i].old_id);
		arc_where(w, sizeof(w), arc_no, more);
		snprintf(t, sizeof(t), "arc_%s", char_db);
		if (sqlarc_copy(&mysql_handle, char_db, t, w, over_char, 1) != 1) {
			ShowError("[ARCHIVE] aid=%d: character %d (%s) could not be restored.\n", account_id, chars[i].old_id, cnames[i]);
			chars[i].new_id = 0;
			continue;
		}
		cid = chars[i].new_id = (int)mysql_insert_id(&mysql_handle);
		snprintf(ov_cid, sizeof(ov_cid), "'%d'", cid);
		for (k = 1; k < N_CHAR_TABLES; k++) { // items (new row ids), skills, memo points, hotkeys, friends, quests, achievements
			snprintf(t, sizeof(t), "arc_%s", char_tables[k]);
			sqlarc_copy(&mysql_handle, char_tables[k], t, w, over_cid, 1);
		}
		snprintf(more, sizeof(more), "`char_id` = '%d' AND `char_id` <> 0", chars[i].old_id);
		arc_where(w, sizeof(w), arc_no, more);
		snprintf(t, sizeof(t), "arc_%s", reg_db);
		sqlarc_copy(&mysql_handle, reg_db, t, w, over_reg, 0);
		// pets (each gets a new id), the hatched one goes back to the character
		snprintf(q, sizeof(q), "SELECT `pet_id` FROM `arc_%s` WHERE `arc_no` = '%d' AND `char_id` = '%d'", pet_db, arc_no, chars[i].old_id);
		if (sqlarc_query(&mysql_handle, q) && (res = mysql_store_result(&mysql_handle)) != NULL) {
			int olds[64], no = 0, j;
			while ((row = mysql_fetch_row(res)) != NULL && no < 64)
				olds[no++] = atoi(row[0]);
			mysql_free_result(res);
			for (j = 0; j < no && np < 64; j++) {
				snprintf(more, sizeof(more), "`pet_id` = '%d'", olds[j]);
				arc_where(w, sizeof(w), arc_no, more);
				snprintf(t, sizeof(t), "arc_%s", pet_db);
				if (sqlarc_copy(&mysql_handle, pet_db, t, w, over_pet, 1) != 1)
					continue;
				pets[np].old_id = olds[j];
				pets[np].new_id = (int)mysql_insert_id(&mysql_handle);
				if (char_pet[i] == olds[j]) {
					snprintf(q, sizeof(q), "UPDATE `%s` SET `pet_id` = '%d' WHERE `char_id` = '%d'", char_db, pets[np].new_id, cid);
					sqlarc_query(&mysql_handle, q);
				}
				np++;
			}
		}
		// the homunculus and its skills
		if (char_hom[i] > 0 && nh < MAX_CHARS) {
			snprintf(more, sizeof(more), "`homun_id` = '%d'", char_hom[i]);
			arc_where(w, sizeof(w), arc_no, more);
			if (sqlarc_copy(&mysql_handle, "homunculus", "arc_homunculus", w, over_cid, 1) == 1) {
				char ov_hom[16];
				const char* over_hom[] = { "homun_id", ov_hom, NULL };
				homs[nh].old_id = char_hom[i];
				homs[nh].new_id = (int)mysql_insert_id(&mysql_handle);
				snprintf(ov_hom, sizeof(ov_hom), "'%d'", homs[nh].new_id);
				sqlarc_copy(&mysql_handle, "skill_homunculus", "arc_skill_homunculus", w, over_hom, 0);
				snprintf(q, sizeof(q), "UPDATE `%s` SET `homun_id` = '%d' WHERE `char_id` = '%d'", char_db, homs[nh].new_id, cid);
				sqlarc_query(&mysql_handle, q);
				nh++;
			}
		}
		if (strcmp(name, cnames[i]))
			ShowWarning("[ARCHIVE] aid=%d: the name '%s' was taken: the restored character is '%s'.\n", account_id, cnames[i], name);
	}
	// the account's storage and variables
	{
		const char* over_aid[] = { "account_id", ov_aid, NULL };
		arc_where(w, sizeof(w), arc_no, NULL);
		snprintf(t, sizeof(t), "arc_%s", storage_db);
		sqlarc_copy(&mysql_handle, storage_db, t, w, over_aid, 1);
		arc_where(w, sizeof(w), arc_no, "`char_id` = 0");
		snprintf(t, sizeof(t), "arc_%s", reg_db);
		sqlarc_copy(&mysql_handle, reg_db, t, w, over_aid, 0);
	}
	// maker and pet ids in the restored items
	{
		char owner[1100];
		size_t p = 0;
		for (i = 0; i < nc; i++)
			if (chars[i].new_id > 0)
				p += snprintf(owner + p, sizeof(owner) - p, "%s%d", p ? "," : "`char_id` IN (", chars[i].new_id);
		if (p) {
			snprintf(owner + p, sizeof(owner) - p, ")");
			restore_card_ids(inventory_db, owner, chars, nc, pets, np);
			restore_card_ids(cart_db, owner, chars, nc, pets, np);
		}
		snprintf(owner, sizeof(owner), "`account_id` = '%d'", account_id);
		restore_card_ids(storage_db, owner, chars, nc, pets, np);
	}
	archive_drop_rows(arc_no);
	snprintf(q, sizeof(q), "UPDATE `arc_index` SET `state` = '2', `restored_at` = NOW() WHERE `arc_no` = '%d'", arc_no);
	sqlarc_query(&mysql_handle, q);
	ShowInfo("[ARCHIVE] restored aid=%d arc_no=%s: %d characters, %d pets, %d homunculi (new ids).\n", account_id, ov_no, nc, np, nh);
}

// Archived character names stay taken (a restore brings them back). `esc_name` is escaped for SQL.
int char_archive_name_taken(const char* esc_name)
{
	char q[600];
	if (!archive_ready)
		return 0;
	snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `arc_%s` WHERE `name` = '%s'", char_db, esc_name);
	return q_int(&mysql_handle, q, 0) > 0;
}
