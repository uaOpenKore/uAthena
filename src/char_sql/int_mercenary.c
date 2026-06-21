// [Backport] Hired Mercenary Soldier storage. Ported from eAthena int_mercenary.c
// but rewritten to uAthena's char_sql raw-mysql idiom (mysql_handle / tmp_sql /
// sql_res / sql_row), mirroring int_quest.c / int_achievement.c — char_sql here
// has no Sql_* API. Two tables: `mercenary` (instance) + `mercenary_owner` (per-char
// loyalty/calls, loaded with the character).

#include "../common/mmo.h"
#include "../common/db.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "../common/socket.h"
#include "../common/strlib.h"

#include "char.h"
#include "inter.h"
#include "int_mercenary.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// Loaded as part of the character: mer_id + per-guild loyalty/calls.
bool mercenary_owner_fromsql(int char_id, struct mmo_charstatus *status)
{
	sprintf(tmp_sql, "SELECT `merc_id`, `arch_calls`, `arch_faith`, `spear_calls`, `spear_faith`, `sword_calls`, `sword_faith` FROM `mercenary_owner` WHERE `char_id` = '%d'", char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}

	sql_res = mysql_store_result(&mysql_handle);
	if( sql_res && (sql_row = mysql_fetch_row(sql_res)) )
	{
		status->mer_id      = atoi(sql_row[0]);
		status->arch_calls  = atoi(sql_row[1]);
		status->arch_faith  = atoi(sql_row[2]);
		status->spear_calls = atoi(sql_row[3]);
		status->spear_faith = atoi(sql_row[4]);
		status->sword_calls = atoi(sql_row[5]);
		status->sword_faith = atoi(sql_row[6]);
	}
	if( sql_res )
		mysql_free_result(sql_res);

	return true;
}

bool mercenary_owner_tosql(int char_id, struct mmo_charstatus *status)
{
	sprintf(tmp_sql, "REPLACE INTO `mercenary_owner` (`char_id`, `merc_id`, `arch_calls`, `arch_faith`, `spear_calls`, `spear_faith`, `sword_calls`, `sword_faith`) VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d', '%d')",
		char_id, status->mer_id, status->arch_calls, status->arch_faith, status->spear_calls, status->spear_faith, status->sword_calls, status->sword_faith);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}

	return true;
}

bool mercenary_owner_delete(int char_id)
{
	sprintf(tmp_sql, "DELETE FROM `mercenary_owner` WHERE `char_id` = '%d'", char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
	}

	sprintf(tmp_sql, "DELETE FROM `mercenary` WHERE `char_id` = '%d'", char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
	}

	return true;
}

static bool mapif_mercenary_save(struct s_mercenary* merc)
{
	bool flag = true;

	if( merc->mercenary_id == 0 )
	{ // Create new DB entry
		sprintf(tmp_sql, "INSERT INTO `mercenary` (`char_id`,`class`,`hp`,`sp`,`kill_counter`,`life_time`) VALUES ('%d','%d','%d','%d','%u','%u')",
			merc->char_id, merc->class_, merc->hp, merc->sp, merc->kill_count, merc->life_time);
		if( mysql_query(&mysql_handle, tmp_sql) )
		{
			ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
			ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
			flag = false;
		}
		else
			merc->mercenary_id = (int)mysql_insert_id(&mysql_handle);
	}
	else
	{ // Update DB entry
		sprintf(tmp_sql, "UPDATE `mercenary` SET `char_id`='%d', `class`='%d', `hp`='%d', `sp`='%d', `kill_counter`='%u', `life_time`='%u' WHERE `mer_id`='%d'",
			merc->char_id, merc->class_, merc->hp, merc->sp, merc->kill_count, merc->life_time, merc->mercenary_id);
		if( mysql_query(&mysql_handle, tmp_sql) )
		{
			ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
			ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
			flag = false;
		}
	}

	return flag;
}

