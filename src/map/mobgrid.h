// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Per-map coarse "is a player nearby" grid. Counts BL_PC|BL_HOM per map block
// (the DEFAULT_ENEMY_TYPE of a normal mob). A normal mob with no counted unit
// within its view_range provably cannot find an active-search target, so that
// area scan can be skipped. Counts are exact (every add +1, every remove -1),
// unlike block_count which is only an upper bound. [perf]

#ifndef _MOBGRID_H_
#define _MOBGRID_H_

// Must equal map.h BLOCK_SIZE. map.c #error-checks this.
#define MOBGRID_BLOCK 8

// pos is the block index (x/MOBGRID_BLOCK + (y/MOBGRID_BLOCK)*bxs), i.e. exactly
// the index map.c already computes for block_count - so the grid can never drift
// out of step with the block list.
void mobgrid_inc(int *grid, int pos);
void mobgrid_dec(int *grid, int pos);

// 1 if any block overlapping the tile square [x-range,x+range]x[y-range,y+range]
// holds a counted unit. Covers exactly the blocks map_foreachinrange() would
// visit for the same (x,y,range), so a true result is a conservative superset
// (never a false negative) of "a PC/HOM is actually in range".
int  mobgrid_any(const int *grid, int bxs, int bys, int x, int y, int range);

#endif /* _MOBGRID_H_ */
