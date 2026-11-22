// Copyright (c) uAthena / bornrok.com
#ifndef _SQLARCHIVE_H_
#define _SQLARCHIVE_H_
// [archive] Account archive helpers (S. 2026-11-22): an account that has not logged in for a long time moves,
// with its characters, into `arc_<table>` copies of the player tables; a login with its user name and password
// brings it back with NEW ids. Shared by the char-server (archives, restores the characters) and the
// login-server (restores the account row).
//
// - arc_<table> has every column of <table> plus `arc_no` (the arc_index row of the archiving), no unique keys and
//   no AUTO_INCREMENT: an id may be archived twice (a restored account archived again, an id reused after a
//   restart), and the archive only needs to find rows by arc_no.
// - Rows are copied by the columns both tables have (looked up at run time), so a column added to a live table
//   later (or present only on one server) never breaks a copy.
// - A copy into a live table leaves out its AUTO_INCREMENT column: the row gets a new id (S.: "ids are not
//   carried between the live tables and the archive, new ones are used").
//
// Header-only (like sqlid.h): each server includes it in one .c file.
#include <mysql.h>
#include <stdio.h>
#include <string.h>
#include "../common/showmsg.h"

#define SQLARC_MAX_COLS 96
#define SQLARC_COL_LEN 64

struct sqlarc_cols {
	int n;
	char name[SQLARC_MAX_COLS][SQLARC_COL_LEN];
	char autoinc[SQLARC_COL_LEN]; // the AUTO_INCREMENT column, "" = none
};

static int sqlarc_query(MYSQL* h, const char* q)
{
	if (mysql_query(h, q)) {
		ShowSQL("DB error - %s\n", mysql_error(h));
		ShowDebug("[archive] %s\n", q);
		return 0;
	}
	return 1;
}

// Columns of `table`; 0 when it does not exist (or the query failed).
static int sqlarc_get_cols(MYSQL* h, const char* table, struct sqlarc_cols* c)
{
	char q[256];
	MYSQL_RES* res;
	MYSQL_ROW row;
	c->n = 0;
	c->autoinc[0] = '\0';
	snprintf(q, sizeof(q), "SHOW COLUMNS FROM `%s`", table);
	if (mysql_query(h, q)) // a missing table is normal here (an optional table): no error output
		return 0;
	if ((res = mysql_store_result(h)) == NULL)
		return 0;
	while ((row = mysql_fetch_row(res)) != NULL && c->n < SQLARC_MAX_COLS) {
		snprintf(c->name[c->n], SQLARC_COL_LEN, "%s", row[0]);
		if (row[5] && strstr(row[5], "auto_increment"))
			snprintf(c->autoinc, SQLARC_COL_LEN, "%s", row[0]);
		c->n++;
	}
	mysql_free_result(res);
	return c->n;
}

static int sqlarc_has_col(const struct sqlarc_cols* c, const char* name)
{
	int i;
	for (i = 0; i < c->n; i++)
		if (!strcmp(c->name[i], name))
			return 1;
	return 0;
}

static int sqlarc_table_exists(MYSQL* h, const char* table)
{
	struct sqlarc_cols c;
	return sqlarc_get_cols(h, table, &c) > 0;
}

