// [Backport] Hired Mercenary Soldier engine — ported from eAthena pre-renewal.
// NOTE: distinct from uAthena's mercenary.c (the HOMUNCULUS, merc_hom_*).
// uAthena adaptations vs the eAthena original:
//   - rand() -> rnd() (central PRNG)
//   - sv_readdb (absent here) -> hand-rolled comma parsers, like quest/achievement
//   - merc_contract_end timer id is intptr_t (uAthena TimerFunc), map_id2sd((int)id)
//   - no unit_calc_pos() here -> spawn on the master's cell (the homun idiom)

#include "../common/cbasetypes.h"
#include "../common/malloc.h"
#include "../common/socket.h"
#include "../common/timer.h"
#include "../common/nullpo.h"
#include "../common/mmo.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "../common/utils.h"

#include "log.h"
#include "clif.h"
#include "chrif.h"
#include "intif.h"
#include "itemdb.h"
#include "map.h"
#include "pc.h"
#include "status.h"
#include "skill.h"
#include "mob.h"
#include "pet.h"
#include "battle.h"
#include "party.h"
#include "guild.h"
#include "atcommand.h"
#include "script.h"
#include "npc.h"
#include "trade.h"
#include "unit.h"
#include "mercenary_soldier.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <time.h>
#include <math.h>

struct s_mercenary_db mercenary_db[MAX_MERCENARY_CLASS]; // Mercenary Database

int merc_search_index(int class_)
{
	int i;
	ARR_FIND(0, MAX_MERCENARY_CLASS, i, mercenary_db[i].class_ == class_);
	return (i == MAX_MERCENARY_CLASS)?-1:i;
}

bool merc_class(int class_)
{
	return (bool)(merc_search_index(class_) > -1);
}

struct view_data * merc_get_viewdata(int class_)
{
	int i = merc_search_index(class_);
	if( i < 0 )
		return 0;

	return &mercenary_db[i].vd;
}

int merc_create(struct map_session_data *sd, int class_, unsigned int lifetime)
{
	struct s_mercenary merc;
	struct s_mercenary_db *db;
	int i;
	nullpo_retr(0,sd);

	if( (i = merc_search_index(class_)) < 0 )
		return 0;

	db = &mercenary_db[i];
	memset(&merc,0,sizeof(struct s_mercenary));

	merc.char_id = sd->status.char_id;
	merc.class_ = class_;
	merc.hp = db->status.max_hp;
	merc.sp = db->status.max_sp;
	merc.life_time = lifetime;

	// Request Char Server to create this mercenary
	intif_mercenary_create(&merc);

	return 1;
}

int mercenary_get_lifetime(struct mercenary_data *md)
{
	const struct TimerData * td;
	if( md == NULL || md->contract_timer == INVALID_TIMER )
		return 0;

	td = get_timer(md->contract_timer);
	return (td != NULL) ? DIFF_TICK(td->tick, gettick()) : 0;
}

int mercenary_get_guild(struct mercenary_data *md)
{
	int class_;

	if( md == NULL || md->db == NULL )
		return -1;

	class_ = md->db->class_;

	if( class_ >= 6017 && class_ <= 6026 )
		return ARCH_MERC_GUILD;
	if( class_ >= 6027 && class_ <= 6036 )
		return SPEAR_MERC_GUILD;
	if( class_ >= 6037 && class_ <= 6046 )
		return SWORD_MERC_GUILD;

	return -1;
}

int mercenary_get_faith(struct mercenary_data *md)
{
	struct map_session_data *sd;
	int class_;

	if( md == NULL || md->db == NULL || (sd = md->master) == NULL )
		return 0;

	class_ = md->db->class_;

	if( class_ >= 6017 && class_ <= 6026 )
		return sd->status.arch_faith;
	if( class_ >= 6027 && class_ <= 6036 )
		return sd->status.spear_faith;
	if( class_ >= 6037 && class_ <= 6046 )
		return sd->status.sword_faith;

	return 0;
}

int mercenary_set_faith(struct mercenary_data *md, int value)
{
	struct map_session_data *sd;
	int class_, *faith;

	if( md == NULL || md->db == NULL || (sd = md->master) == NULL )
		return 0;

	class_ = md->db->class_;

	if( class_ >= 6017 && class_ <= 6026 )
		faith = &sd->status.arch_faith;
	else if( class_ >= 6027 && class_ <= 6036 )
		faith = &sd->status.spear_faith;
	else if( class_ >= 6037 && class_ <= 6046 )
		faith = &sd->status.sword_faith;
	else
		return 0;

	*faith += value;
	*faith = cap_value(*faith, 0, SHRT_MAX);
	clif_mercenary_updatestatus(sd, SP_MERCFAITH);

	return 0;
}

