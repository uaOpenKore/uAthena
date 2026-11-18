// Copyright (c) uAthena / bornrok.com
// «Натиск» weapon streak (S. 2026-11-17). Every weapon hit a player lands on the same monster adds a step to the
// base attack (+25% each: 100, 125, 150 ... up to the cap, 700% by default); a miss takes one step back; another
// monster - or the same id after a respawn - restarts the streak; a weapon skill the player uses spends it (that
// skill's hits on the streak monster get the steps, then the streak restarts at 0). Pure rules only, so
// test_streak.c needs nothing else; battle.c / skill.c / pc.c apply them.
#ifndef _STREAK_H_
#define _STREAK_H_

struct streak_state {
	int target;          // block id of the streak monster (0 = none)
	unsigned int life;   // its spawn tick: a respawned monster keeps its id but starts a new streak
	int count;           // steps so far
	int active;          // >0 while a weapon skill the player used resolves (skill.c opens/closes the window)
	int snap_target, snap_count, snap_skill; // the streak that skill spent (streak_spend)
	unsigned int snap_life;
};

// Base attack rate (%) at `count` steps: 100 + step*count, at most `max` (max <= 0: no cap).
static inline int streak_rate(int count, int step, int max)
{
	int rate = 100 + step*count;
	if (max > 0 && rate > max)
		rate = max;
	return rate < 100 ? 100 : rate;
}

// Steps at which the rate reaches the cap; the count never grows past it (1000 when there is no cap).
static inline int streak_max_count(int step, int max)
{
	if (step <= 0)
		return 0;
	if (max <= 0)
		return 1000;
	return max > 100 ? (max - 100 + step - 1) / step : 0;
}

// Steps a passive hit (normal attack, Double Attack, Triple Attack, card autocast) on monster `target` gets.
// Another monster - or the same id with a new spawn tick - restarts the streak there.
static inline int streak_passive_steps(struct streak_state *s, int target, unsigned int life)
{
	if (s->target != target || s->life != life) {
		s->target = target;
		s->life = life;
		s->count = 0;
	}
	return s->count;
}

// After a passive hit: landed -> one step up (to max_count), miss -> one step back (not below 0).
static inline void streak_passive_done(struct streak_state *s, int landed, int max_count)
{
	if (landed) {
		if (s->count < max_count)
			s->count++;
	} else if (s->count > 0)
		s->count--;
}

// A weapon skill the player uses spends the streak: keep it for that skill's hits, restart the streak at 0.
static inline void streak_spend(struct streak_state *s, int skill)
{
	s->snap_target = s->target;
	s->snap_life = s->life;
	s->snap_count = s->count;
	s->snap_skill = skill;
	s->count = 0;
}

// Steps a hit of that skill (or its delayed hit) on monster `target` gets: the spent streak on its own monster,
// nothing on any other.
static inline int streak_spent_steps(const struct streak_state *s, int skill, int target, unsigned int life)
{
	return (skill == s->snap_skill && target == s->snap_target && life == s->snap_life) ? s->snap_count : 0;
}

// Weapon/ammo change, death, teleport or map change: no streak, no spent streak. A skill window that is open
// stays open (it closes itself when the skill finishes resolving).
static inline void streak_reset(struct streak_state *s)
{
	s->target = 0;
	s->life = 0;
	s->count = 0;
	s->snap_target = 0;
	s->snap_life = 0;
	s->snap_count = 0;
	s->snap_skill = 0;
}

#endif /* _STREAK_H_ */
