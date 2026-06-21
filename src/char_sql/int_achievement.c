// Achievement storage. Mirrors int_quest.c using uAthena's char_sql raw-mysql
// API (mysql_handle / tmp_sql / sql_res / sql_row). uAthena SP.

#include "../common/mmo.h"
#include "../common/db.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "../common/socket.h"
#include "../common/strlib.h"

#include "char.h"
#include "inter.h"
#include "int_achievement.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

// Load all achievements for a character. Returns the count read.
int mapif_achievements_fromsql(int char_id, struct achievement log[])
{
	int i = 0;

	sprintf(tmp_sql, "SELECT `achievement_id`, `count`, `completed`, `rewarded` FROM `achievement` WHERE `char_id`='%d' LIMIT %d", char_id, MAX_ACHIEVEMENT);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return 0;
	}
	sql_res = mysql_store_result(&mysql_handle);
	if( sql_res )
	{
		while( i < MAX_ACHIEVEMENT && (sql_row = mysql_fetch_row(sql_res)) )
		{
			memset(&log[i], 0, sizeof(struct achievement));
			log[i].achievement_id = atoi(sql_row[0]);
			log[i].count          = atoi(sql_row[1]);
			log[i].completed      = (unsigned int)strtoul(sql_row[2], NULL, 10);
			log[i].rewarded       = atoi(sql_row[3]);
			i++;
		}
		mysql_free_result(sql_res);
	}
	return i;
}

bool mapif_achievement_delete(int char_id, int achievement_id)
{
	sprintf(tmp_sql, "DELETE FROM `achievement` WHERE `achievement_id`='%d' AND `char_id`='%d'", achievement_id, char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}
	return true;
}

bool mapif_achievement_add(int char_id, struct achievement ad)
{
	sprintf(tmp_sql, "INSERT INTO `achievement`(`achievement_id`, `char_id`, `count`, `completed`, `rewarded`) VALUES ('%d', '%d', '%d', '%u', '%d')", ad.achievement_id, char_id, ad.count, ad.completed, ad.rewarded);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}
	return true;
}

bool mapif_achievement_update(int char_id, struct achievement ad)
{
	sprintf(tmp_sql, "UPDATE `achievement` SET `count`='%d', `completed`='%u', `rewarded`='%d' WHERE `achievement_id`='%d' AND `char_id`='%d'", ad.count, ad.completed, ad.rewarded, ad.achievement_id, char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}
	return true;
}

// Save achievements: diff the map's log against the DB (idempotent by char_id+achievement_id).
int mapif_parse_achievement_save(int fd)
{
	int i, j, old_n, new_n = (RFIFOW(fd,2)-8)/sizeof(struct achievement);
	int char_id = RFIFOL(fd,4);
	struct achievement ad_new[MAX_ACHIEVEMENT], ad_old[MAX_ACHIEVEMENT];
	bool success = true;

	RFIFOHEAD(fd);
	memset(ad_new, 0, sizeof(ad_new));
	memset(ad_old, 0, sizeof(ad_old));
	if( new_n )
		memcpy(&ad_new, RFIFOP(fd,8), RFIFOW(fd,2)-8);
	old_n = mapif_achievements_fromsql(char_id, ad_old);

	for( i = 0; i < new_n; i++ )
	{
		ARR_FIND( 0, old_n, j, ad_new[i].achievement_id == ad_old[j].achievement_id );
		if( j < old_n ) // update existing
		{
			if( ad_new[i].count != ad_old[j].count || ad_new[i].completed != ad_old[j].completed || ad_new[i].rewarded != ad_old[j].rewarded )
				success &= mapif_achievement_update(char_id, ad_new[i]);

			if( j < (--old_n) ) // drop matched row from ad_old
			{
				memmove(&ad_old[j], &ad_old[j+1], sizeof(struct achievement)*(old_n-j));
				memset(&ad_old[old_n], 0, sizeof(struct achievement));
			}
		}
		else // add new
			success &= mapif_achievement_add(char_id, ad_new[i]);
	}

	for( i = 0; i < old_n; i++ ) // rows still in ad_old were removed on the map -> delete
		success &= mapif_achievement_delete(char_id, ad_old[i].achievement_id);

	WFIFOHEAD(fd,7);
	WFIFOW(fd,0) = 0x3863;
	WFIFOL(fd,2) = char_id;
	WFIFOB(fd,6) = success ? 1 : 0;
	WFIFOSET(fd,7);

	return 0;
}

// Send the achievement log to the map server.
int mapif_parse_achievement_load(int fd)
{
	int char_id = RFIFOL(fd,2);
	struct achievement tmp_log[MAX_ACHIEVEMENT];
	int n;

	RFIFOHEAD(fd);
	memset(tmp_log, 0, sizeof(tmp_log));
	n = mapif_achievements_fromsql(char_id, tmp_log);

	WFIFOHEAD(fd, n*sizeof(struct achievement)+8);
	WFIFOW(fd,0) = 0x3862;
	WFIFOW(fd,2) = n*sizeof(struct achievement)+8;
	WFIFOL(fd,4) = char_id;
	if( n )
		memcpy(WFIFOP(fd,8), tmp_log, n*sizeof(struct achievement));
	WFIFOSET(fd, n*sizeof(struct achievement)+8);

	return 0;
}

int inter_achievement_parse_frommap(int fd)
{
	switch(RFIFOW(fd,0))
	{
		case 0x3062: mapif_parse_achievement_load(fd); break;
		case 0x3063: mapif_parse_achievement_save(fd); break;
		default:
			return 0;
	}
	return 1;
}
