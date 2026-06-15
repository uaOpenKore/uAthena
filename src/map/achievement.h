// [Backport] Achievements & titles - mirrors the quest-log engine (SP2). uAthena SP.

#ifndef _ACHIEVEMENT_H_
#define _ACHIEVEMENT_H_

#include "../common/mmo.h" // MAX_ACHIEVEMENT_DB, struct achievement, achievement_group

struct map_session_data;

struct s_achievement_db {
	int id;
	int group;          // achievement_group (see mmo.h)
	int target_id;      // mob / job / quest id (0 = any)
	int target_count;   // goal count
	int reward_item;
	int reward_amount;
	int reward_zeny;
	int reward_exp;     // base exp
	char name[64];
	char title[32];     // granted title ("" = none)
};
extern struct s_achievement_db achievement_db[MAX_ACHIEVEMENT_DB];

int achievement_search_db(int achievement_id);
int achievement_get_index(struct map_session_data *sd, int achievement_id);
void achievement_progress(struct map_session_data *sd, int group, int target_id, int amount);
void achievement_login(struct map_session_data *sd);
int achievement_chat_list(struct map_session_data *sd);
int achievement_title_list(struct map_session_data *sd);
int achievement_set_title(struct map_session_data *sd, int achievement_id);
const char* achievement_active_title(struct map_session_data *sd);
void do_init_achievement(void);

#endif /* _ACHIEVEMENT_H_ */