int mercenary_get_calls(struct mercenary_data *md)
{
	struct map_session_data *sd;
	int class_;

	if( md == NULL || md->db == NULL || (sd = md->master) == NULL )
		return 0;

	class_ = md->db->class_;

	if( class_ >= 6017 && class_ <= 6026 )
		return sd->status.arch_calls;
	if( class_ >= 6027 && class_ <= 6036 )
		return sd->status.spear_calls;
	if( class_ >= 6037 && class_ <= 6046 )
		return sd->status.sword_calls;

	return 0;
}

int mercenary_set_calls(struct mercenary_data *md, int value)
{
	struct map_session_data *sd;
	int class_, *calls;

	if( md == NULL || md->db == NULL || (sd = md->master) == NULL )
		return 0;

	class_ = md->db->class_;

	if( class_ >= 6017 && class_ <= 6026 )
		calls = &sd->status.arch_calls;
	else if( class_ >= 6027 && class_ <= 6036 )
		calls = &sd->status.spear_calls;
	else if( class_ >= 6037 && class_ <= 6046 )
		calls = &sd->status.sword_calls;
	else
		return 0;

	*calls += value;
	*calls = cap_value(*calls, 0, INT_MAX);

	return 0;
}

int mercenary_save(struct mercenary_data *md)
{
	md->mercenary.hp = md->battle_status.hp;
	md->mercenary.sp = md->battle_status.sp;
	md->mercenary.life_time = mercenary_get_lifetime(md);

	intif_mercenary_save(&md->mercenary);
	return 1;
}

static int merc_contract_end(int tid, unsigned int tick, intptr_t id, intptr_t data)
{
	struct map_session_data *sd;
	struct mercenary_data *md;

	if( (sd = map_id2sd((int)id)) == NULL )
		return 1;
	if( (md = sd->md) == NULL )
		return 1;

	if( md->contract_timer != tid )
	{
		ShowError("merc_contract_end %d != %d.\n", md->contract_timer, tid);
		return 0;
	}

	md->contract_timer = INVALID_TIMER;
	merc_delete(md, 0); // Mercenary soldier's duty hour is over.

	return 0;
}

int merc_delete(struct mercenary_data *md, int reply)
{
	struct map_session_data *sd = md->master;
	md->mercenary.life_time = 0;

	merc_contract_stop(md);

	if( !sd )
		return unit_free(&md->bl, 0 /*CLR_OUTSIGHT*/);

	if( md->devotion_flag )
	{
		md->devotion_flag = 0;
		status_change_end(&sd->bl, SC_DEVOTION, INVALID_TIMER);
	}

	switch( reply )
	{
		case 0: mercenary_set_faith(md, 1); break; // +1 Loyalty on Contract ends.
		case 1: mercenary_set_faith(md, -1); break; // -1 Loyalty on Mercenary killed
	}

	clif_mercenary_message(sd, reply);
	return unit_remove_map(&md->bl, 0 /*CLR_OUTSIGHT*/);
}

void merc_contract_stop(struct mercenary_data *md)
{
	nullpo_retv(md);
	if( md->contract_timer != INVALID_TIMER )
		delete_timer(md->contract_timer, merc_contract_end);
	md->contract_timer = INVALID_TIMER;
}

void merc_contract_init(struct mercenary_data *md)
{
	if( md->contract_timer == INVALID_TIMER )
		md->contract_timer = add_timer(gettick() + md->mercenary.life_time, merc_contract_end, md->master->bl.id, 0);

	md->regen.state.block = 0;
}

