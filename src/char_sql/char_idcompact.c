// Copyright (c) uAthena / bornrok.com
// [idcompact] At the char-server's start, before anything is loaded and before any server or player can connect,
// the ids freed by deletions and the archive are reused: every id kind is renumbered densely from its first
// number in its old order, and every column that holds such an id is rewritten (S. 2026-11-22: after the monthly
// reboot, "move the ids into the freed places, then lower AUTO_INCREMENT").
//
// Kinds: accounts (from START_ACCOUNT_NUM; the server accounts below it stay), characters, guilds, parties, pets,
// homunculi, mercenaries, and the row ids of the item tables and the memo points. The columns are found in the
// schema by name (any table but the logs, the archive and these helper tables), so a table added later is not
// forgotten; the maker of forged/brewed items (card2/card3) and the pet of an egg (card1/card2) are rewritten in
// every table with card columns. Rows that point at an id that no longer exists (left over by old deletions)
// would end up on another player after the move: a reference column (spouse, family, party leader, a guild's
// castle, a pet's owner...) is set to 0, any other such row is deleted -- unless there are many (then nothing is
// changed, see the log). Then AUTO_INCREMENT goes to MAX+1.
// Mode (char_athena.conf id_compact_mode): 0 = off, 1 = only log what it would do, 2 = do it.
//
// The updates run in ascending id order: a dense renumbering only lowers ids (new <= old), so a row never takes
// an id another row still has (primary keys stay unique all the way).
#include "../common/cbasetypes.h"
#include "../common/mmo.h"
#include "../common/showmsg.h"
#include "../common/malloc.h"
#include "../common/strlib.h"
#include "../common/sqlarchive.h"
#include "char.h"
#include "inter.h"
#include "char_archive.h"
#include "char_idcompact.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern char login_db[256];
extern int login_server_port, char_server_port;
extern char login_server_ip[32], char_server_ip[32];

static int compact_mode = 1;
static int compact_orphan_max = 0; // > 0: more rows pointing at missing ids than this and nothing is changed

int char_idcompact_config(const char* w1, const char* w2)
{
	if (strcmpi(w1, "id_compact_mode") == 0) compact_mode = atoi(w2);
	else if (strcmpi(w1, "id_compact_orphan_max") == 0) compact_orphan_max = atoi(w2);
	else return 0;
	return 1;
}

enum { CARDS_NONE, CARDS_MAKER, CARDS_EGG };
struct idkind {
	const char* name;     // log name and helper table suffix (idc_<name>)
	const char* table;    // the table the ids live in
	const char* pk;       // their column
	int base;             // first number (accounts: ids below it are not moved)
	bool keep_below;      // accounts: the server accounts below base keep their ids
	bool in_login_db;     // the table is in the login database
	const char* refs[8];  // the column names that hold this kind's ids anywhere ("" = only table.pk)
	int cards;
	// filled in:
	int total, moved, max_old, max_new;
};
static struct idkind kinds[] = {
	{ "acc", NULL /*login*/, "account_id", START_ACCOUNT_NUM, true, true, { "account_id", "friend_account", "leader_id", "arc_new_aid", "new_aid" }, CARDS_NONE },
	{ "chr", NULL /*char*/, "char_id", START_CHAR_NUM, false, false, { "char_id", "partner_id", "father", "mother", "child", "friend_id", "leader_char" }, CARDS_MAKER },
	{ "gld", "guild", "guild_id", 1, false, false, { "guild_id", "alliance_id" }, CARDS_NONE },
	{ "pty", "party", "party_id", 1, false, false, { "party_id" }, CARDS_NONE },
	{ "pet", "pet", "pet_id", 1, false, false, { "pet_id" }, CARDS_EGG },
	{ "hom", "homunculus", "homun_id", 1, false, false, { "homun_id" }, CARDS_NONE },
	{ "mer", "mercenary", "mer_id", 1, false, false, { "mer_id", "merc_id" }, CARDS_NONE },
	// row ids: nothing refers to them
	{ "inv", NULL /*inventory*/, "id", 1, false, false, { "" }, CARDS_NONE },
	{ "crt", NULL /*cart*/, "id", 1, false, false, { "" }, CARDS_NONE },
	{ "sto", NULL /*storage*/, "id", 1, false, false, { "" }, CARDS_NONE },
	{ "gst", NULL /*guild storage*/, "id", 1, false, false, { "" }, CARDS_NONE },
	{ "mem", NULL /*memo*/, "memo_id", 1, false, false, { "" }, CARDS_NONE },
};
#define N_KINDS (int)(sizeof(kinds) / sizeof(kinds[0]))

