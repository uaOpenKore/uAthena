// Standalone unit test for the «Натиск» weapon-streak rules (streak.h).
//
// Not part of `make sql`. Build & run with:
//   gcc -Wall -I src/map -o /tmp/test_streak src/map/test_streak.c
//   /tmp/test_streak
//
// The rules (S. 2026-11-17): every landed weapon hit a player lands on the same monster adds a step (+25% base
// attack: 100, 125, 150 ... up to the cap, 700% by default); a miss takes one step back; another monster - or the
// same id after a respawn - restarts the streak; a weapon skill the player uses spends the streak (its hits on the
// streak monster get the steps, then the streak restarts at 0); weapon/ammo change, death, teleport reset it.

#include "streak.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

#define STEP 25
#define MAX 700

// One passive hit (normal attack and the like) on monster `id`/`life`, the way battle.c applies the rules.
// Returns the base attack rate (%) the hit gets.
static int passive(struct streak_state *s, int id, unsigned int life, int landed)
{
	int rate = streak_rate(streak_passive_steps(s, id, life), STEP, MAX);
	streak_passive_done(s, landed, streak_max_count(STEP, MAX));
	return rate;
}

int main(void)
{
	struct streak_state s;
	int i, ok, rate;

	// --- rates and the cap ---
	CHECK(streak_rate(0, STEP, MAX) == 100, "first hit: 100%");
	CHECK(streak_rate(1, STEP, MAX) == 125, "second hit: 125%");
	CHECK(streak_rate(4, STEP, MAX) == 200, "fifth hit: 200%");
	CHECK(streak_rate(24, STEP, MAX) == 700, "25th hit: 700% (the cap)");
	CHECK(streak_rate(30, STEP, MAX) == 700, "never above the cap");
	CHECK(streak_rate(40, STEP, 0) == 1100, "max 0: no cap");
	CHECK(streak_max_count(STEP, MAX) == 24, "the count stops at the cap (24 steps)");

	// --- S.'s example: 100 - 125 - 150 - 175 - 200 on one monster ---
	memset(&s, 0, sizeof(s));
	ok = 1;
	for (i = 0; i < 5; i++)
		ok &= passive(&s, 1001, 50, 1) == 100 + 25*i;
	CHECK(ok, "same monster: 100, 125, 150, 175, 200");

	// --- up to the cap and it stays there ---
	memset(&s, 0, sizeof(s));
	for (i = 0; i < 30; i++)
		rate = passive(&s, 1001, 50, 1);
	CHECK(rate == 700 && s.count == 24, "30 hits: still 700%");

	// --- a miss takes one step back, never below zero ---
	memset(&s, 0, sizeof(s));
	passive(&s, 1001, 50, 1);   // 100
	passive(&s, 1001, 50, 1);   // 125
	passive(&s, 1001, 50, 1);   // 150, next would be 175
	passive(&s, 1001, 50, 0);   // miss
	CHECK(passive(&s, 1001, 50, 1) == 150, "a miss: the next hit is one step lower (150, not 175)");
	memset(&s, 0, sizeof(s));
	passive(&s, 1001, 50, 0);
	CHECK(s.count == 0 && passive(&s, 1001, 50, 1) == 100, "a miss at zero stays at zero");

	// --- another monster, or the same id after a respawn, restarts the streak ---
	memset(&s, 0, sizeof(s));
	for (i = 0; i < 4; i++)
		passive(&s, 1001, 50, 1);
	CHECK(passive(&s, 1002, 70, 1) == 100, "another monster: back to 100%");
	CHECK(passive(&s, 1001, 50, 1) == 100, "and back on the first one: 100% again");
	for (i = 0; i < 4; i++)
		passive(&s, 1001, 50, 1);
	CHECK(passive(&s, 1001, 90, 1) == 100, "the same id respawned (new spawn tick): 100%");

	// --- a weapon skill spends the streak ---
	memset(&s, 0, sizeof(s));
	for (i = 0; i < 5; i++)
		passive(&s, 1001, 50, 1);            // next step would be 225%
	streak_spend(&s, 5);                     // Bash
	CHECK(streak_rate(streak_spent_steps(&s, 5, 1001, 50), STEP, MAX) == 225,
		"Bash after 5 hits: 225% on the streak monster");
	CHECK(streak_spent_steps(&s, 5, 1002, 70) == 0, "the same skill on another monster: no bonus");
	CHECK(streak_spent_steps(&s, 7, 1001, 50) == 0, "another skill's hit: no bonus");
	CHECK(s.count == 0, "the skill restarts the streak at 0");
	CHECK(passive(&s, 1001, 50, 1) == 100, "the next normal hit: 100%");

	// --- a skill on another monster: spends the streak, no bonus anywhere ---
	memset(&s, 0, sizeof(s));
	for (i = 0; i < 3; i++)
		passive(&s, 1001, 50, 1);
	streak_spend(&s, 5);
	CHECK(streak_spent_steps(&s, 5, 1002, 70) == 0 && s.count == 0, "Bash on another monster: no bonus, streak 0");

	// --- resets ---
	memset(&s, 0, sizeof(s));
	for (i = 0; i < 6; i++)
		passive(&s, 1001, 50, 1);
	streak_spend(&s, 5);
	s.active = 1;
	streak_reset(&s);
	CHECK(s.count == 0 && s.target == 0 && streak_spent_steps(&s, 5, 1001, 50) == 0 && s.active == 1,
		"reset: no streak, no spent streak; a running skill window stays open");
	CHECK(passive(&s, 1001, 50, 1) == 100, "after a reset: 100%");

	printf("%s (%d failure%s)\n", failures ? "FAILED" : "ALL PASSED", failures, failures == 1 ? "" : "s");
	return failures ? 1 : 0;
}
