// Copyright (c) uAthena / bornrok.com
// [whobot] Tick rate of a session (S. 2026-11-19). A game client sends the tick packet every few seconds (BornRok
// every 4 s); OpenKore's default config sends one every 0.1 s, ~9 a second (the 19.11 logs: 86 accounts at
// 10-310 thousand ticks in 9.5 h). Pure arithmetic only, so test_tickrate.c needs nothing else; clif.c counts
// the ticks and logs the rate on logout, atcommand.c lists the suspects (@whobot).
#ifndef _TICKRATE_H_
#define _TICKRATE_H_

#include <limits.h>

// A session is judged only after this long online: a fresh one has too few ticks to tell anything.
#define TICKRATE_MIN_ONLINE_MS 60000
// More ticks a second than this = not a game client (@whobot).
#define TICKRATE_CLIENT_MAX_PER_S 1

// Ticks per second over `online_ms`, in tenths (88 = 8.8/s); 0 while nothing was measured yet.
static inline unsigned int tickrate_tenths(unsigned int ticks, unsigned int online_ms)
{
	unsigned long long tenths;

	if (online_ms == 0)
		return 0;
	tenths = (unsigned long long)ticks * 10000ULL / online_ms;
	return tenths > UINT_MAX ? UINT_MAX : (unsigned int)tenths;
}

// 1 when a session online for at least TICKRATE_MIN_ONLINE_MS sent more than `max_per_s` ticks a second.
static inline int tickrate_suspect(unsigned int ticks, unsigned int online_ms, unsigned int max_per_s)
{
	if (online_ms < TICKRATE_MIN_ONLINE_MS)
		return 0;
	return (unsigned long long)ticks * 1000ULL > (unsigned long long)max_per_s * online_ms;
}

#endif /* _TICKRATE_H_ */
