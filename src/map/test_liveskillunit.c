// Standalone unit test for the flat-array live skill-unit index (liveskillunit.c).
//
// Not part of `make sql`. Build & run with:
//   gcc -DLIVESKILLUNIT_TEST -fsanitize=address,undefined -I src/map \
//       -o /tmp/test_liveskillunit src/map/liveskillunit.c src/map/test_liveskillunit.c
//   /tmp/test_liveskillunit
//
// Exercises swap-remove bookkeeping and the snapshot iteration that must stay
// correct when the callback adds/removes units mid-pass (an off-by-one would
// silently drop a live AoE/trap from the 100ms tick).

#include "liveskillunit.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#define N 50
static struct skill_unit units[N];
static int fails = 0;

#define CHECK(cond, msg) do{ if(!(cond)){ printf("FAIL: %s\n", msg); fails++; } }while(0)

static struct block_list *BL(int i){ return &units[i].bl; }

// --- foreach callbacks ----------------------------------------------------
static int g_visits[N], g_nvisit;
static int cb_count(struct block_list *bl, va_list ap){ (void)ap; g_visits[g_nvisit++] = bl->id; return 0; }

// removes the CURRENT unit and one other (id+1) mid-pass
static int cb_remove(struct block_list *bl, va_list ap){
	int other;
	(void)ap;
	g_visits[g_nvisit++] = bl->id;
	liveskillunit_remove(bl);
	other = bl->id + 1;
	if (other < N) liveskillunit_remove(BL(other));
	return 0;
}

// checks tick is passed through varargs intact
static unsigned int g_seen_tick;
static int cb_tick(struct block_list *bl, va_list ap){ (void)bl; g_seen_tick = (unsigned int)va_arg(ap, unsigned int); return 0; }

int main(void)
{
	int i;

	for (i = 0; i < N; i++){ memset(&units[i],0,sizeof(units[i])); units[i].bl.id = i; units[i].liveskillunit_idx = -1; }

	liveskillunit_init();

	// 1) add all -> all visited exactly once
	for (i = 0; i < N; i++) liveskillunit_add(BL(i));
	g_nvisit = 0; liveskillunit_foreach(cb_count, 0);
	CHECK(g_nvisit == N, "foreach should visit every added unit");

	// 2) swap-remove a middle unit; the moved-up unit must keep a valid idx and
	//    still be iterated; the removed one must not.
	liveskillunit_remove(BL(10));
	CHECK(units[10].liveskillunit_idx == -1, "removed unit idx must be -1");
	g_nvisit = 0; liveskillunit_foreach(cb_count, 0);
	CHECK(g_nvisit == N-1, "foreach must visit N-1 after one removal");
	for (i = 0; i < g_nvisit; i++) CHECK(g_visits[i] != 10, "removed unit must not be visited");

	// 3) double-remove / never-added is a no-op (idx guard)
	liveskillunit_remove(BL(10));   // already removed
	g_nvisit = 0; liveskillunit_foreach(cb_count, 0);
	CHECK(g_nvisit == N-1, "double-remove must not change the set");

	// 4) mid-pass removal: callback removes itself + neighbour. Must not crash,
	//    must not visit a unit that was swap-removed before we reached it.
	liveskillunit_final(); liveskillunit_init();
	for (i = 0; i < N; i++){ units[i].liveskillunit_idx = -1; liveskillunit_add(BL(i)); }
	g_nvisit = 0; liveskillunit_foreach(cb_remove, 0);
	CHECK(g_nvisit > 0 && g_nvisit <= N, "mid-pass removal must terminate sanely");
	// every visited id must be unique (no double-visit from swap-during-pass)
	for (i = 0; i < g_nvisit; i++){ int j; for (j=i+1;j<g_nvisit;j++) CHECK(g_visits[i]!=g_visits[j],"no id visited twice"); }
	// after the pass the index must be empty or consistent (re-iterate -> no crash)
	g_nvisit = 0; liveskillunit_foreach(cb_count, 0);

	// 5) varargs tick passthrough
	liveskillunit_final(); liveskillunit_init();
	liveskillunit_add(BL(0));
	g_seen_tick = 0; liveskillunit_foreach(cb_tick, (unsigned int)123456u);
	CHECK(g_seen_tick == 123456u, "tick must pass through varargs intact");

	liveskillunit_final();

	if (fails == 0) printf("test_liveskillunit: ALL PASS\n");
	else            printf("test_liveskillunit: %d FAILURE(S)\n", fails);
	return fails ? 1 : 0;
}