int merc_data_received(struct s_mercenary *merc, bool flag)
{
	struct map_session_data *sd;
	struct mercenary_data *md;
	struct s_mercenary_db *db;
	int i = merc_search_index(merc->class_);

	if( (sd = map_charid2sd(merc->char_id)) == NULL )
		return 0;
	if( !flag || i < 0 )
	{ // Not created - loaded - DB info
		sd->status.mer_id = 0;
		return 0;
	}

	db = &mercenary_db[i];
	if( !sd->md )
	{
		sd->md = md = (struct mercenary_data*)aCalloc(1,sizeof(struct mercenary_data));
		md->bl.type = BL_MER;
		md->bl.id = npc_get_new_npc_id();
		md->devotion_flag = 0;

		md->master = sd;
		md->db = db;
		memcpy(&md->mercenary, merc, sizeof(struct s_mercenary));
		status_set_viewdata(&md->bl, md->mercenary.class_);
		status_change_init(&md->bl);
		unit_dataset(&md->bl);
		md->ud.dir = sd->ud.dir;

		md->bl.m = sd->bl.m;
		md->bl.x = sd->bl.x;
		md->bl.y = sd->bl.y;

		map_addiddb(&md->bl);
		status_calc_mercenary(md,1);
		md->contract_timer = INVALID_TIMER;
		merc_contract_init(md);
	}
	else
	{
		memcpy(&sd->md->mercenary, merc, sizeof(struct s_mercenary));
		md = sd->md;
	}

	if( sd->status.mer_id == 0 )
		mercenary_set_calls(md, 1);
	sd->status.mer_id = merc->mercenary_id;

	if( md && md->bl.prev == NULL && sd->bl.prev != NULL )
	{
		map_addblock(&md->bl);
		clif_spawn(&md->bl);
		clif_mercenary_info(sd);
		clif_mercenary_skillblock(sd);
	}

	return 1;
}

void mercenary_damage(struct mercenary_data *md, struct block_list *src, int hp, int sp)
{
	if( hp )
		clif_mercenary_updatestatus(md->master, SP_HP);
	if( sp )
		clif_mercenary_updatestatus(md->master, SP_SP);
}

void mercenary_heal(struct mercenary_data *md, int hp, int sp)
{
	if( hp )
		clif_mercenary_updatestatus(md->master, SP_HP);
	if( sp )
		clif_mercenary_updatestatus(md->master, SP_SP);
}

int mercenary_dead(struct mercenary_data *md, struct block_list *src)
{
	merc_delete(md, 1);
	return 0;
}

int mercenary_killbonus(struct mercenary_data *md)
{
	const int scs[] = { SC_MERC_FLEEUP, SC_MERC_ATKUP, SC_MERC_HPUP, SC_MERC_SPUP, SC_MERC_HITUP };	// uAthena sc enum is anonymous
	int index = rnd() % ARRAYLENGTH(scs);

	status_change_start(&md->bl, scs[index], 10000, rnd()%5, 0, 0, 0, 600000, 0);
	return 0;
}

int mercenary_kills(struct mercenary_data *md)
{
	md->mercenary.kill_count++;
	md->mercenary.kill_count = cap_value(md->mercenary.kill_count, 0, INT_MAX);

	if( (md->mercenary.kill_count % 50) == 0 )
	{
		mercenary_set_faith(md, 1);
		mercenary_killbonus(md);
	}

	if( md->master )
		clif_mercenary_updatestatus(md->master, SP_MERCKILLS);

	return 0;
}

int mercenary_checkskill(struct mercenary_data *md, int skill_id)
{
	int i = skill_id - MC_SKILLBASE;

	if( !md || !md->db )
		return 0;
	if( i < 0 || i >= MAX_MERCSKILL )
		return 0;
	if( md->db->skill[i].id == skill_id )
		return md->db->skill[i].lv;

	return 0;
}

