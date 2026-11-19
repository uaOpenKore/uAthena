// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// [Backport] Hired mercenary soldiers of the TXT char-server (NOT the homunculus, see int_homun.c).
// The map-server is shared with the SQL build, so this answers the same inter packets as
// char_sql/int_mercenary.c (0x3070 create -> 0x3870, 0x3071 load -> 0x3870, 0x3072 delete -> 0x3871,
// 0x3073 save -> 0x3872) with the same replies. The mercenaries (the SQL `mercenary` table) are kept
// in memory and written to mercenary_txt with the other TXT saves, one line per mercenary, then the
// next id like the %newid% line of athena.txt, so a deleted id is never handed out again (the SQL
// auto_increment):
//   <mer_id>,<char_id>,<class>,<hp>,<sp>,<kill_counter>,<life_time>
//   <next mer_id>\t%newid%
// The owner side (mer_id + loyalty/calls, the SQL `mercenary_owner` table) belongs to the character:
// see mercenary_owner_txt in char.c.

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
#include "int_mercenary.h"

char mercenary_txt[1024] = "save/mercenary.txt";

static struct dbt *mercenary_db = NULL;
static int mercenary_newid = 1;

static int inter_mercenary_tostr(char *str, struct s_mercenary *p)
{
	sprintf(str, "%d,%d,%d,%d,%d,%u,%u", p->mercenary_id, p->char_id, p->class_, p->hp, p->sp,
		p->kill_count, p->life_time);
	return 0;
}

static int inter_mercenary_fromstr(char *str, struct s_mercenary *p)
{
	int tmp_int[5];
	unsigned int tmp_uint[2];

	memset(p, 0, sizeof(struct s_mercenary));
	if (sscanf(str, "%d,%d,%d,%d,%d,%u,%u", &tmp_int[0], &tmp_int[1], &tmp_int[2], &tmp_int[3], &tmp_int[4],
		&tmp_uint[0], &tmp_uint[1]) != 7)
		return 1;

	p->mercenary_id = tmp_int[0];
	p->char_id = tmp_int[1];
	p->class_ = tmp_int[2];
	p->hp = tmp_int[3];
	p->sp = tmp_int[4];
	p->kill_count = tmp_uint[0];
	p->life_time = tmp_uint[1];
	return 0;
}

//---------------------------------------------------------
// Load all mercenaries from mercenary_txt
int inter_mercenary_init(void)
{
	char line[1024];
	struct s_mercenary *p;
	FILE *fp;
	int c = 0;

	mercenary_db = db_alloc(__FILE__,__LINE__,DB_INT,DB_OPT_RELEASE_DATA,sizeof(int));

	if ((fp = fopen(mercenary_txt, "r")) == NULL)
		return 1;
	while (fgets(line, sizeof(line), fp))
	{
		int i, j = 0;

		c++;
		if ((line[0] == '/' && line[1] == '/') || line[0] == '\n' || line[0] == '\r')
			continue;
		if (sscanf(line, "%d\t%%newid%%%n", &i, &j) == 1 && j > 0) {
			if (mercenary_newid < i)
				mercenary_newid = i;
			continue;
		}
		p = (struct s_mercenary *)aCalloc(1, sizeof(struct s_mercenary));
		if (inter_mercenary_fromstr(line, p) != 0 || p->mercenary_id <= 0) {
			ShowError("int_mercenary: broken data [%s] line %d\n", mercenary_txt, c);
			aFree(p);
			continue;
		}
		if (idb_get(mercenary_db, p->mercenary_id) != NULL) {
			ShowError("int_mercenary: duplicate mercenary id %d [%s] line %d, ignored\n", p->mercenary_id, mercenary_txt, c);
			aFree(p);
			continue;
		}
		if (p->mercenary_id >= mercenary_newid)
			mercenary_newid = p->mercenary_id + 1;
		idb_put(mercenary_db, p->mercenary_id, p);
	}
	fclose(fp);
	return 0;
}

void inter_mercenary_final(void)
{
	if (mercenary_db)
		mercenary_db->destroy(mercenary_db, NULL);
	mercenary_db = NULL;
}

static int inter_mercenary_save_sub(DBKey key, void *data, va_list ap)
{
	char line[256];
	FILE *fp = va_arg(ap, FILE *);

	inter_mercenary_tostr(line, (struct s_mercenary *)data);
	fprintf(fp, "%s" RETCODE, line);
	return 0;
}

//---------------------------------------------------------
// Write all mercenaries and the next id to mercenary_txt
int inter_mercenary_save(void)
{
	FILE *fp;
	int lock;

	if ((fp = lock_fopen(mercenary_txt, &lock)) == NULL) {
		ShowError("int_mercenary: can't write [%s] !!! data is lost !!!\n", mercenary_txt);
		return 1;
	}
	mercenary_db->foreach(mercenary_db, inter_mercenary_save_sub, fp);
	fprintf(fp, "%d\t%%newid%%" RETCODE, mercenary_newid);
	lock_fclose(fp, mercenary_txt, &lock);
	return 0;
}

