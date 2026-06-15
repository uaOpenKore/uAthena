// [Backport] Achievements & titles engine - mirrors quest.c (SP2). uAthena SP.
// Phase 1: definition database (db/achievement_db.txt) loader.

#include "../common/cbasetypes.h"
#include "../common/malloc.h"
#include "../common/nullpo.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "map.h"
#include "pc.h"
#include "clif.h"
#include "achievement.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct s_achievement_db achievement_db[MAX_ACHIEVEMENT_DB];
int achievement_db_count = 0;

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
	achievement_db_count = k;
	fclose(fp);
	ShowStatus("Done reading '"CL_WHITE"%d"CL_RESET"' entries in '"CL_WHITE"%s"CL_RESET"'.\n", k, "achievement_db.txt");
	return 0;
}

/// Returns the achievement_log index for achievement_id, or -1.
int achievement_get_index(struct map_session_data *sd, int achievement_id)
{
	int i;
	ARR_FIND(0, sd->num_achievements, i, sd->achievement_log[i].achievement_id == achievement_id);
	return (i < sd->num_achievements) ? i : -1;
}

/// Ensures a log entry exists for achievement_id (db index dbidx); returns log index or -1.
static int achievement_ensure(struct map_session_data *sd, int achievement_id, int dbidx)
{
	int i = achievement_get_index(sd, achievement_id);
	if( i >= 0 )
		return i;
	if( sd->num_achievements >= MAX_ACHIEVEMENT )
		return -1;
	i = sd->num_achievements;
	memset(&sd->achievement_log[i], 0, sizeof(struct achievement));
	sd->achievement_log[i].achievement_id = achievement_id;
	sd->achievement_index[i] = dbidx;
	sd->num_achievements++;
	sd->save_achievement = true;
	return i;
}

/// Grants the reward for a completed achievement (idempotent via the rewarded flag).
static void achievement_reward(struct map_session_data *sd, int i)
{
	struct s_achievement_db *ad = &achievement_db[sd->achievement_index[i]];
	char output[128];

	if( sd->achievement_log[i].rewarded )
		return;
	sd->achievement_log[i].rewarded = 1;
	sd->save_achievement = true;

	if( ad->reward_zeny > 0 )
		pc_getzeny(sd, ad->reward_zeny);
	if( ad->reward_exp > 0 )
		pc_gainexp(sd, NULL, (unsigned int)ad->reward_exp, 0);
	if( ad->reward_item > 0 ) {
		struct item it;
		memset(&it, 0, sizeof(it));
		it.nameid = ad->reward_item;
		it.identify = 1;
		pc_additem(sd, &it, ad->reward_amount > 0 ? ad->reward_amount : 1);
	}

	snprintf(output, sizeof(output), "Achievement unlocked: %s", ad->name);
	clif_displaymessage(sd->fd, output);
	if( ad->title[0] ) {
		snprintf(output, sizeof(output), "New title available: %s  (use @title)", ad->title);
		clif_displaymessage(sd->fd, output);
	}
}

/// Completes the achievement at log index i if its count reached the goal.
static void achievement_try_complete(struct map_session_data *sd, int i)
{
	struct s_achievement_db *ad = &achievement_db[sd->achievement_index[i]];
	if( sd->achievement_log[i].completed )
		return;
	if( sd->achievement_log[i].count >= ad->target_count ) {
		sd->achievement_log[i].completed = (unsigned int)time(NULL);
		sd->save_achievement = true;
		achievement_reward(sd, i);
	}
}

/// Advances all achievements of `group` (filtered by target_id; 0 in db = any) by `amount`.
/// KILL/QUEST/JOBCHANGE accumulate; BASELEVEL/JOBLEVEL/ZENY take `amount` as the absolute value.
void achievement_progress(struct map_session_data *sd, int group, int target_id, int amount)
{
	int j;
	nullpo_retv(sd);

	for( j = 0; j < achievement_db_count; j++ )
	{
		struct s_achievement_db *ad = &achievement_db[j];
		int i;
		if( ad->id <= 0 || ad->group != group )
			continue;
		if( ad->target_id != 0 && ad->target_id != target_id )
			continue;
		if( (i = achievement_ensure(sd, ad->id, j)) < 0 )
			continue;
		if( sd->achievement_log[i].completed )
			continue;
		if( group == AG_KILL || group == AG_QUEST || group == AG_JOBCHANGE )
			sd->achievement_log[i].count += amount;
		else
			sd->achievement_log[i].count = amount;
		sd->save_achievement = true;
		achievement_try_complete(sd, i);
	}
}

