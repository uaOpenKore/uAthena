// [Backport] Achievements & titles - mirrors the quest-log engine (SP2). uAthena SP.

#ifndef _ACHIEVEMENT_H_
#define _ACHIEVEMENT_H_

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
void do_init_achievement(void);

#endif /* _ACHIEVEMENT_H_ */
