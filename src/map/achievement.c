// [Backport] Achievements & titles engine - mirrors quest.c (SP2). uAthena SP.
// Phase 1: definition database (db/achievement_db.txt) loader.

#include "../common/cbasetypes.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "map.h"
#include "achievement.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct s_achievement_db achievement_db[MAX_ACHIEVEMENT_DB];

/// Returns the achievement_db index for the given id, or -1 if not defined.
int achievement_search_db(int achievement_id)
{
	int i;
	for( i = 0; i < MAX_ACHIEVEMENT_DB; i++ )
		if( achievement_db[i].id == achievement_id )
			return i;
	return -1;
}

/// Copies the next double-quoted field (starting at/after *pp) into dst and
/// advances *pp past its closing quote. dst becomes "" if no quoted field.
static void achievement_read_quoted(char **pp, char *dst, int dstsize)
{
	char *ns, *ne;
	int nlen;

	dst[0] = '\0';
	if( pp == NULL || *pp == NULL )
		return;
	ns = strchr(*pp, '"');
	if( ns == NULL )
		return;
	ne = strchr(ns + 1, '"');
	if( ne == NULL )
		return;
	nlen = (int)(ne - (ns + 1));
	if( nlen >= dstsize )
		nlen = dstsize - 1;
	memcpy(dst, ns + 1, nlen);
	dst[nlen] = '\0';
	*pp = ne + 1;
}

/// Reads db/achievement_db.txt:
/// ID,Group,TargetID,TargetCount,RewardItem,RewardAmount,RewardZeny,RewardExp,"Name","Title"
int achievement_read_db(void)
{
	FILE *fp;
	char line[1024];
	int j, k = 0;
	char *str[8], *p, *np;

	sprintf(line, "%s/achievement_db.txt", db_path);
	if( (fp = fopen(line, "r")) == NULL ) {
		ShowError("can't read %s\n", line);
		return -1;
	}

	while( fgets(line, sizeof(line), fp) )
	{
		if( k == MAX_ACHIEVEMENT_DB ) {
			ShowError("achievement_read_db: Too many entries in %s/achievement_db.txt!\n", db_path);
			break;
		}
		if( line[0] == '/' && line[1] == '/' )
			continue;
		memset(str, 0, sizeof(str));

		// 8 leading numeric fields
		for( j = 0, p = line; j < 8; j++ )
		{
			if( (np = strchr(p, ',')) != NULL ) {
				str[j] = p;
				*np = 0;
				p = np + 1;
			}
			else
				break;
		}
		if( str[0] == NULL || j < 8 )
			continue;

		memset(&achievement_db[k], 0, sizeof(achievement_db[0]));
		achievement_db[k].id            = atoi(str[0]);
		achievement_db[k].group         = atoi(str[1]);
		achievement_db[k].target_id     = atoi(str[2]);
		achievement_db[k].target_count  = atoi(str[3]);
		achievement_db[k].reward_item   = atoi(str[4]);
		achievement_db[k].reward_amount = atoi(str[5]);
		achievement_db[k].reward_zeny   = atoi(str[6]);
		achievement_db[k].reward_exp    = atoi(str[7]);
		// 9th + 10th fields: "Name","Title"  (p points past the 8th comma)
		achievement_read_quoted(&p, achievement_db[k].name, sizeof(achievement_db[k].name));
		achievement_read_quoted(&p, achievement_db[k].title, sizeof(achievement_db[k].title));

		if( achievement_db[k].id <= 0 )
			continue;
		k++;
	}
	fclose(fp);
	ShowStatus("Done reading '"CL_WHITE"%d"CL_RESET"' entries in '"CL_WHITE"%s"CL_RESET"'.\n", k, "achievement_db.txt");
	return 0;
}

void do_init_achievement(void)
{
	achievement_read_db();
}
