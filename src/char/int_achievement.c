// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// [Backport] Achievements of the TXT char-server. The map-server is shared with the SQL build, so this
// answers the same inter packets as char_sql/int_achievement.c (0x3062 load -> 0x3862, 0x3063 save ->
// 0x3863) with the same replies; the logs are kept in memory and written to achievement_txt with the
// other TXT saves. One line per achievement, like one row of the SQL `achievement` table:
//   <char_id>,<achievement_id>,<count>,<completed>,<rewarded>

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
#include "int_achievement.h"

char achievement_txt[1024] = "save/achievement.txt";

// The achievement log of one character, in the order it was stored.
struct achievement_log {
	int char_id;
	int count;
	struct achievement *data;
};

static struct dbt *achievement_log_db = NULL;

static int inter_achievement_tostr(char *str, int char_id, struct achievement *ad)
{
	sprintf(str, "%d,%d,%d,%u,%d", char_id, ad->achievement_id, ad->count, ad->completed, ad->rewarded);
	return 0;
}

static int inter_achievement_fromstr(char *str, int *char_id, struct achievement *ad)
{
	int tmp_int[3];
	unsigned int tmp_uint;

	memset(ad, 0, sizeof(struct achievement));
	if (sscanf(str, "%d,%d,%d,%u,%d", char_id, &tmp_int[0], &tmp_int[1], &tmp_uint, &tmp_int[2]) != 5)
		return 1;

	ad->achievement_id = tmp_int[0];
	ad->count = tmp_int[1];
	ad->completed = tmp_uint;
	ad->rewarded = tmp_int[2];
	return 0;
}

static void* create_achievement_log(DBKey key, va_list args)
{
	struct achievement_log *al = (struct achievement_log *)aCalloc(1, sizeof(struct achievement_log));
	al->char_id = key.i;
	return al;
}

static void achievement_log_free(struct achievement_log *al)
{
	if (al->data)
		aFree(al->data);
	aFree(al);
}

static int achievement_log_db_final(DBKey key, void *data, va_list ap)
{
	achievement_log_free((struct achievement_log *)data);
	return 0;
}

//---------------------------------------------------------
// Load all achievement logs from achievement_txt
int inter_achievement_init(void)
{
	char line[1024];
	FILE *fp;
	int c = 0;

	achievement_log_db = db_alloc(__FILE__,__LINE__,DB_INT,DB_OPT_BASE,sizeof(int));

	if ((fp = fopen(achievement_txt, "r")) == NULL)
		return 1;
	while (fgets(line, sizeof(line), fp))
	{
		struct achievement_log *al;
		struct achievement ad;
		int char_id, i;

		c++;
		if ((line[0] == '/' && line[1] == '/') || line[0] == '\n' || line[0] == '\r')
			continue;
		if (inter_achievement_fromstr(line, &char_id, &ad) != 0 || char_id <= 0) {
			ShowError("int_achievement: broken data [%s] line %d\n", achievement_txt, c);
			continue;
		}
		al = (struct achievement_log *)idb_ensure(achievement_log_db, char_id, create_achievement_log);
		ARR_FIND(0, al->count, i, al->data[i].achievement_id == ad.achievement_id);
		if (i < al->count) {
			ShowError("int_achievement: duplicate achievement %d of character %d [%s] line %d, ignored\n", ad.achievement_id, char_id, achievement_txt, c);
			continue;
		}
		if (al->count >= MAX_ACHIEVEMENT) {
			ShowError("int_achievement: character %d has more than %d achievements [%s] line %d, ignored\n", char_id, MAX_ACHIEVEMENT, achievement_txt, c);
			continue;
		}
		al->data = (struct achievement *)aRealloc(al->data, (al->count+1)*sizeof(struct achievement));
		memcpy(&al->data[al->count++], &ad, sizeof(struct achievement));
	}
	fclose(fp);
	return 0;
}

void inter_achievement_final(void)
{
	if (achievement_log_db)
		achievement_log_db->destroy(achievement_log_db, achievement_log_db_final);
	achievement_log_db = NULL;
}

static int inter_achievement_save_sub(DBKey key, void *data, va_list ap)
{
	char line[256];
	struct achievement_log *al = (struct achievement_log *)data;
	FILE *fp = va_arg(ap, FILE *);
	int i;

	for (i = 0; i < al->count; i++) {
		inter_achievement_tostr(line, al->char_id, &al->data[i]);
		fprintf(fp, "%s" RETCODE, line);
	}
	return 0;
}

