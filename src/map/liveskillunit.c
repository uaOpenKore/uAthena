// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Flat-array index of every live skill_unit — see liveskillunit.h. [perf]

#include <string.h>

#ifdef LIVESKILLUNIT_TEST
// Test build: structs come from liveskillunit.h (under LIVESKILLUNIT_TEST); just
// stub the allocator + the deferred-free lock the index calls around iteration.
#include <stdlib.h>
#define aMalloc(n)     malloc(n)
#define aRealloc(p,n)  realloc(p,n)
#define aFree(p)       free(p)
static int map_freeblock_lock(void)   { return 0; }
static int map_freeblock_unlock(void) { return 0; }
#else
#include "../common/malloc.h"
#include "map.h"            // struct block_list, struct skill_unit
extern int map_freeblock_lock(void);
extern int map_freeblock_unlock(void);
#endif

#include "liveskillunit.h"

#define LIVESKILLUNIT_MIN_CAP 256

// Live skill units, contiguous. Each unit caches its own slot in
// skill_unit.liveskillunit_idx so removal is O(1) (swap with the last).
static struct block_list **lsu_arr = NULL;
static int lsu_count = 0;
static int lsu_cap   = 0;

// Reusable snapshot buffer for liveskillunit_foreach (grown, never shrunk).
static struct block_list **lsu_snap = NULL;
static int lsu_snap_cap = 0;

#define LSUIDX(bl) (((struct skill_unit*)(bl))->liveskillunit_idx)

void liveskillunit_init(void)
{
	if (lsu_arr == NULL) {
		lsu_cap = LIVESKILLUNIT_MIN_CAP;
		lsu_arr = (struct block_list**)aMalloc(lsu_cap * sizeof(*lsu_arr));
	}
	lsu_count = 0;
}

void liveskillunit_final(void)
{
	if (lsu_arr)  { aFree(lsu_arr);  lsu_arr  = NULL; }
	if (lsu_snap) { aFree(lsu_snap); lsu_snap = NULL; }
	lsu_count = lsu_cap = lsu_snap_cap = 0;
}

void liveskillunit_add(struct block_list *bl)
{
	if (bl == NULL)
		return;
	if (lsu_count >= lsu_cap) {
		lsu_cap = lsu_cap ? lsu_cap * 2 : LIVESKILLUNIT_MIN_CAP;
		lsu_arr = (struct block_list**)aRealloc(lsu_arr, lsu_cap * sizeof(*lsu_arr));
	}
	LSUIDX(bl) = lsu_count;
	lsu_arr[lsu_count++] = bl;
}

void liveskillunit_remove(struct block_list *bl)
{
	int i;
	if (bl == NULL)
		return;
	i = LSUIDX(bl);
	// Ignore units that were never indexed (idx still 0 from calloc but not us,
	// or already removed) — exactly like livemob_remove.
	if (i < 0 || i >= lsu_count || lsu_arr[i] != bl)
		return;
	lsu_count--;
	if (i != lsu_count) {               // move the last element into the gap
		lsu_arr[i] = lsu_arr[lsu_count];
		LSUIDX(lsu_arr[i]) = i;
	}
	lsu_arr[lsu_count] = NULL;
	LSUIDX(bl) = -1;                    // mark removed
}

void liveskillunit_foreach(int (*func)(struct block_list*, va_list), ...)
{
	int i, n = lsu_count;
	va_list ap;

	if (n <= 0 || func == NULL)
		return;

	va_start(ap, func);

	// Snapshot the current live set so add/remove during the pass is safe.
	if (lsu_snap_cap < n) {
		lsu_snap_cap = lsu_cap;
		lsu_snap = (struct block_list**)aRealloc(lsu_snap, lsu_snap_cap * sizeof(*lsu_snap));
	}
	memcpy(lsu_snap, lsu_arr, (size_t)n * sizeof(*lsu_snap));

	// Defer skill-unit/group frees triggered by the callback (group->unit is
	// freed via the deferred map_freeblock) so snapshot pointers stay valid.
	map_freeblock_lock();
	for (i = 0; i < n; i++) {
		struct block_list *bl = lsu_snap[i];
		if (LSUIDX(bl) < 0)             // removed from the index during this pass
			continue;
		{ va_list apc; va_copy(apc, ap); func(bl, apc); va_end(apc); }
	}
	map_freeblock_unlock();
	va_end(ap);
}