// "table.column" (or ".column": any table) whose dangling ids are set to 0 instead of deleting the row.
static const char* zero_refs[] = { ".partner_id", ".father", ".mother", ".child", ".leader_id", ".leader_char",
	"guild.char_id", "char.guild_id", "char.party_id", "char.pet_id", "char.homun_id", "guild_castle.guild_id",
	"pet.account_id", "pet.char_id", "mercenary_owner.merc_id", ".arc_new_aid", ".new_aid", NULL };
// tables whose rows are never deleted for a dangling id: a dangling id there stops the whole compaction
static const char* keep_tables[] = { "login", "char", "guild", "party", NULL };

static bool is_zero_ref(const char* table, const char* col)
{
	char a[300], b[300];
	int i;
	snprintf(a, sizeof(a), "%s.%s", table, col);
	snprintf(b, sizeof(b), ".%s", col);
	for (i = 0; zero_refs[i]; i++)
		if (!strcmp(zero_refs[i], a) || !strcmp(zero_refs[i], b))
			return true;
	return false;
}

static bool is_keep_table(const char* table)
{
	int i;
	for (i = 0; keep_tables[i]; i++)
		if (!strcmp(keep_tables[i], table))
			return true;
	return false;
}

static long long q_ll(MYSQL* h, const char* q, long long def)
{
	MYSQL_RES* res;
	MYSQL_ROW row;
	long long v = def;
	if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL)
		return def;
	if ((row = mysql_fetch_row(res)) != NULL && row[0])
		v = strtoll(row[0], NULL, 10);
	mysql_free_result(res);
	return v;
}

// One column that holds ids of a kind.
struct idcol { char table[128]; char col[64]; int kind; bool zero; bool login_db; long long moved, orphans; };
static struct idcol cols[256];
static int ncols = 0;
// tables with card0..card3 (maker / egg ids), per database
struct cardtab { char table[128]; bool login_db; };
static struct cardtab cardtabs[32];
static int ncardtabs = 0;

static bool skip_table(const char* t)
{
	size_t n = strlen(t);
	if (!strncmp(t, "arc_", 4) || !strncmp(t, "idc_", 4))
		return true;
	if (n >= 3 && !strcmp(t + n - 3, "log")) // loginlog, charlog, picklog, zenylog, chatlog, ...
		return true;
	return !strcmp(t, "mapreg") || !strcmp(t, "ragsrvinfo") || !strcmp(t, "sstatus") || !strcmp(t, "ipbanlist");
}

// Find the id columns of one database.
static void scan_db(MYSQL* h, bool login_db, bool both_same)
{
	char q[512];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int k, r;
	snprintf(q, sizeof(q), "SELECT `table_name`, `column_name` FROM information_schema.columns WHERE `table_schema` = DATABASE() ORDER BY `table_name`, `ordinal_position`");
	if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL)
		return;
	while ((row = mysql_fetch_row(res)) != NULL) {
		const char* t = row[0];
		const char* c = row[1];
		// the archive keeps its old ids as labels -- except the new account id of an account the login-server has
		// brought back and whose characters the char-server has not yet (they must find each other after the move)
		if (skip_table(t) && !(!strncmp(t, "arc_", 4) && (!strcmp(c, "arc_new_aid") || !strcmp(c, "new_aid"))))
			continue;
		if (!strcmp(c, "card2") && !login_db) {
			int i;
			for (i = 0; i < ncardtabs && strcmp(cardtabs[i].table, t); i++)
				;
			if (i == ncardtabs && ncardtabs < 32) {
				snprintf(cardtabs[ncardtabs].table, sizeof(cardtabs[0].table), "%s", t);
				cardtabs[ncardtabs++].login_db = login_db;
			}
			continue;
		}
		for (k = 0; k < N_KINDS; k++) {
			bool match = false;
			if (!strcmp(t, kinds[k].table) && !strcmp(c, kinds[k].pk))
				match = true;
			for (r = 0; !match && r < 8 && kinds[k].refs[r]; r++)
				match = kinds[k].refs[r][0] && !strcmp(kinds[k].refs[r], c);
			if (!match || ncols >= 256)
				continue;
			// the login database (when it is another one) only has the account map
			if (login_db && (both_same || k != 0))
				continue;
			snprintf(cols[ncols].table, sizeof(cols[0].table), "%s", t);
			snprintf(cols[ncols].col, sizeof(cols[0].col), "%s", c);
			cols[ncols].kind = k;
			cols[ncols].zero = is_zero_ref(t, c);
			cols[ncols].login_db = login_db;
			cols[ncols].moved = cols[ncols].orphans = 0;
			ncols++;
			break;
		}
	}
	mysql_free_result(res);
}

