// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Quest log of the TXT char-server. The map-server is shared with the SQL build, so this answers the
// same inter packets as char_sql/int_quest.c (0x3060 load -> 0x3860, 0x3061 save -> 0x3861) with the
// same replies; the logs are kept in memory and written to quest_txt with the other TXT saves.
// One line per quest, like one row of the SQL `quest` table:
//   <char_id>,<quest_id>,<state>,<time>,<count1>,<count2>,<count3>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../common/mmo.h"
#include "../common/malloc.h"
#include "../common/socket.h"
#include "../common/db.h"
#include "../common/lock.h"
#include "../common/showmsg.h"
#include "char.h"
#include "inter.h"
#include "int_quest.h"

char quest_txt[1024] = "save/quest.txt";

// The quest log of one character, in the order it was stored.
struct quest_log {
	int char_id;
	int count;
	struct quest *data;
};

static struct dbt *quest_log_db = NULL;

static int inter_quest_tostr(char *str, int char_id, struct quest *qd)
{
	sprintf(str, "%d,%d,%d,%u,%d,%d,%d", char_id, qd->quest_id, (int)qd->state, qd->time,
		qd->count[0], qd->count[1], qd->count[2]);
	return 0;
}

static int inter_quest_fromstr(char *str, int *char_id, struct quest *qd)
{
	int tmp_int[5];
	unsigned int tmp_uint;

	memset(qd, 0, sizeof(struct quest));
	if (sscanf(str, "%d,%d,%d,%u,%d,%d,%d", char_id, &tmp_int[0], &tmp_int[1], &tmp_uint,
		&tmp_int[2], &tmp_int[3], &tmp_int[4]) != 7)
		return 1;

	qd->quest_id = tmp_int[0];
	qd->state = (quest_state)tmp_int[1];
	qd->time = tmp_uint;
	qd->count[0] = tmp_int[2];
	qd->count[1] = tmp_int[3];
	qd->count[2] = tmp_int[4];
	return 0;
}

static void* create_quest_log(DBKey key, va_list args)
{
	struct quest_log *ql = (struct quest_log *)aCalloc(1, sizeof(struct quest_log));
	ql->char_id = key.i;
	return ql;
}

static void quest_log_free(struct quest_log *ql)
{
	if (ql->data)
		aFree(ql->data);
	aFree(ql);
}

static int quest_log_db_final(DBKey key, void *data, va_list ap)
{
	quest_log_free((struct quest_log *)data);
	return 0;
}

//---------------------------------------------------------
// Load all quest logs from quest_txt
int inter_quest_init(void)
{
	char line[1024];
	FILE *fp;
	int c = 0;

	quest_log_db = db_alloc(__FILE__,__LINE__,DB_INT,DB_OPT_BASE,sizeof(int));

	if ((fp = fopen(quest_txt, "r")) == NULL)
		return 1;
	while (fgets(line, sizeof(line), fp))
	{
		struct quest_log *ql;
		struct quest qd;
		int char_id, i;

		c++;
		if ((line[0] == '/' && line[1] == '/') || line[0] == '\n' || line[0] == '\r')
			continue;
		if (inter_quest_fromstr(line, &char_id, &qd) != 0 || char_id <= 0) {
			ShowError("int_quest: broken data [%s] line %d\n", quest_txt, c);
			continue;
		}
		ql = (struct quest_log *)idb_ensure(quest_log_db, char_id, create_quest_log);
		ARR_FIND(0, ql->count, i, ql->data[i].quest_id == qd.quest_id);
		if (i < ql->count) { // (char_id, quest_id) is the primary key of the SQL table
			ShowError("int_quest: duplicate quest %d of character %d [%s] line %d, ignored\n", qd.quest_id, char_id, quest_txt, c);
			continue;
		}
		if (ql->count >= MAX_PC_QUESTS) {
			ShowError("int_quest: character %d has more than %d quests [%s] line %d, ignored\n", char_id, MAX_PC_QUESTS, quest_txt, c);
			continue;
		}
		ql->data = (struct quest *)aRealloc(ql->data, (ql->count+1)*sizeof(struct quest));
		memcpy(&ql->data[ql->count++], &qd, sizeof(struct quest));
	}
	fclose(fp);
	return 0;
}

void inter_quest_final(void)
{
	if (quest_log_db)
		quest_log_db->destroy(quest_log_db, quest_log_db_final);
	quest_log_db = NULL;
}

static int inter_quest_save_sub(DBKey key, void *data, va_list ap)
{
	char line[256];
	struct quest_log *ql = (struct quest_log *)data;
	FILE *fp = va_arg(ap, FILE *);
	int i;

	for (i = 0; i < ql->count; i++) {
		inter_quest_tostr(line, ql->char_id, &ql->data[i]);
		fprintf(fp, "%s" RETCODE, line);
	}
	return 0;
}

