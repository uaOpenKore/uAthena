// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Central pseudo-random generator for game logic. Replaces scattered rand()
// calls with a fast, good-quality generator (xoshiro256**): each draw is a
// handful of register ops with no libc global state and no lock. Seed once at
// startup with rnd_init().
//
// NOT cryptographically secure - never use rnd()/rnd_value() for anything an
// attacker must not predict (session ids, keys, tokens). For those use
// rnd_secure_fill(), which pulls real entropy from the kernel (getrandom).

#ifndef _RANDOM_H_
#define _RANDOM_H_

#include "cbasetypes.h"

void   rnd_init(void);                  // seed the generator (call once at startup)
int    rnd(void);                       // [0, RAND_MAX] - drop-in for rand()
uint32 rnd_u32(void);                   // full 32-bit draw
int    rnd_value(int min, int max);     // unbiased, inclusive [min, max]
double rnd_uniform(void);               // [0.0, 1.0)
int    rnd_secure_fill(void* buf, int len); // kernel CSPRNG; 1 = ok, 0 = failed

#endif /* _RANDOM_H_ */
