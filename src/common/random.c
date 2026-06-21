// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Central PRNG - see random.h. xoshiro256** (Blackman & Vigna, 2018) seeded
// from the kernel CSPRNG. Single global state, used from the game thread only
// (do not call rnd*() from worker threads - give them their own state if ever
// needed). rnd_secure_fill() is the separate, real-entropy path for secrets.

#include "random.h"

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/random.h> // getrandom
#endif

static uint64 s[4]; // generator state

static uint64 rotl(const uint64 x, int k)
{
	return (x << k) | (x >> (64 - k));
}

static uint64 xoshiro_next(void)
{
	const uint64 result = rotl(s[1] * 5, 7) * 9;
	const uint64 t = s[1] << 17;
	s[2] ^= s[0];
	s[3] ^= s[1];
	s[1] ^= s[2];
	s[0] ^= s[3];
	s[2] ^= t;
	s[3] = rotl(s[3], 45);
	return result;
}

static uint64 splitmix64(uint64* x)
{
	uint64 z = (*x += 0x9e3779b97f4a7c15ULL);
	z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
	z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
	return z ^ (z >> 31);
}

int rnd_secure_fill(void* buf, int len)
{
	if (buf == NULL || len <= 0)
		return 0;
#if defined(__linux__)
	{
		int got = 0;
		char* p = (char*)buf;
		while (got < len) {
			ssize_t n = getrandom(p + got, (size_t)(len - got), 0);
			if (n <= 0)
				break;
			got += (int)n;
		}
		if (got == len)
			return 1;
	}
#endif
	{	// fallback: /dev/urandom
		FILE* f = fopen("/dev/urandom", "rb");
		if (f != NULL) {
			size_t n = fread(buf, 1, (size_t)len, f);
			fclose(f);
			if ((int)n == len)
				return 1;
		}
	}
	return 0;
}

void rnd_init(void)
{
	if (!rnd_secure_fill(s, (int)sizeof(s))) {
		// last-resort seed if the kernel CSPRNG is unavailable
		uint64 seed = (uint64)time(NULL) ^ ((uint64)getpid() << 32);
		int i;
		for (i = 0; i < 4; i++)
			s[i] = splitmix64(&seed);
	}
	if ((s[0] | s[1] | s[2] | s[3]) == 0) // xoshiro must not be seeded all-zero
		s[0] = 0x9e3779b97f4a7c15ULL;
}

uint32 rnd_u32(void)
{
	return (uint32)(xoshiro_next() >> 32);
}

int rnd(void)
{
	// 31-bit value in [0, 2147483647] == [0, RAND_MAX], so rnd()%n and
	// rnd()/(RAND_MAX+1.0) behave exactly like the rand() they replace.
	return (int)(xoshiro_next() >> 33);
}

int rnd_value(int min, int max)
{
	uint32 range, t, x;
	if (max <= min)
		return min;
	range = (uint32)max - (uint32)min + 1u;
	if (range == 0) // full 32-bit span requested
		return (int)((uint32)min + rnd_u32());
	t = (0u - range) % range; // == 2^32 % range; reject below this for no bias
	do {
		x = rnd_u32();
	} while (x < t);
	return (int)((uint32)min + (x % range));
}

double rnd_uniform(void)
{
	// top 53 bits -> uniform double in [0, 1)
	return (double)(xoshiro_next() >> 11) * (1.0 / 9007199254740992.0);
}
