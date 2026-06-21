// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Flat-array index of every live skill_unit (ground AoE cells, traps, walls).
// skill_unit_timer used to walk the WHOLE global objects[] array (floor items +
// skill units + ...) via map_foreachobject(BL_SKILL) every 100ms; this lets it
// iterate only the live skill units directly. Mirrors livemob.c: a contiguous
// pointer array, O(1) swap-remove, slot cached in skill_unit.liveskillunit_idx,
// snapshot under map_freeblock_lock (group->unit frees are deferred there, so
// snapshot pointers stay valid for the whole pass). [perf]

#ifndef _LIVESKILLUNIT_H_
#define _LIVESKILLUNIT_H_

#include <stdarg.h>

#ifdef LIVESKILLUNIT_TEST
// Minimal stand-ins so the index logic can be unit-tested without the whole
// world. Layout mirrors the real structs for the (skill_unit*)bl cast + idx.
struct block_list { struct block_list *prev, *next; int id, type; };
struct skill_unit { struct block_list bl; int liveskillunit_idx; };
#else
struct block_list;
#endif

void liveskillunit_init(void);
void liveskillunit_final(void);
void liveskillunit_add(struct block_list *bl);     // call when a skill_unit becomes alive (skill_initunit)
void liveskillunit_remove(struct block_list *bl);  // call when a skill_unit dies (skill_delunit)
// Apply func to every live skill unit. Safe against add/remove of any unit
// (including the current one) from inside the callback. Varargs, same shape as
// map_foreachobject: liveskillunit_foreach(skill_unit_timer_sub, tick).
void liveskillunit_foreach(int (*func)(struct block_list*, va_list), ...);

#endif /* _LIVESKILLUNIT_H_ */