// [Backport] hand-rolled comma parser (uAthena has no sv_readdb).
// mercenary_db.txt: 26 numeric/text fields, '//' line comments.
static int read_mercenarydb(void)
{
	FILE *fp;
	char line[1024];
	int k = 0;

	memset(mercenary_db, 0, sizeof(mercenary_db));
	sprintf(line, "%s/mercenary_db.txt", db_path);
	if( (fp = fopen(line, "r")) == NULL ) {
		ShowError("can't read %s/mercenary_db.txt\n", db_path);
		return -1;
	}

	while( fgets(line, sizeof(line), fp) )
	{
		char *str[26], *p, *np;
		int i, ele;
		struct s_mercenary_db *db;
		struct status_data *status;

		if( line[0] == '/' && line[1] == '/' )
			continue;
		if( line[0] == '\r' || line[0] == '\n' )
			continue;
		if( k >= MAX_MERCENARY_CLASS ) {
			ShowError("read_mercenarydb: Too many entries in mercenary_db.txt (max %d).\n", MAX_MERCENARY_CLASS);
			break;
		}

		p = line;
		for( i = 0; i < 26; i++ ) {
			str[i] = p;
			if( i < 25 ) {
				if( (np = strchr(p, ',')) == NULL )
					break;
				*np = 0;
				p = np + 1;
			}
		}
		if( i < 26 ) // malformed (fewer than 26 fields)
			continue;

		db = &mercenary_db[k];
		db->class_ = atoi(str[0]);
		strncpy(db->sprite, str[1], NAME_LENGTH);
		strncpy(db->name, str[2], NAME_LENGTH);
		db->lv = atoi(str[3]);

		status = &db->status;
		db->vd.class_ = db->class_;

		status->max_hp = atoi(str[4]);
		status->max_sp = atoi(str[5]);
		status->rhw.range = atoi(str[6]);
		status->rhw.atk = atoi(str[7]);
		status->rhw.atk2 = status->rhw.atk + atoi(str[8]);
		status->def = atoi(str[9]);
		status->mdef = atoi(str[10]);
		status->str = atoi(str[11]);
		status->agi = atoi(str[12]);
		status->vit = atoi(str[13]);
		status->int_ = atoi(str[14]);
		status->dex = atoi(str[15]);
		status->luk = atoi(str[16]);
		db->range2 = atoi(str[17]);
		db->range3 = atoi(str[18]);
		status->size = atoi(str[19]);
		status->race = atoi(str[20]);

		ele = atoi(str[21]);
		status->def_ele = ele%10;
		status->ele_lv = ele/20;
		if( status->def_ele >= ELE_MAX ) {
			ShowWarning("Mercenary %d has invalid element type %d (max element is %d)\n", db->class_, status->def_ele, ELE_MAX - 1);
			status->def_ele = ELE_NEUTRAL;
		}
		if( status->ele_lv < 1 || status->ele_lv > 4 ) {
			ShowWarning("Mercenary %d has invalid element level %d (max is 4)\n", db->class_, status->ele_lv);
			status->ele_lv = 1;
		}

		status->aspd_rate = 1000;
		status->speed = atoi(str[22]);
		status->adelay = atoi(str[23]);
		status->amotion = atoi(str[24]);
		status->dmotion = atoi(str[25]);

		k++;
	}
	fclose(fp);
	ShowStatus("Done reading '"CL_WHITE"%d"CL_RESET"' entries in '"CL_WHITE"%s"CL_RESET"'.\n", k, "mercenary_db.txt");
	return 0;
}

// mercenary_skill_db.txt: <merc class>,<skill id>,<skill level>
static int read_mercenary_skilldb(void)
{
	FILE *fp;
	char line[1024];
	int count = 0;

	sprintf(line, "%s/mercenary_skill_db.txt", db_path);
	if( (fp = fopen(line, "r")) == NULL ) {
		ShowError("can't read %s/mercenary_skill_db.txt\n", db_path);
		return -1;
	}

	while( fgets(line, sizeof(line), fp) )
	{
		char *str[3], *p, *np;
		int i, class_, skillid, skilllv;
		struct s_mercenary_db *db;

		if( line[0] == '/' && line[1] == '/' )
			continue;
		if( line[0] == '\r' || line[0] == '\n' )
			continue;

		p = line;
		for( i = 0; i < 3; i++ ) {
			str[i] = p;
			if( i < 2 ) {
				if( (np = strchr(p, ',')) == NULL )
					break;
				*np = 0;
				p = np + 1;
			}
		}
		if( i < 3 )
			continue;

		class_ = atoi(str[0]);
		ARR_FIND(0, MAX_MERCENARY_CLASS, i, class_ == mercenary_db[i].class_);
		if( i == MAX_MERCENARY_CLASS ) {
			ShowError("read_mercenary_skilldb : Class %d not found in mercenary_db for skill entry.\n", class_);
			continue;
		}

		skillid = atoi(str[1]);
		if( skillid < MC_SKILLBASE || skillid >= MC_SKILLBASE + MAX_MERCSKILL ) {
			ShowError("read_mercenary_skilldb : Skill %d out of range.\n", skillid);
			continue;
		}

		db = &mercenary_db[i];
		skilllv = atoi(str[2]);

		i = skillid - MC_SKILLBASE;
		db->skill[i].id = skillid;
		db->skill[i].lv = skilllv;
		count++;
	}
	fclose(fp);
	ShowStatus("Done reading '"CL_WHITE"%d"CL_RESET"' entries in '"CL_WHITE"%s"CL_RESET"'.\n", count, "mercenary_skill_db.txt");
	return 0;
}

//=========================================================
// [Backport] Custom Mercenary Soldier AI.
// eAthena has no autonomous merc AI — the player drives it via the merc skill
// window, which is dormant under PV7. This self-contained AI (modelled on the
// pet AI) makes the mercenary follow its master, auto-aggro nearby enemies and
// melee them. Skill auto-cast is layered on in a later milestone.
//=========================================================
#define MIN_MERCTHINKTIME 100
#define MERC_MAX_DISTANCE 13	// master leash: farther than this -> run back
#define MERC_FOLLOW_DISTANCE 3	// idle: stay within this of the master

