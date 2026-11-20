// Copyright (c) uAthena / bornrok.com
// [whobot] Tick rate of a session (S. 2026-11-19). A game client sends the tick packet every few seconds (BornRok
// every 4 s); OpenKore's default config sends one every 0.1 s, ~9 a second (the 19.11 logs: 86 accounts at
// 10-310 thousand ticks in 9.5 h). Pure arithmetic only, so test_tickrate.c needs nothing else; clif.c counts
// the ticks and logs the rate on logout, atcommand.c lists the suspects (@whobot).
#ifndef _TICKRATE_H_
#define _TICKRATE_H_

#include <limits.h>
#include <stddef.h>

// A session is judged only after this long online: a fresh one has too few ticks to tell anything.
#define TICKRATE_MIN_ONLINE_MS 60000
// Rates below are in hundredths of a tick a second (25 = 0.25/s).
// More ticks a second than this = not a game client (@whobot). BornRok ticks every 4 s (0.25/s), the original
// client every 9-12 s (0.08-0.12/s). The 20.11 logs had farms at ~9/s, ~1.8/s and ~1/s - the last one at 0.98/s,
// just under the first threshold of 1/s (S. 2026-11-20: 0.4/s).
#define TICKRATE_CLIENT_MAX_HUNDREDTHS 40
// OpenKore's walk padding (00 00 44) with fewer ticks a second than this = not a game client either: BornRok sends
// that padding too (before 0.0.53.0) but ticks every 4 s, and the original client, which ticks this slowly, walks
// with other bytes. The 20.11 farms at 5.83.145.35 and 180.190.136.76 tick every ~12 s (0.08/s).
#define TICKRATE_OKORE_SLOW_HUNDREDTHS 15

// Why @whobot lists a session.
enum { TICKRATE_CLIENT = 0, TICKRATE_FAST, TICKRATE_OKORE_SLOW };

// Ticks per second over `online_ms`, in tenths (88 = 8.8/s); 0 while nothing was measured yet.
static inline unsigned int tickrate_tenths(unsigned int ticks, unsigned int online_ms)
{
	unsigned long long tenths;

	if (online_ms == 0)
		return 0;
	tenths = (unsigned long long)ticks * 10000ULL / online_ms;
	return tenths > UINT_MAX ? UINT_MAX : (unsigned int)tenths;
}

// Ticks per second over `online_ms`, in hundredths (8 = 0.08/s); 0 while nothing was measured yet.
static inline unsigned int tickrate_hundredths(unsigned int ticks, unsigned int online_ms)
{
	unsigned long long hundredths;

	if (online_ms == 0)
		return 0;
	hundredths = (unsigned long long)ticks * 100000ULL / online_ms;
	return hundredths > UINT_MAX ? UINT_MAX : (unsigned int)hundredths;
}

// 1 when a session online for at least TICKRATE_MIN_ONLINE_MS sent more than `hundredths`/100 ticks a second.
static inline int tickrate_faster(unsigned int ticks, unsigned int online_ms, unsigned int hundredths)
{
	if (online_ms < TICKRATE_MIN_ONLINE_MS)
		return 0;
	return (unsigned long long)ticks * 100000ULL > (unsigned long long)hundredths * online_ms;
}

// 1 when a session online for at least TICKRATE_MIN_ONLINE_MS sent fewer than `hundredths`/100 ticks a second.
static inline int tickrate_slower(unsigned int ticks, unsigned int online_ms, unsigned int hundredths)
{
	if (online_ms < TICKRATE_MIN_ONLINE_MS)
		return 0;
	return (unsigned long long)ticks * 100000ULL < (unsigned long long)hundredths * online_ms;
}

// 1 for OpenKore's walk padding, 00 00 44 (sent by BornRok before 0.0.53.0 too).
static inline int tickrate_okore_walk_pad(const unsigned char *pad, unsigned int len)
{
	return pad != NULL && len == 3 && pad[0] == 0x00 && pad[1] == 0x00 && pad[2] == 0x44;
}

// Why @whobot lists a session - TICKRATE_FAST (more ticks than a game client) or TICKRATE_OKORE_SLOW (OpenKore's
// walk padding with fewer ticks than BornRok) - or TICKRATE_CLIENT. `walks` = walk packets the session sent,
// `pad`/`len` = the padding of the first one.
static inline int tickrate_verdict(unsigned int ticks, unsigned int online_ms, unsigned int walks,
	const unsigned char *pad, unsigned int len)
{
	if (tickrate_faster(ticks, online_ms, TICKRATE_CLIENT_MAX_HUNDREDTHS))
		return TICKRATE_FAST;
	if (walks > 0 && tickrate_okore_walk_pad(pad, len) && tickrate_slower(ticks, online_ms, TICKRATE_OKORE_SLOW_HUNDREDTHS))
		return TICKRATE_OKORE_SLOW;
	return TICKRATE_CLIENT;
}

#endif /* _TICKRATE_H_ */
