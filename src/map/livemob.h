// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Flat-array index of every spawned mob (a maintained subset of id_db), for
// cheap mob-only iteration by the AI timers. Replaces the DBMap-based
// livemob_db: a contiguous pointer array iterated directly, eliminating the
// HASH_SIZE (16381) empty-bucket sweep and the per-node va_copy/tree-walk of
// db_obj_vforeach that dominated the profile under mob_ai&0x20. [perf]

#ifndef _LIVEMOB_H_
#define _LIVEMOB_H_

#include <stdarg.h>

#ifdef LIVEMOB_TEST
// Minimal stand-ins so the index logic can be unit-tested without the whole
// world. The field layout mirrors the real structs for the (mob_data*)bl cast
// and the prev/id/livemob_idx accesses the index relies on.
typedef union dbkey { int i; unsigned int ui; const char *str; } DBKey;
struct block_list { struct block_list *prev, *next; int id, type; };
struct mob_data { struct block_list bl; int livemob_idx; };
#else
#include "../common/db.h"   // DBKey
struct block_list;
#endif

void livemob_init(void);
void livemob_final(void);
void livemob_add(struct block_list *bl);     // call when a mob is registered in id_db
void livemob_remove(struct block_list *bl);  // call when a mob leaves id_db
// Apply func to every live mob. Safe against add/remove of any mob (including
// the current one) from inside the callback.
void livemob_foreach(int (*func)(DBKey, void*, va_list), va_list ap);

#endif /* _LIVEMOB_H_ */