// Find the closest valid enemy in sight (mirrors mob_ai_sub_hard_activesearch).
static int merc_ai_sub_hard_activesearch(struct block_list *bl, va_list ap)
{
	struct mercenary_data *md;
	struct block_list **target;
	int dist;

	nullpo_ret(bl);
	md = va_arg(ap, struct mercenary_data *);
	target = va_arg(ap, struct block_list**);

	if( (*target) == bl || !status_check_skilluse(&md->bl, bl, 0, 0) )
		return 0;
	if( battle_check_target(&md->bl, bl, BCT_ENEMY) <= 0 )
		return 0;

	dist = distance_bl(&md->bl, bl);
	if( ((*target) == NULL || !check_distance_bl(&md->bl, *target, dist)) &&
		battle_check_range(&md->bl, bl, md->db->range2) )
	{
		(*target) = bl;
		md->ud.target = bl->id;
		return 1;
	}
	return 0;
}

static int merc_ai_sub_hard(struct mercenary_data *md, struct map_session_data *sd, unsigned int tick)
{
	struct block_list *target = NULL;

	if( md->bl.prev == NULL || sd == NULL || sd->bl.prev == NULL )
		return 0;

	if( DIFF_TICK(tick, md->last_thinktime) < MIN_MERCTHINKTIME )
		return 0;
	md->last_thinktime = tick;

	if( md->ud.skilltimer != -1 )
		return 0; // casting
	if( md->bl.m != sd->bl.m )
		return 0; // master on another map (handled on map change)
	if( md->ud.walktimer != -1 && md->ud.walkpath.path_pos <= 2 )
		return 0; // just started walking

	// Master too far -> run back to him (drop any target)
	if( !check_distance_bl(&sd->bl, &md->bl, MERC_MAX_DISTANCE) )
	{
		if( md->ud.walktimer != -1 && md->ud.target == sd->bl.id )
			return 0; // already heading there
		if( DIFF_TICK(tick, md->ud.canmove_tick) < 0 )
			return 0;
		unit_walktobl(&md->bl, &sd->bl, 3, 0);
		return 0;
	}

	// Validate the current target
	if( md->ud.target )
	{
		target = map_id2bl(md->ud.target);
		if( target == NULL || md->bl.m != target->m || status_isdead(target) ||
			!check_distance_bl(&md->bl, target, md->db->range3) ||
			battle_check_target(&md->bl, target, BCT_ENEMY) <= 0 )
			target = NULL;
	}

	// No target and idle -> look for a nearby enemy (auto-aggro)
	if( target == NULL && md->ud.attacktimer == -1 )
		map_foreachinrange(merc_ai_sub_hard_activesearch, &md->bl, md->db->range2, BL_CHAR, md, &target);

	if( target == NULL )
	{	// Nothing to fight: stay close to the master
		if( md->ud.attacktimer != -1 || md->ud.walktimer != -1 )
			return 0;
		if( check_distance_bl(&sd->bl, &md->bl, MERC_FOLLOW_DISTANCE) )
			return 0; // already next to him
		unit_walktobl(&md->bl, &sd->bl, MERC_FOLLOW_DISTANCE, 0);
		return 0;
	}

	// Engage the target
	if( md->ud.target == target->id && (md->ud.attacktimer != -1 || md->ud.walktimer != -1) )
		return 0; // already locked on

	if( !battle_check_range(&md->bl, target, md->battle_status.rhw.range) )
	{	// Out of range -> chase
		if( !unit_walktobl(&md->bl, target, md->battle_status.rhw.range, 2) )
			md->ud.target = 0; // unreachable
		return 0;
	}
	unit_attack(&md->bl, target->id, 1); // continuous melee
	return 0;
}

static int merc_ai_sub_foreachclient(struct map_session_data *sd, va_list ap)
{
	unsigned int tick = va_arg(ap, unsigned int);
	if( sd->md && sd->md->bl.prev != NULL )
		merc_ai_sub_hard(sd->md, sd, tick);
	return 0;
}

static int merc_ai_hard(int tid, unsigned int tick, intptr_t id, intptr_t data)
{
	clif_foreachclient(merc_ai_sub_foreachclient, tick);
	return 0;
}

int do_init_mercenary(void)
{
	read_mercenarydb();
	read_mercenary_skilldb();

	add_timer_func_list(merc_ai_hard, "merc_ai_hard");
	add_timer_interval(gettick()+MIN_MERCTHINKTIME, merc_ai_hard, 0, 0, MIN_MERCTHINKTIME);

	return 0;
}

int do_final_mercenary(void)
{
	return 0;
}
