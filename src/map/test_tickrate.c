// Standalone unit test for the tick-rate rules (tickrate.h) behind @whobot and the [PADMETRIC] logout line.
//
// Not part of `make sql`. Build & run with:
//   gcc -Wall -I src/map -o /tmp/test_tickrate src/map/test_tickrate.c
//   /tmp/test_tickrate
//
// The idea (S. 2026-11-19, from the 19.11 logs): the client sends a tick packet every few seconds (BornRok every
// 4 s), OpenKore's default config sends one every 0.1 s (~9 a second). A session online for at least a minute
// that sends more than one tick a second is not a game client.

#include "tickrate.h"

#include <limits.h>
#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

int main(void)
{
	// rate in tenths of a tick per second
	CHECK(tickrate_tenths(0, 60000) == 0, "no ticks -> 0.0/s");
	CHECK(tickrate_tenths(600, 60000) == 100, "600 ticks in a minute -> 10.0/s");
	CHECK(tickrate_tenths(15, 60000) == 2, "BornRok, one tick every 4 s -> 0.25/s shown as 0.2");
	CHECK(tickrate_tenths(309516, 34200000) == 90, "MayLee 19.11: 309516 ticks in 9.5 h -> 9.0/s");
	CHECK(tickrate_tenths(5, 0) == 0, "no time online yet -> 0, no division by zero");
	CHECK(tickrate_tenths(4000000000u, 1000) == UINT_MAX, "absurd count saturates instead of wrapping");

	// suspect: online >= TICKRATE_MIN_ONLINE_MS and more than max_per_s ticks a second
	CHECK(TICKRATE_MIN_ONLINE_MS == 60000, "a session is judged after one minute online");
	CHECK(!tickrate_suspect(599, 59999, 1), "10/s but online under a minute -> not judged yet");
	CHECK(tickrate_suspect(600, 60000, 1), "10/s after exactly a minute -> suspect");
	CHECK(!tickrate_suspect(60, 60000, 1), "exactly one tick a second -> not more than once a second");
	CHECK(tickrate_suspect(61, 60000, 1), "61 ticks in a minute -> more than once a second");
	CHECK(!tickrate_suspect(900, 3600000, 1), "BornRok for an hour (every 4 s) -> not suspect");
	CHECK(!tickrate_suspect(300, 3600000, 1), "a client ticking every 12 s for an hour -> not suspect");
	CHECK(tickrate_suspect(32400, 3600000, 1), "OpenKore default for an hour (9/s) -> suspect");
	CHECK(!tickrate_suspect(0, 0, 1), "nothing measured -> not suspect");
	CHECK(tickrate_suspect(4000000000u, 4000000000u - 1, 1), "big numbers do not overflow the comparison");

	printf("%s (%d failure(s))\n", failures ? "FAILED" : "PASSED", failures);
	return failures ? 1 : 0;
}