//---------------------------------------------------------
// Write all achievement logs to achievement_txt
int inter_achievement_save(void)
{
	FILE *fp;
	int lock;

	if ((fp = lock_fopen(achievement_txt, &lock)) == NULL) {
		ShowError("int_achievement: can't write [%s] !!! data is lost !!!\n", achievement_txt);
		return 1;
	}
	achievement_log_db->foreach(achievement_log_db, inter_achievement_save_sub, fp);
	lock_fclose(fp, achievement_txt, &lock);
	return 0;
}

// Delete the achievement log of a character (character deletion)
int inter_achievement_delete(int char_id)
{
	struct achievement_log *al = (struct achievement_log *)idb_remove(achievement_log_db, char_id);
	if (al)
		achievement_log_free(al);
	return 0;
}

//---------------------------------------------------------
// packets from map server

// 0x3063 <len>.W <char_id>.L {<struct achievement>}* -- the whole achievement log of a character.
// Same result as the SQL diff save: entries not in the packet are deleted, the others take the new
// values. Answer: 0x3863 <char_id>.L <success>.B
static int mapif_parse_achievement_save(int fd)
{
	int i, j, n = 0, len = RFIFOW(fd,2);
	int new_n = (len > 8) ? (len-8) / (int)sizeof(struct achievement) : 0;
	int char_id = RFIFOL(fd,4);
	struct achievement_log *al;
	struct achievement *ad_new = NULL;
	bool success = true;

	if (new_n > MAX_ACHIEVEMENT) {
		ShowError("mapif_parse_achievement_save: %d achievements for character %d, only %d are saved.\n", new_n, char_id, MAX_ACHIEVEMENT);
		new_n = MAX_ACHIEVEMENT;
		success = false;
	}
	if (new_n > 0)
		ad_new = (struct achievement *)aMalloc(new_n*sizeof(struct achievement));
	for (i = 0; i < new_n; i++) {
		struct achievement ad;
		memcpy(&ad, RFIFOP(fd,8+i*sizeof(struct achievement)), sizeof(struct achievement));
		ARR_FIND(0, n, j, ad_new[j].achievement_id == ad.achievement_id);
		if (j < n) { // a second row with the same key: the SQL INSERT fails
			success = false;
			continue;
		}
		memcpy(&ad_new[n++], &ad, sizeof(struct achievement));
	}

	if (n == 0) {
		if (ad_new)
			aFree(ad_new);
		inter_achievement_delete(char_id);
	} else {
		al = (struct achievement_log *)idb_ensure(achievement_log_db, char_id, create_achievement_log);
		if (al->data)
			aFree(al->data);
		al->data = ad_new;
		al->count = n;
	}

	WFIFOHEAD(fd,7);
	WFIFOW(fd,0) = 0x3863;
	WFIFOL(fd,2) = char_id;
	WFIFOB(fd,6) = success ? 1 : 0;
	WFIFOSET(fd,7);
	return 0;
}

// 0x3062 <char_id>.L -- request the achievement log of a character.
// Answer: 0x3862 <len>.W <char_id>.L {<struct achievement>}*
static int mapif_parse_achievement_load(int fd)
{
	int char_id = RFIFOL(fd,2);
	struct achievement_log *al = (struct achievement_log *)idb_get(achievement_log_db, char_id);
	int n = al ? al->count : 0;

	WFIFOHEAD(fd, n*sizeof(struct achievement)+8);
	WFIFOW(fd,0) = 0x3862;
	WFIFOW(fd,2) = n*sizeof(struct achievement)+8;
	WFIFOL(fd,4) = char_id;
	if (n)
		memcpy(WFIFOP(fd,8), al->data, n*sizeof(struct achievement));
	WFIFOSET(fd, n*sizeof(struct achievement)+8);
	return 0;
}

int inter_achievement_parse_frommap(int fd)
{
	RFIFOHEAD(fd);
	switch(RFIFOW(fd,0)) {
	case 0x3062: mapif_parse_achievement_load(fd); break;
	case 0x3063: mapif_parse_achievement_save(fd); break;
	default:
		return 0;
	}
	return 1;
}