static bool mapif_mercenary_load(int merc_id, int char_id, struct s_mercenary *merc)
{
	memset(merc, 0, sizeof(struct s_mercenary));
	merc->mercenary_id = merc_id;
	merc->char_id = char_id;

	sprintf(tmp_sql, "SELECT `class`, `hp`, `sp`, `kill_counter`, `life_time` FROM `mercenary` WHERE `mer_id` = '%d' AND `char_id` = '%d'", merc_id, char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}

	sql_res = mysql_store_result(&mysql_handle);
	if( !sql_res || !(sql_row = mysql_fetch_row(sql_res)) )
	{
		if( sql_res )
			mysql_free_result(sql_res);
		return false;
	}

	merc->class_     = atoi(sql_row[0]);
	merc->hp         = atoi(sql_row[1]);
	merc->sp         = atoi(sql_row[2]);
	merc->kill_count = atoi(sql_row[3]);
	merc->life_time  = atoi(sql_row[4]);
	mysql_free_result(sql_res);

	return true;
}

static bool mapif_mercenary_delete(int merc_id)
{
	sprintf(tmp_sql, "DELETE FROM `mercenary` WHERE `mer_id` = '%d'", merc_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}

	return true;
}

static void mapif_mercenary_send(int fd, struct s_mercenary *merc, unsigned char flag)
{
	int size = sizeof(struct s_mercenary) + 5;

	WFIFOHEAD(fd,size);
	WFIFOW(fd,0) = 0x3870;
	WFIFOW(fd,2) = size;
	WFIFOB(fd,4) = flag;
	memcpy(WFIFOP(fd,5), merc, sizeof(struct s_mercenary));
	WFIFOSET(fd,size);
}

static void mapif_parse_mercenary_create(int fd, struct s_mercenary* merc)
{
	bool result = mapif_mercenary_save(merc);
	mapif_mercenary_send(fd, merc, result);
}

static void mapif_parse_mercenary_load(int fd, int merc_id, int char_id)
{
	struct s_mercenary merc;
	bool result = mapif_mercenary_load(merc_id, char_id, &merc);
	mapif_mercenary_send(fd, &merc, result);
}

static void mapif_mercenary_deleted(int fd, unsigned char flag)
{
	WFIFOHEAD(fd,3);
	WFIFOW(fd,0) = 0x3871;
	WFIFOB(fd,2) = flag;
	WFIFOSET(fd,3);
}

static void mapif_parse_mercenary_delete(int fd, int merc_id)
{
	bool result = mapif_mercenary_delete(merc_id);
	mapif_mercenary_deleted(fd, result);
}

static void mapif_mercenary_saved(int fd, unsigned char flag)
{
	WFIFOHEAD(fd,3);
	WFIFOW(fd,0) = 0x3872;
	WFIFOB(fd,2) = flag;
	WFIFOSET(fd,3);
}

static void mapif_parse_mercenary_save(int fd, struct s_mercenary* merc)
{
	bool result = mapif_mercenary_save(merc);
	mapif_mercenary_saved(fd, result);
}

int inter_mercenary_sql_init(void)
{
	return 0;
}

void inter_mercenary_sql_final(void)
{
	return;
}

/*==========================================
 * Inter Packets (map -> char)
 *------------------------------------------*/
int inter_mercenary_parse_frommap(int fd)
{
	unsigned short cmd = RFIFOW(fd,0);

	switch( cmd )
	{
		case 0x3070: mapif_parse_mercenary_create(fd, (struct s_mercenary*)RFIFOP(fd,4)); break;
		case 0x3071: mapif_parse_mercenary_load(fd, (int)RFIFOL(fd,2), (int)RFIFOL(fd,6)); break;
		case 0x3072: mapif_parse_mercenary_delete(fd, (int)RFIFOL(fd,2)); break;
		case 0x3073: mapif_parse_mercenary_save(fd, (struct s_mercenary*)RFIFOP(fd,4)); break;
		default:
			return 0;
	}
	return 1;
}
