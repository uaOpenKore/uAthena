// Copyright (c) uAthena / bornrok.com
#ifndef _SQLID_H_
#define _SQLID_H_
// [counters] A new row id from an AUTO_INCREMENT column (mysql_insert_id) must fit the int the server keeps it in
// (character, guild, party, pet, homunculus, mercenary ids) and the range of its kind (`max`, inclusive): the
// columns are int(11) UNSIGNED, and an id cast past 2^31-1 became negative -- every later UPDATE/DELETE by that
// id missed its row. Out of range: the creation is refused (the caller removes the row), never stored wrong.
#include <limits.h>
#include "../common/showmsg.h"

static inline int sql_new_id_ok(unsigned long long id, unsigned long long max, const char* what)
{
	if (id > 0 && id <= max && id <= (unsigned long long)INT_MAX)
		return 1;
	ShowError("%s: the new id %llu is out of range (1..%llu): creation refused. The table's AUTO_INCREMENT has run "
		"out for this server; see sql-files/upgrade_2026-11-21_counters.sql.\n", what, id, max < (unsigned long long)INT_MAX ? max : (unsigned long long)INT_MAX);
	return 0;
}
#endif
