// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// See livemob.h. [perf]

#include "livemob.h"

#include <string.h>

#ifdef LIVEMOB_TEST
#include <stdlib.h>
#define aMalloc(n)     malloc(n)
#define aRealloc(p,n)  realloc((p),(n))
#define aFree(p)       free(p)
extern int map_freeblock_lock(void);
extern int map_freeblock_unlock(void);
#else
#include "../common/cbasetypes.h"
#include "../common/malloc.h"
#include "map.h"   // struct block_list, struct mob_data, map_freeblock_lock/unlock
#endif

#define LIVEMOB_MIN_CAP 4096

// Live mobs, contiguous. Each mob caches its own slot in mob_data.livemob_idx
// so removal is O(1) (swap with the last element). RAM: one pointer per live
// mob plus an equal-sized iteration snapshot - a few tens of KB. [perf]
static struct block_list **livemob_arr = NULL;
static int livemob_count = 0;
static int livemob_cap   = 0;

// Snapshot taken at the start of each pass so the callback may freely mutate
// the live array (kill/spawn mobs) without disturbing the iteration.
static struct block_list **livemob_snap = NULL;
static int livemob_snap_cap = 0;

#define MOBIDX(bl) (((struct mob_data*)(bl))->livemob_idx)

void livemob_init(void)
{
	if (livemob_arr == NULL) {
		livemob_cap = LIVEMOB_MIN_CAP;
		livemob_arr = (struct block_list**)aMalloc(livemob_cap * sizeof(*livemob_arr));
	}
	livemob_count = 0;
}

void livemob_final(void)
{
	if (livemob_arr)  { aFree(livemob_arr);  livemob_arr  = NULL; }
	if (livemob_snap) { aFree(livemob_snap); livemob_snap = NULL; }
	livemob_count = livemob_cap = livemob_snap_cap = 0;
}

void livemob_add(struct block_list *bl)
{
	if (bl == NULL) return;
	if (livemob_count >= livemob_cap) {
		livemob_cap = livemob_cap ? livemob_cap * 2 : LIVEMOB_MIN_CAP;
		livemob_arr = (struct block_list**)aRealloc(livemob_arr, livemob_cap * sizeof(*livemob_arr));
	}
	MOBIDX(bl) = livemob_count;
	livemob_arr[livemob_count++] = bl;
}

void livemob_remove(struct block_list *bl)
{
	int i;
	if (bl == NULL) return;
	i = MOBIDX(bl);
	// Guard against a never-added / already-removed mob: the stored slot must
	// actually point back to this mob. (mob_data is aCalloc'd -> idx 0, so the
	// identity check is what makes a stale 0 safe.)
	if (i < 0 || i >= livemob_count || livemob_arr[i] != bl)
		return;
	livemob_count--;
	if (i != livemob_count) {           // move the last element into the gap
		livemob_arr[i] = livemob_arr[livemob_count];
		MOBIDX(livemob_arr[i]) = i;
	}
	livemob_arr[livemob_count] = NULL;
	MOBIDX(bl) = -1;                     // mark removed (analogue of node->deleted)
}

void livemob_foreach(int (*func)(DBKey, void*, va_list), va_list ap)
{
	int i, n = livemob_count;

	if (n <= 0 || func == NULL)
		return;

	// Snapshot the current live set. Grown to the live capacity and kept.
	if (livemob_snap_cap < n) {
		livemob_snap_cap = livemob_cap;
		livemob_snap = (struct block_list**)aRealloc(livemob_snap, livemob_snap_cap * sizeof(*livemob_snap));
	}
	memcpy(livemob_snap, livemob_arr, (size_t)n * sizeof(*livemob_snap));

	// Defer mob frees triggered by the AI so snapshot pointers stay valid.
	map_freeblock_lock();
	for (i = 0; i < n; i++) {
		struct block_list *bl = livemob_snap[i];
		DBKey key;
		if (MOBIDX(bl) < 0)             // removed from the index during this pass
			continue;
		key.i = bl->id;
		{ va_list apc; va_copy(apc, ap); func(key, bl, apc); va_end(apc); }
	}
	map_freeblock_unlock();
}