// Build idc_<kind> (o -> n) in database h from the ids in `ids`.
static bool write_map(MYSQL* h, const struct idkind* k, const unsigned int* ids, const unsigned int* news, int n)
{
	static char q[65536];
	int i = 0;
	size_t p;
	snprintf(q, sizeof(q), "DROP TABLE IF EXISTS `idc_%s`", k->name);
	sqlarc_query(h, q);
	snprintf(q, sizeof(q), "CREATE TABLE `idc_%s` (`o` INT UNSIGNED NOT NULL, `n` INT UNSIGNED NOT NULL, PRIMARY KEY (`o`), KEY (`n`)) ENGINE=MyISAM", k->name);
	if (!sqlarc_query(h, q))
		return false;
	while (i < n) {
		p = (size_t)snprintf(q, sizeof(q), "INSERT INTO `idc_%s` (`o`,`n`) VALUES ", k->name);
		for (; i < n && p < sizeof(q) - 64; i++)
			p += (size_t)snprintf(q + p, sizeof(q) - p, "%s(%u,%u)", (q[p-1] == ' ') ? "" : ",", ids[i], news[i]);
		if (!sqlarc_query(h, q))
			return false;
	}
	return true;
}

static void drop_maps(MYSQL* lh, bool same)
{
	char q[96];
	int k;
	for (k = 0; k < N_KINDS; k++) {
		snprintf(q, sizeof(q), "DROP TABLE IF EXISTS `idc_%s`", kinds[k].name);
		sqlarc_query(&mysql_handle, q);
		if (!same && lh)
			sqlarc_query(lh, q);
	}
}

