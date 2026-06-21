// [Backport] Hired Mercenary Soldier — ported from eAthena pre-renewal.
// NOTE: distinct from uAthena's mercenary.c, which is the HOMUNCULUS (merc_hom_*).
// Symbols here (merc_*, mercenary_*) do not clash with the homunculus ones.

#ifndef _MERCENARY_SOLDIER_H_
#define _MERCENARY_SOLDIER_H_

#include "map.h"    // struct block_list, view_data, regen_data, status_change, unit_data
#include "status.h" // struct status_data
#include "unit.h"   // struct unit_data

enum {
	ARCH_MERC_GUILD,
	SPEAR_MERC_GUILD,
	SWORD_MERC_GUILD,
};

struct s_mercenary_db {
	int class_;
	char sprite[NAME_LENGTH], name[NAME_LENGTH];
	unsigned short lv;
	short range2, range3;
	struct status_data status;
	struct view_data vd;
	struct {
		unsigned short id, lv;
	} skill[MAX_MERCSKILL];
};

extern struct s_mercenary_db mercenary_db[MAX_MERCENARY_CLASS];

struct mercenary_data {
	struct block_list bl;
	struct unit_data ud;
	struct view_data *vd;
	struct status_data base_status, battle_status;
	struct status_change sc;
	struct regen_data regen;

	struct s_mercenary_db *db;
	struct s_mercenary mercenary;
	char blockskill[MAX_SKILL];

	struct map_session_data *master;
	int contract_timer;
	unsigned int last_thinktime;	// [Backport] custom merc AI tick gate

	unsigned devotion_flag : 1;
};

bool merc_class(int class_);
struct view_data * merc_get_viewdata(int class_);

int merc_create(struct map_session_data *sd, int class_, unsigned int lifetime);
int merc_data_received(struct s_mercenary *merc, bool flag);
int mercenary_save(struct mercenary_data *md);

void mercenary_damage(struct mercenary_data *md, struct block_list *src, int hp, int sp);
void mercenary_heal(struct mercenary_data *md, int hp, int sp);
int mercenary_dead(struct mercenary_data *md, struct block_list *src);

int merc_delete(struct mercenary_data *md, int reply);
void merc_contract_stop(struct mercenary_data *md);

int mercenary_get_lifetime(struct mercenary_data *md);
int mercenary_get_guild(struct mercenary_data *md);
int mercenary_get_faith(struct mercenary_data *md);
int mercenary_set_faith(struct mercenary_data *md, int value);
int mercenary_get_calls(struct mercenary_data *md);
int mercenary_set_calls(struct mercenary_data *md, int value);
int mercenary_kills(struct mercenary_data *md);

int mercenary_checkskill(struct mercenary_data *md, int skill_id);

void mercenary_chat_status(struct map_session_data *sd);	// [Backport] @merc chat UI

int do_init_mercenary(void);
int do_final_mercenary(void);

#endif /* _MERCENARY_SOLDIER_H_ */