static int inter_mercenary_delete_char_sub(DBKey key, void *data, va_list ap)
{
	int char_id = va_arg(ap, int);

	if (((struct s_mercenary *)data)->char_id == char_id)
		idb_remove(mercenary_db, key.i);
	return 0;
}

// Delete the mercenaries of a character (character deletion; mercenary_owner_delete on SQL)
int inter_mercenary_delete_char(int char_id)
{
	mercenary_db->foreach(mercenary_db, inter_mercenary_delete_char_sub, char_id);
	return 0;
}

// Like the SQL INSERT/UPDATE: id 0 creates a new mercenary (the id is written back into merc), an
// existing id overwrites it, an unknown id changes nothing.
static bool inter_mercenary_store(struct s_mercenary *merc)
{
	struct s_mercenary *p;

	if (merc->mercenary_id == 0) {
		merc->mercenary_id = mercenary_newid++;
		p = (struct s_mercenary *)aCalloc(1, sizeof(struct s_mercenary));
		memcpy(p, merc, sizeof(struct s_mercenary));
		idb_put(mercenary_db, p->mercenary_id, p);
	} else if ((p = (struct s_mercenary *)idb_get(mercenary_db, merc->mercenary_id)) != NULL)
		memcpy(p, merc, sizeof(struct s_mercenary));

	return true;
}

//---------------------------------------------------------
// packets to map server

// 0x3870 <len>.W <flag>.B <struct s_mercenary> -- created/loaded mercenary (flag 0 = failed)
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

// 0x3871 <flag>.B -- delete result
static void mapif_mercenary_deleted(int fd, unsigned char flag)
{
	WFIFOHEAD(fd,3);
	WFIFOW(fd,0) = 0x3871;
	WFIFOB(fd,2) = flag;
	WFIFOSET(fd,3);
}

// 0x3872 <flag>.B -- save result
static void mapif_mercenary_saved(int fd, unsigned char flag)
{
	WFIFOHEAD(fd,3);
	WFIFOW(fd,0) = 0x3872;
	WFIFOB(fd,2) = flag;
	WFIFOSET(fd,3);
}

//---------------------------------------------------------
// packets from map server

// 0x3070 <len>.W <struct s_mercenary> -- create (mercenary_id 0)
static void mapif_parse_mercenary_create(int fd)
{
	struct s_mercenary merc;
	bool result;

	memset(&merc, 0, sizeof(merc));
	if (RFIFOW(fd,2) != sizeof(struct s_mercenary) + 4) {
		ShowError("inter mercenary: create data size error %d != %d\n", RFIFOW(fd,2) - 4, (int)sizeof(struct s_mercenary));
		mapif_mercenary_send(fd, &merc, 0);
		return;
	}
	memcpy(&merc, RFIFOP(fd,4), sizeof(struct s_mercenary));
	result = inter_mercenary_store(&merc); // assigns the new id
	mapif_mercenary_send(fd, &merc, result);
}

// 0x3071 <mer_id>.L <char_id>.L -- load. Like the SQL SELECT ... WHERE mer_id AND char_id: a mercenary
// of another character is not found. On failure the reply carries only the two ids.
static void mapif_parse_mercenary_load(int fd, int merc_id, int char_id)
{
	struct s_mercenary merc, *p;
	bool result = false;

	memset(&merc, 0, sizeof(merc));
	merc.mercenary_id = merc_id;
	merc.char_id = char_id;
	p = (struct s_mercenary *)idb_get(mercenary_db, merc_id);
	if (p != NULL && p->char_id == char_id) {
		memcpy(&merc, p, sizeof(struct s_mercenary));
		result = true;
	}
	mapif_mercenary_send(fd, &merc, result);
}

// 0x3072 <mer_id>.L -- delete. Like the SQL DELETE it succeeds when there is no such mercenary.
static void mapif_parse_mercenary_delete(int fd, int merc_id)
{
	idb_remove(mercenary_db, merc_id);
	mapif_mercenary_deleted(fd, 1);
}

// 0x3073 <len>.W <struct s_mercenary> -- save
static void mapif_parse_mercenary_save(int fd)
{
	struct s_mercenary merc;
	bool result;

	if (RFIFOW(fd,2) != sizeof(struct s_mercenary) + 4) {
		ShowError("inter mercenary: save data size error %d != %d\n", RFIFOW(fd,2) - 4, (int)sizeof(struct s_mercenary));
		mapif_mercenary_saved(fd, 0);
		return;
	}
	memcpy(&merc, RFIFOP(fd,4), sizeof(struct s_mercenary));
	result = inter_mercenary_store(&merc);
	mapif_mercenary_saved(fd, result);
}

int inter_mercenary_parse_frommap(int fd)
{
	RFIFOHEAD(fd);
	switch(RFIFOW(fd,0)) {
	case 0x3070: mapif_parse_mercenary_create(fd); break;
	case 0x3071: mapif_parse_mercenary_load(fd, (int)RFIFOL(fd,2), (int)RFIFOL(fd,6)); break;
	case 0x3072: mapif_parse_mercenary_delete(fd, (int)RFIFOL(fd,2)); break;
	case 0x3073: mapif_parse_mercenary_save(fd); break;
	default:
		return 0;
	}
	return 1;
}