// Ids of a kind, in order, and their new numbers.
static bool build_kind(MYSQL* lh, bool same, struct idkind* k)
{
	char q[512];
	MYSQL* h = k->in_login_db ? lh : &mysql_handle;
	MYSQL_RES* res;
	MYSQL_ROW row;
	unsigned int *ids, *news;
	int n = 0, cap, i;
	unsigned int next, minid;

	k->total = k->moved = k->max_old = k->max_new = 0;
	if (!sqlarc_table_exists(h, k->table))
		return true; // an optional table (mercenary on an old schema)
	cap = (int)q_ll(h, (snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s`", k->table), q), -1);
	if (cap < 0)
		return false;
	ids = (unsigned int*)aMalloc(sizeof(unsigned int) * (cap + 1));
	news = (unsigned int*)aMalloc(sizeof(unsigned int) * (cap + 1));
	snprintf(q, sizeof(q), "SELECT `%s` FROM `%s` ORDER BY `%s`", k->pk, k->table, k->pk);
	if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL) {
		aFree(ids); aFree(news);
		return false;
	}
	while ((row = mysql_fetch_row(res)) != NULL && n < cap + 1)
		ids[n++] = (unsigned int)strtoul(row[0], NULL, 10);
	mysql_free_result(res);
	minid = n ? ids[0] : 0;
	next = (unsigned int)k->base;
	if (!k->keep_below && n && minid < next)
		next = minid; // ids from before the usual first number: start there (a renumbering only goes down)
	for (i = 0; i < n; i++) {
		if (k->keep_below && ids[i] < (unsigned int)k->base)
			news[i] = ids[i];
		else
			news[i] = next++;
		if (news[i] != ids[i])
			k->moved++;
	}
	k->total = n;
	k->max_old = n ? (int)ids[n-1] : 0;
	k->max_new = n ? (int)news[n-1] : 0;
	if (!write_map(&mysql_handle, k, ids, news, n) || (!same && k->in_login_db && !write_map(lh, k, ids, news, n))) {
		aFree(ids); aFree(news);
		return false;
	}
	// the account map is needed in the character database (char.account_id, storage, ...) and, when the login
	// table is elsewhere, there too
	aFree(ids); aFree(news);
	return true;
}

static void set_autoinc(MYSQL* h, const char* table, const char* col);
// AUTO_INCREMENT = MAX+1 in every table of the database that has one (S.: "all tables, every storage...").
static int set_all_autoinc(MYSQL* h, bool login_tables_only)
{
	char q[512], tabs[128][128], colsn[128][64];
	MYSQL_RES* res;
	MYSQL_ROW row;
	int n = 0, i;
	snprintf(q, sizeof(q), "SELECT `table_name`, `column_name` FROM information_schema.columns WHERE `table_schema` = DATABASE() AND `extra` LIKE '%%auto_increment%%'");
	if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL)
		return 0;
	while ((row = mysql_fetch_row(res)) != NULL && n < 128) {
		if (skip_table(row[0]) && strncmp(row[0], "arc_", 4) != 0)
			continue; // logs: leave them (arc_index has one too: it is set like the rest)
		if (login_tables_only && strcmp(row[0], login_db))
			continue;
		snprintf(tabs[n], sizeof(tabs[0]), "%s", row[0]);
		snprintf(colsn[n], sizeof(colsn[0]), "%s", row[1]);
		n++;
	}
	mysql_free_result(res);
	for (i = 0; i < n; i++)
		set_autoinc(h, tabs[i], colsn[i]);
	return n;
}

static void set_autoinc(MYSQL* h, const char* table, const char* col)
{
	char q[512];
	long long mx;
	snprintf(q, sizeof(q), "SELECT COALESCE(MAX(`%s`),0) FROM `%s`", col, table);
	if ((mx = q_ll(h, q, -1)) < 0)
		return;
	snprintf(q, sizeof(q), "ALTER TABLE `%s` AUTO_INCREMENT = %lld", table, mx + 1);
	sqlarc_query(h, q);
}

void char_idcompact_run(void)
{
	char q[2048];
	MYSQL* lh;
	bool same;
	int k, i;
	long long orphans = 0, orphan_keep = 0, moved_rows = 0, orphan_nomap = 0;
	char dbc[256] = "", dbl[256] = "";
	MYSQL_RES* res;
	MYSQL_ROW row;

	if (compact_mode <= 0)
		return;
	kinds[0].table = login_db; kinds[1].table = char_db; kinds[7].table = inventory_db; kinds[8].table = cart_db;
	kinds[9].table = storage_db; kinds[10].table = guild_storage_db; kinds[11].table = memo_db;
	if ((lh = char_archive_login_db()) == NULL) {
		ShowError("[IDCOMPACT] no connection to the login database: the ids are not compacted.\n");
		return;
	}
	if (sqlarc_query(&mysql_handle, "SELECT DATABASE()") && (res = mysql_store_result(&mysql_handle)) != NULL) {
		if ((row = mysql_fetch_row(res)) && row[0]) snprintf(dbc, sizeof(dbc), "%s", row[0]);
		mysql_free_result(res);
	}
	if (sqlarc_query(lh, "SELECT DATABASE()") && (res = mysql_store_result(lh)) != NULL) {
		if ((row = mysql_fetch_row(res)) && row[0]) snprintf(dbl, sizeof(dbl), "%s", row[0]);
		mysql_free_result(res);
	}
	same = (lh == &mysql_handle) || (dbc[0] && !strcmp(dbc, dbl) && !strcmp(login_server_ip, char_server_ip) && login_server_port == char_server_port);
	ShowStatus("[IDCOMPACT] %s: building the id maps (char db '%s', login db '%s'%s)...\n",
		compact_mode == 2 ? "compacting the ids" : "report only (id_compact_mode 1)", dbc, dbl, same ? ", the same" : "");

	ncols = ncardtabs = 0;
	for (k = 0; k < N_KINDS; k++)
		if (!build_kind(lh, same, &kinds[k])) {
			ShowError("[IDCOMPACT] could not read the %s ids: nothing changed.\n", kinds[k].name);
			drop_maps(lh, same);
			return;
		}
	scan_db(&mysql_handle, false, same);
	if (!same)
		scan_db(lh, true, same);

	// how many rows each column would change / points at missing ids
	for (i = 0; i < ncols; i++) {
		struct idcol* c = &cols[i];
		MYSQL* h = c->login_db ? lh : &mysql_handle;
		const char* kn = kinds[c->kind].name;
		bool own = !strcmp(c->table, kinds[c->kind].table) && !strcmp(c->col, kinds[c->kind].pk);
		snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s` WHERE `%s` IN (SELECT `o` FROM `idc_%s` WHERE `n` <> `o`)", c->table, c->col, kn);
		c->moved = q_ll(h, q, 0);
		moved_rows += c->moved;
		if (own)
			continue;
		snprintf(q, sizeof(q), "SELECT COUNT(*) FROM `%s` WHERE `%s` <> 0 AND `%s` NOT IN (SELECT `o` FROM `idc_%s`)", c->table, c->col, c->col, kn);
		c->orphans = q_ll(h, q, 0);
		if (c->orphans > 0) {
			ShowInfo("[IDCOMPACT] %s.%s: %lld rows point at %s ids that do not exist -> %s.\n", c->table, c->col, c->orphans, kn,
				c->zero ? "set to 0" : is_keep_table(c->table) ? "STOP (never deleted here)" : "deleted");
			if (kinds[c->kind].total == 0)
				orphan_nomap += c->orphans; // no ids of the kind read at all: a wrong table/database, not leftovers
			if (!c->zero) {
				orphans += c->orphans;
				if (is_keep_table(c->table))
					orphan_keep += c->orphans;
			}
		}
	}
	for (k = 0; k < N_KINDS; k++)
		if (kinds[k].total)
			ShowInfo("[IDCOMPACT] %s (%s.%s): %d ids, %d to move, max %d -> %d.\n", kinds[k].name, kinds[k].table, kinds[k].pk,
				kinds[k].total, kinds[k].moved, kinds[k].max_old, kinds[k].max_new);
	ShowInfo("[IDCOMPACT] %d id columns, %d item tables; %lld rows to rewrite, %lld rows with missing ids to delete.\n",
		ncols, ncardtabs, moved_rows, orphans);
	if (compact_mode != 2) {
		ShowStatus("[IDCOMPACT] report only: nothing changed (id_compact_mode: 2 compacts on the next start).\n");
		drop_maps(lh, same);
		return;
	}
	if (orphan_keep > 0 || orphan_nomap > 0 || (compact_orphan_max > 0 && orphans > compact_orphan_max)) {
		ShowError("[IDCOMPACT] %lld rows point at missing ids (%lld in tables never deleted from, %lld of a kind with no ids at all; "
			"id_compact_orphan_max %d): nothing changed. Look at the lines above.\n", orphans, orphan_keep, orphan_nomap, compact_orphan_max);
		drop_maps(lh, same);
		return;
	}

	// steps 1-3 in one transaction per database (the tables are InnoDB on the live server): any failed statement
	// rolls all of it back. AUTO_INCREMENT (an ALTER, which commits) comes after.
	{
	int failed = 0;
	sqlarc_query(&mysql_handle, "START TRANSACTION");
	if (!same)
		sqlarc_query(lh, "START TRANSACTION");
	// 1. dangling ids: 0 or the row goes
	for (i = 0; i < ncols; i++) {
		struct idcol* c = &cols[i];
		MYSQL* h = c->login_db ? lh : &mysql_handle;
		if (c->orphans <= 0)
			continue;
		if (c->zero)
			snprintf(q, sizeof(q), "UPDATE `%s` SET `%s` = 0 WHERE `%s` <> 0 AND `%s` NOT IN (SELECT `o` FROM `idc_%s`)", c->table, c->col, c->col, c->col, kinds[c->kind].name);
		else
			snprintf(q, sizeof(q), "DELETE FROM `%s` WHERE `%s` <> 0 AND `%s` NOT IN (SELECT `o` FROM `idc_%s`)", c->table, c->col, c->col, kinds[c->kind].name);
		if (!sqlarc_query(h, q))
			failed++;
	}
	// 2. the ids, in ascending order (new <= old: no row ever takes an id another still has)
	for (i = 0; i < ncols; i++) {
		struct idcol* c = &cols[i];
		MYSQL* h = c->login_db ? lh : &mysql_handle;
		const char* kn = kinds[c->kind].name;
		if (c->moved <= 0)
			continue;
		snprintf(q, sizeof(q), "UPDATE `%s` SET `%s` = (SELECT `n` FROM `idc_%s` WHERE `o` = `%s`.`%s`)"
			" WHERE `%s` IN (SELECT `o` FROM `idc_%s` WHERE `n` <> `o`) ORDER BY `%s`",
			c->table, c->col, kn, c->table, c->col, c->col, kn, c->col);
		if (!sqlarc_query(h, q)) {
			ShowError("[IDCOMPACT] %s.%s could not be rewritten (see the SQL error above).\n", c->table, c->col);
			failed++;
		}
	}
	// 3. ids inside items: the maker of forged/brewed items, the pet of an egg
	for (i = 0; i < ncardtabs; i++) {
		MYSQL* h = cardtabs[i].login_db ? lh : &mysql_handle;
		const char* t = cardtabs[i].table;
#define LO(x) "IF(((" x ") & 0xFFFF) > 32767, ((" x ") & 0xFFFF) - 65536, (" x ") & 0xFFFF)"
#define HI(x) "IF(((" x ") >> 16 & 0xFFFF) > 32767, ((" x ") >> 16 & 0xFFFF) - 65536, (" x ") >> 16 & 0xFFFF)"
		snprintf(q, sizeof(q), "UPDATE `%s` t JOIN `idc_chr` m ON m.`o` = ((t.`card2` & 0xFFFF) | ((t.`card3` & 0xFFFF) << 16))"
			" SET t.`card2` = " LO("m.`n`") ", t.`card3` = " HI("m.`n`") " WHERE t.`card0` IN (255,254) AND m.`n` <> m.`o`", t);
		if (!sqlarc_query(h, q))
			failed++;
		snprintf(q, sizeof(q), "UPDATE `%s` t JOIN `idc_pet` m ON m.`o` = ((t.`card1` & 0xFFFF) | ((t.`card2` & 0xFFFF) << 16))"
			" SET t.`card1` = " LO("m.`n`") ", t.`card2` = " HI("m.`n`") " WHERE t.`card0` = -256 AND m.`n` <> m.`o`", t);
		if (!sqlarc_query(h, q))
			failed++;
#undef LO
#undef HI
	}
	if (failed) {
		sqlarc_query(&mysql_handle, "ROLLBACK");
		if (!same)
			sqlarc_query(lh, "ROLLBACK");
		drop_maps(lh, same);
		ShowError("[IDCOMPACT] %d statements failed: everything rolled back (on InnoDB tables), the ids stay as they were.\n", failed);
		return;
	}
	sqlarc_query(&mysql_handle, "COMMIT");
	if (!same)
		sqlarc_query(lh, "COMMIT");
	}
	// 4. AUTO_INCREMENT = MAX+1 in every table that has one
	drop_maps(lh, same);
	i = set_all_autoinc(&mysql_handle, false);
	if (!same)
		i += set_all_autoinc(lh, true);
	ShowStatus("[IDCOMPACT] done: %lld rows rewritten, %lld rows with missing ids removed; AUTO_INCREMENT = MAX+1 in %d tables.\n", moved_rows, orphans, i);
}
