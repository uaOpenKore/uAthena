// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
// Quest-log storage. Ported from eAthena and adapted to uAthena's char_sql
// raw-mysql API (mysql_handle / tmp_sql / sql_res / sql_row), matching int_homun.c.

#include "../common/mmo.h"
#include "../common/db.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "../common/socket.h"
#include "../common/strlib.h"

#include "char.h"
#include "inter.h"
#include "int_quest.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

//Load entire questlog for a character. Returns the number of quests read.
int mapif_quests_fromsql(int char_id, struct quest questlog[])
{
	int i = 0;

	sprintf(tmp_sql, "SELECT `quest_id`, `state`, `time`, `count1`, `count2`, `count3` FROM `%s` WHERE `char_id`='%d' LIMIT %d", quest_db, char_id, MAX_QUEST_DB);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return 0;
	}
	sql_res = mysql_store_result(&mysql_handle);
	if( sql_res )
	{
		while( i < MAX_QUEST_DB && (sql_row = mysql_fetch_row(sql_res)) )
		{
			memset(&questlog[i], 0, sizeof(struct quest));
			questlog[i].quest_id = atoi(sql_row[0]);
			questlog[i].state    = (quest_state)atoi(sql_row[1]);
			questlog[i].time     = (unsigned int)strtoul(sql_row[2], NULL, 10);
			questlog[i].count[0] = atoi(sql_row[3]);
			questlog[i].count[1] = atoi(sql_row[4]);
			questlog[i].count[2] = atoi(sql_row[5]);
			i++;
		}
		mysql_free_result(sql_res);
	}
	return i;
}

//Delete a quest
bool mapif_quest_delete(int char_id, int quest_id)
{
	sprintf(tmp_sql, "DELETE FROM `%s` WHERE `quest_id`='%d' AND `char_id`='%d'", quest_db, quest_id, char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}
	return true;
}

//Add a quest to a questlog
bool mapif_quest_add(int char_id, struct quest qd)
{
	sprintf(tmp_sql, "INSERT INTO `%s`(`quest_id`, `char_id`, `state`, `time`, `count1`, `count2`, `count3`) VALUES ('%d', '%d', '%d', '%u', '%d', '%d', '%d')", quest_db, qd.quest_id, char_id, qd.state, qd.time, qd.count[0], qd.count[1], qd.count[2]);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}
	return true;
}

//Update a questlog (only state and counts are mutable)
bool mapif_quest_update(int char_id, struct quest qd)
{
	sprintf(tmp_sql, "UPDATE `%s` SET `state`='%d', `count1`='%d', `count2`='%d', `count3`='%d' WHERE `quest_id`='%d' AND `char_id`='%d'", quest_db, qd.state, qd.count[0], qd.count[1], qd.count[2], qd.quest_id, char_id);
	if( mysql_query(&mysql_handle, tmp_sql) )
	{
		ShowSQL("DB error - %s\n", mysql_error(&mysql_handle));
		ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, tmp_sql);
		return false;
	}
	return true;
}

//Save quests: diff the map's questlog against the DB (idempotent by char_id+quest_id)
int mapif_parse_quest_save(int fd)
{
	int i, j, k, old_n, new_n = (RFIFOW(fd,2)-8)/sizeof(struct quest);
	int char_id = RFIFOL(fd,4);
	struct quest qd_new[MAX_QUEST_DB], qd_old[MAX_QUEST_DB];
	bool success = true;

	RFIFOHEAD(fd);
	memset(qd_new, 0, sizeof(qd_new));
	memset(qd_old, 0, sizeof(qd_old));
	if( new_n )
		memcpy(&qd_new, RFIFOP(fd,8), RFIFOW(fd,2)-8);
	old_n = mapif_quests_fromsql(char_id, qd_old);

	for( i = 0; i < new_n; i++ )
	{
		ARR_FIND( 0, old_n, j, qd_new[i].quest_id == qd_old[j].quest_id );
		if( j < old_n ) // Update existing quest
		{
			ARR_FIND( 0, MAX_QUEST_OBJECTIVES, k, qd_new[i].count[k] != qd_old[j].count[k] );
			if( k != MAX_QUEST_OBJECTIVES || qd_new[i].state != qd_old[j].state )
				success &= mapif_quest_update(char_id, qd_new[i]);

			if( j < (--old_n) ) // drop matched row from qd_old
			{
				memmove(&qd_old[j], &qd_old[j+1], sizeof(struct quest)*(old_n-j));
				memset(&qd_old[old_n], 0, sizeof(struct quest));
			}
		}
		else // Add new quest
			success &= mapif_quest_add(char_id, qd_new[i]);
	}

	for( i = 0; i < old_n; i++ ) // Quests still in qd_old were removed on the map -> delete
		success &= mapif_quest_delete(char_id, qd_old[i].quest_id);

	WFIFOHEAD(fd,7);
	WFIFOW(fd,0) = 0x3861;
	WFIFOL(fd,2) = char_id;
	WFIFOB(fd,6) = success ? 1 : 0;
	WFIFOSET(fd,7);

	return 0;
}

//Send questlog to the map server (active/inactive first, completed last)
int mapif_parse_quest_load(int fd)
{
	int char_id = RFIFOL(fd,2);
	struct quest tmp_questlog[MAX_QUEST_DB];
	int num_quests, i, num_complete = 0;
	int complete[MAX_QUEST_DB];

	RFIFOHEAD(fd);
	memset(tmp_questlog, 0, sizeof(tmp_questlog));
	memset(complete, 0, sizeof(complete));

	num_quests = mapif_quests_fromsql(char_id, tmp_questlog);

	WFIFOHEAD(fd, num_quests*sizeof(struct quest)+8);
	WFIFOW(fd,0) = 0x3860;
	WFIFOW(fd,2) = num_quests*sizeof(struct quest)+8;
	WFIFOL(fd,4) = char_id;

	//Active and inactive quests
	for( i = 0; i < num_quests; i++ )
	{
		if( tmp_questlog[i].state == Q_COMPLETE )
		{
			complete[num_complete++] = i;
			continue;
		}
		memcpy(WFIFOP(fd,(i-num_complete)*sizeof(struct quest)+8), &tmp_questlog[i], sizeof(struct quest));
	}

	// Completed quests
	for( i = num_quests - num_complete; i < num_quests; i++ )
		memcpy(WFIFOP(fd,i*sizeof(struct quest)+8), &tmp_questlog[complete[i-num_quests+num_complete]], sizeof(struct quest));

	WFIFOSET(fd, num_quests*sizeof(struct quest)+8);

	return 0;
}

int inter_quest_parse_frommap(int fd)
{
	switch(RFIFOW(fd,0))
	{
		case 0x3060: mapif_parse_quest_load(fd); break;
		case 0x3061: mapif_parse_quest_save(fd); break;
		default:
			return 0;
	}
	return 1;
}