// Make arc_<table> when <table> exists and the archive copy does not. 1 = there (or made), 0 = no <table> / failed.
static int sqlarc_ensure(MYSQL* h, const char* table)
{
	char arc[96], q[512];
	struct sqlarc_cols c;
	MYSQL_RES* res;
	MYSQL_ROW row;
	char keys[16][SQLARC_COL_LEN];
	int nkeys = 0, i;

	if (!sqlarc_table_exists(h, table))
		return 0;
	snprintf(arc, sizeof(arc), "arc_%s", table);
	if (sqlarc_get_cols(h, arc, &c) > 0)
		return sqlarc_has_col(&c, "arc_no");
	snprintf(q, sizeof(q), "CREATE TABLE `%s` LIKE `%s`", arc, table);
	if (!sqlarc_query(h, q) || !sqlarc_get_cols(h, arc, &c))
		return 0;
	if (c.autoinc[0]) { // keep the column, lose AUTO_INCREMENT (it needs a key, and the keys go below)
		snprintf(q, sizeof(q), "SHOW COLUMNS FROM `%s` WHERE `Field` = '%s'", arc, c.autoinc);
		if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL)
			return 0;
		row = mysql_fetch_row(res);
		if (row)
			snprintf(q, sizeof(q), "ALTER TABLE `%s` MODIFY `%s` %s NOT NULL DEFAULT '0'", arc, c.autoinc, row[1]);
		mysql_free_result(res);
		if (!row || !sqlarc_query(h, q))
			return 0;
	}
	snprintf(q, sizeof(q), "SHOW INDEX FROM `%s` WHERE `Non_unique` = 0", arc);
	if (!sqlarc_query(h, q) || (res = mysql_store_result(h)) == NULL)
		return 0;
	while ((row = mysql_fetch_row(res)) != NULL && nkeys < 16) {
		for (i = 0; i < nkeys && strcmp(keys[i], row[2]); i++)
			;
		if (i == nkeys)
			snprintf(keys[nkeys++], SQLARC_COL_LEN, "%s", row[2]);
	}
	mysql_free_result(res);
	for (i = 0; i < nkeys; i++) {
		if (!strcmp(keys[i], "PRIMARY"))
			snprintf(q, sizeof(q), "ALTER TABLE `%s` DROP PRIMARY KEY", arc);
		else
			snprintf(q, sizeof(q), "ALTER TABLE `%s` DROP INDEX `%s`", arc, keys[i]);
		if (!sqlarc_query(h, q))
			return 0;
	}
	snprintf(q, sizeof(q), "ALTER TABLE `%s` ADD COLUMN `arc_no` INT UNSIGNED NOT NULL DEFAULT '0', ADD KEY `arc_no` (`arc_no`)", arc);
	if (!sqlarc_query(h, q))
		return 0;
	ShowStatus("[archive] made table `%s`.\n", arc);
	return 1;
}

// INSERT INTO dst (...) SELECT ... FROM src WHERE <where>, by the columns both tables have. `over` is a list of
// column/expression pairs ("char_id", "123", ..., NULL) whose values replace the copied ones (a column of dst only
// is set too); skip_autoinc leaves out dst's AUTO_INCREMENT column (a new id). Returns the rows copied, -1 = error.
static long sqlarc_copy(MYSQL* h, const char* dst, const char* src, const char* where, const char* const* over, int skip_autoinc)
{
	static char q[16384];
	struct sqlarc_cols d, s;
	char* pc;
	char* pv;
	static char cols[6144], vals[8192];
	int i, j, first = 1;

	if (!sqlarc_get_cols(h, dst, &d) || !sqlarc_get_cols(h, src, &s))
		return 0; // an optional table that is not there: nothing to copy
	pc = cols; pv = vals;
	*pc = *pv = '\0';
	for (i = 0; i < d.n; i++) {
		const char* expr = NULL;
		if (skip_autoinc && d.autoinc[0] && !strcmp(d.name[i], d.autoinc))
			continue;
		for (j = 0; over && over[j] && over[j+1]; j += 2)
			if (!strcmp(over[j], d.name[i]))
				expr = over[j+1];
		if (!expr && !sqlarc_has_col(&s, d.name[i]))
			continue; // dst only (arc_no, a newer column): its default
		pc += snprintf(pc, cols + sizeof(cols) - pc, "%s`%s`", first ? "" : ",", d.name[i]);
		if (expr)
			pv += snprintf(pv, vals + sizeof(vals) - pv, "%s%s", first ? "" : ",", expr);
		else
			pv += snprintf(pv, vals + sizeof(vals) - pv, "%s`%s`", first ? "" : ",", d.name[i]);
		first = 0;
	}
	snprintf(q, sizeof(q), "INSERT INTO `%s` (%s) SELECT %s FROM `%s` WHERE %s", dst, cols, vals, src, where);
	if (!sqlarc_query(h, q))
		return -1;
	return (long)mysql_affected_rows(h);
}

// DELETE FROM table WHERE <where>; a missing optional table is fine. 1 = done, 0 = error.
static int sqlarc_delete(MYSQL* h, const char* table, const char* where)
{
	char q[1024];
	if (!sqlarc_table_exists(h, table))
		return 1;
	snprintf(q, sizeof(q), "DELETE FROM `%s` WHERE %s", table, where);
	return sqlarc_query(h, q);
}

// card2/card3 (signed smallint in the tables) of a character id; card1/card2 of a pet id.
static void sqlarc_split_id(int id, int* lo, int* hi)
{
	*lo = (short)(id & 0xFFFF);
	*hi = (short)((id >> 16) & 0xFFFF);
}
#endif