// [Backport] On login (after the log loads) catch up level/zeny milestones.
void achievement_login(struct map_session_data *sd)
{
	nullpo_retv(sd);
	achievement_progress(sd, AG_BASELEVEL, 0, sd->status.base_level);
	achievement_progress(sd, AG_JOBLEVEL,  0, sd->status.job_level);
	achievement_progress(sd, AG_ZENY,      0, sd->status.zeny);
}

// [Backport] @achievements: refresh zeny (no live hook) then list every defined
// achievement, completed first, with the player's progress. Returns total count.
int achievement_chat_list(struct map_session_data *sd)
{
	int j, done = 0, total = 0;
	char output[160];

	nullpo_ret(sd);
	achievement_progress(sd, AG_ZENY, 0, sd->status.zeny);

	for( j = 0; j < achievement_db_count; j++ )
	{
		int li;
		if( achievement_db[j].id <= 0 )
			continue;
		total++;
		li = achievement_get_index(sd, achievement_db[j].id);
		if( li >= 0 && sd->achievement_log[li].completed )
			done++;
	}
	snprintf(output, sizeof(output), "Achievements: %d/%d completed.", done, total);
	clif_displaymessage(sd->fd, output);

	for( j = 0; j < achievement_db_count; j++ ) // completed
	{
		struct s_achievement_db *ad = &achievement_db[j];
		int li;
		if( ad->id <= 0 )
			continue;
		li = achievement_get_index(sd, ad->id);
		if( li < 0 || !sd->achievement_log[li].completed )
			continue;
		snprintf(output, sizeof(output), "[%d] %s - DONE%s", ad->id, ad->name, ad->title[0] ? " (title)" : "");
		clif_displaymessage(sd->fd, output);
	}
	for( j = 0; j < achievement_db_count; j++ ) // in progress / locked
	{
		struct s_achievement_db *ad = &achievement_db[j];
		int li, cnt;
		if( ad->id <= 0 )
			continue;
		li = achievement_get_index(sd, ad->id);
		if( li >= 0 && sd->achievement_log[li].completed )
			continue;
		cnt = (li >= 0) ? sd->achievement_log[li].count : 0;
		snprintf(output, sizeof(output), "[%d] %s - %d/%d", ad->id, ad->name, cnt, ad->target_count);
		clif_displaymessage(sd->fd, output);
	}
	return total;
}

// List unlocked titles (completed achievements that grant one). Returns the count.
int achievement_title_list(struct map_session_data *sd)
{
	int j, n = 0;
	char output[160];

	nullpo_ret(sd);
	clif_displaymessage(sd->fd, "Titles from your completed achievements:");
	for( j = 0; j < achievement_db_count; j++ )
	{
		struct s_achievement_db *ad = &achievement_db[j];
		int li;
		if( ad->id <= 0 || !ad->title[0] )
			continue;
		li = achievement_get_index(sd, ad->id);
		if( li < 0 || !sd->achievement_log[li].completed )
			continue;
		snprintf(output, sizeof(output), "[%d] %s%s", ad->id, ad->title, (sd->active_title == ad->id) ? "  <-- active" : "");
		clif_displaymessage(sd->fd, output);
		n++;
	}
	if( !n )
		clif_displaymessage(sd->fd, "  (none yet - complete achievements that grant a title)");
	clif_displaymessage(sd->fd, "'@title <id>' to set, '@title off' to clear.");
	return n;
}

// Set the active title to the given completed-and-titled achievement (0 = clear).
// Returns 1 on success, 0 on failure.
int achievement_set_title(struct map_session_data *sd, int achievement_id)
{
	int dbidx, li;

	nullpo_ret(sd);
	if( achievement_id == 0 )
	{
		sd->active_title = 0;
		return 1;
	}
	dbidx = achievement_search_db(achievement_id);
	if( dbidx < 0 || !achievement_db[dbidx].title[0] )
		return 0;
	li = achievement_get_index(sd, achievement_id);
	if( li < 0 || !sd->achievement_log[li].completed )
		return 0;
	sd->active_title = achievement_id;
	return 1;
}

// Returns the active title string ("" if none).
const char* achievement_active_title(struct map_session_data *sd)
{
	int dbidx;
	if( !sd || sd->active_title == 0 )
		return "";
	dbidx = achievement_search_db(sd->active_title);
	return (dbidx >= 0) ? achievement_db[dbidx].title : "";
}

void do_init_achievement(void)
{
	achievement_read_db();
}