//---------------------------------------------------------
// Write all quest logs to quest_txt
int inter_quest_save(void)
{
	FILE *fp;
	int lock;

	if ((fp = lock_fopen(quest_txt, &lock)) == NULL) {
		ShowError("int_quest: can't write [%s] !!! data is lost !!!\n", quest_txt);
		return 1;
	}
	quest_log_db->foreach(quest_log_db, inter_quest_save_sub, fp);
	lock_fclose(fp, quest_txt, &lock);
	return 0;
}

// Delete the quest log of a character (character deletion)
int inter_quest_delete(int char_id)
{
	struct quest_log *ql = (struct quest_log *)idb_remove(quest_log_db, char_id);
	if (ql)
		quest_log_free(ql);
	return 0;
}

//---------------------------------------------------------
// packets from map server

// 0x3061 <len>.W <char_id>.L {<struct quest>}* -- the whole quest log of a character.
// Same result as the SQL diff save: quests not in the packet are deleted, new ones are added, and a
// quest that was already stored only takes the new state and counts (the SQL UPDATE leaves `time`).
// Answer: 0x3861 <char_id>.L <success>.B
static int mapif_parse_quest_save(int fd)
{
	int i, j, n = 0, len = RFIFOW(fd,2);
	int new_n = (len > 8) ? (len-8) / (int)sizeof(struct quest) : 0;
	int char_id = RFIFOL(fd,4);
	struct quest_log *ql = (struct quest_log *)idb_get(quest_log_db, char_id);
	struct quest *qd_new = NULL;
	bool success = true;

	if (new_n > MAX_PC_QUESTS) {
		ShowError("mapif_parse_quest_save: %d quests for character %d, only %d are saved.\n", new_n, char_id, MAX_PC_QUESTS);
		new_n = MAX_PC_QUESTS;
		success = false;
	}
	if (new_n > 0)
		qd_new = (struct quest *)aMalloc(new_n*sizeof(struct quest));
	for (i = 0; i < new_n; i++) {
		struct quest qd;
		memcpy(&qd, RFIFOP(fd,8+i*sizeof(struct quest)), sizeof(struct quest));
		ARR_FIND(0, n, j, qd_new[j].quest_id == qd.quest_id);
		if (j < n) { // a second row with the same key: the SQL INSERT fails
			success = false;
			continue;
		}
		if (ql) { // already stored -> keep its time
			ARR_FIND(0, ql->count, j, ql->data[j].quest_id == qd.quest_id);
			if (j < ql->count)
				qd.time = ql->data[j].time;
		}
		memcpy(&qd_new[n++], &qd, sizeof(struct quest));
	}

	if (n == 0) {
		if (qd_new)
			aFree(qd_new);
		inter_quest_delete(char_id);
	} else {
		if (ql == NULL)
			ql = (struct quest_log *)idb_ensure(quest_log_db, char_id, create_quest_log);
		if (ql->data)
			aFree(ql->data);
		ql->data = qd_new;
		ql->count = n;
	}

	WFIFOHEAD(fd,7);
	WFIFOW(fd,0) = 0x3861;
	WFIFOL(fd,2) = char_id;
	WFIFOB(fd,6) = success ? 1 : 0;
	WFIFOSET(fd,7);
	return 0;
}

// 0x3060 <char_id>.L -- request the quest log of a character.
// Answer: 0x3860 <len>.W <char_id>.L {<struct quest>}* with the active and inactive quests first and
// the completed ones last, exactly like the SQL char-server.
static int mapif_parse_quest_load(int fd)
{
	int char_id = RFIFOL(fd,2);
	struct quest_log *ql = (struct quest_log *)idb_get(quest_log_db, char_id);
	int i, k = 0, num_quests = ql ? ql->count : 0;

	WFIFOHEAD(fd, num_quests*sizeof(struct quest)+8);
	WFIFOW(fd,0) = 0x3860;
	WFIFOW(fd,2) = num_quests*sizeof(struct quest)+8;
	WFIFOL(fd,4) = char_id;
	for (i = 0; i < num_quests; i++)
		if (ql->data[i].state != Q_COMPLETE)
			memcpy(WFIFOP(fd,(k++)*sizeof(struct quest)+8), &ql->data[i], sizeof(struct quest));
	for (i = 0; i < num_quests; i++)
		if (ql->data[i].state == Q_COMPLETE)
			memcpy(WFIFOP(fd,(k++)*sizeof(struct quest)+8), &ql->data[i], sizeof(struct quest));
	WFIFOSET(fd, num_quests*sizeof(struct quest)+8);
	return 0;
}

int inter_quest_parse_frommap(int fd)
{
	RFIFOHEAD(fd);
	switch(RFIFOW(fd,0)) {
	case 0x3060: mapif_parse_quest_load(fd); break;
	case 0x3061: mapif_parse_quest_save(fd); break;
	default:
		return 0;
	}
	return 1;
}
