// Standalone unit test for the element-mark rules (elemark.h).
//
// Not part of `make sql`. Build & run with:
//   gcc -Wall -I src/map -o /tmp/test_elemark src/map/test_elemark.c
//   /tmp/test_elemark
//
// The rules (S. 2026-11-17): a player's hit whose element passes below 100% marks the monster; the next
// player hit on it uses the mark up, and if that hit's element passes above 100% its bonus doubles
// (175% -> 250%). Resists are never strengthened, the hit that uses a mark never marks again, a miss
// neither sets nor uses a mark.

#include "elemark.h"

#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

// One hit on a monster, the way battle.c applies the rules: the ratio the hit deals (with the boost when the
// monster was marked before it), then the mark state after it. Returns the ratio dealt.
static int hit(int *marked, int landed, int table_ratio)
{
	int dealt = *marked ? elemark_boost_ratio(table_ratio) : table_ratio;
	*marked = elemark_after_hit(*marked, landed, table_ratio < 100);
	return dealt;
}

int main(void)
{
	int marked, a, b, c, d;

	// --- the boost on the hit that uses a mark: only the part above 100% doubles ---
	CHECK(elemark_boost_ratio(175) == 250, "Wind on Water 1: 175% -> 250%");
	CHECK(elemark_boost_ratio(150) == 200, "150% -> 200%");
	CHECK(elemark_boost_ratio(125) == 150, "125% -> 150%");
	CHECK(elemark_boost_ratio(200) == 300, "200% -> 300%");
	CHECK(elemark_boost_ratio(100) == 100, "100% stays 100%");
	CHECK(elemark_boost_ratio(50) == 50, "a resist is not strengthened: 50% stays 50%");
	CHECK(elemark_boost_ratio(0) == 0, "immune stays immune");
	CHECK(elemark_boost_ratio(-25) == -25, "healing is not strengthened");

	// --- the mark state ---
	CHECK(elemark_after_hit(0, 1, 1) == 1, "a landed hit below 100% marks");
	CHECK(elemark_after_hit(0, 1, 0) == 0, "a landed hit at 100% or more does not mark");
	CHECK(elemark_after_hit(1, 1, 0) == 0, "the next landed hit uses the mark up");
	CHECK(elemark_after_hit(1, 1, 1) == 0, "the hit that uses the mark never marks again");
	CHECK(elemark_after_hit(0, 0, 1) == 0, "a miss does not mark");
	CHECK(elemark_after_hit(1, 0, 0) == 1, "a miss does not use the mark up");

	// --- S.'s example: Poring (Water 1). Fire 50% marks, the Wind hit after it deals 250% instead of 175% ---
	marked = 0;
	a = hit(&marked, 1, 50);   // Fire
	b = hit(&marked, 1, 175);  // Wind, uses the mark
	c = hit(&marked, 1, 175);  // Wind again, no mark left
	CHECK(a == 50 && b == 250 && c == 175 && marked == 0, "Poring: Fire 50, Wind 250, Wind 175");

	// --- a mark waits for the next hit however long it takes (no timer); a miss in between keeps it ---
	marked = 0;
	hit(&marked, 1, 50);
	b = hit(&marked, 0, 175);  // missed
	c = hit(&marked, 1, 175);
	CHECK(b == 250 && c == 250 && marked == 0, "a miss keeps the mark for the next landed hit");

	// --- neutral weapon on Giant Whisper (Ghost 2, 25%): marks every other hit and never heals ---
	marked = 0;
	a = hit(&marked, 1, 25);
	b = hit(&marked, 1, 25);
	c = hit(&marked, 1, 25);
	d = hit(&marked, 1, 25);
	CHECK(a == 25 && b == 25 && c == 25 && d == 25, "wrong element in a row: 25% every hit, the mob never heals");

	printf("%s (%d failure%s)\n", failures ? "FAILED" : "ALL PASSED", failures, failures == 1 ? "" : "s");
	return failures ? 1 : 0;
}
