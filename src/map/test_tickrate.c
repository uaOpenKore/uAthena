// Standalone unit test for the tick-rate rules (tickrate.h) behind @whobot and the [PADMETRIC] logout line.
//
// Not part of `make sql`. Build & run with:
//   gcc -Wall -I src/map -o /tmp/test_tickrate src/map/test_tickrate.c
//   /tmp/test_tickrate
//
// The idea (S. 2026-11-19, from the 19.11 logs): the client sends a tick packet every few seconds (BornRok every
// 4 s), OpenKore's default config sends one every 0.1 s (~9 a second). A session online for at least a minute
// that sends more ticks than a game client is not one.
// 20.11 (S. "да"): farms at ~1 tick/s slipped under the first threshold of 1/s, so it is 0.4/s now; and farms
// that tick as slowly as the original client but walk with OpenKore's padding (00 00 44) are listed too.

#include "tickrate.h"

#include <limits.h>
#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

static const unsigned char okore_pad[3]  = { 0x00, 0x00, 0x44 }; // OpenKore, BornRok before 0.0.53.0
static const unsigned char marker_pad[3] = { 0x01, 0x01, 0x01 }; // BornRok 0.0.53.0+
static const unsigned char orig_pad[3]   = { 0x37, 0x34, 0x00 }; // the original client (varies)
static const unsigned char zero_pad[3]   = { 0x00, 0x00, 0x00 };

int main(void)
{
	// rate in tenths of a tick per second (the logout line)
	CHECK(tickrate_tenths(0, 60000) == 0, "no ticks -> 0.0/s");
	CHECK(tickrate_tenths(600, 60000) == 100, "600 ticks in a minute -> 10.0/s");
	CHECK(tickrate_tenths(15, 60000) == 2, "BornRok, one tick every 4 s -> 0.25/s shown as 0.2");
	CHECK(tickrate_tenths(309516, 34200000) == 90, "MayLee 19.11: 309516 ticks in 9.5 h -> 9.0/s");
	CHECK(tickrate_tenths(5, 0) == 0, "no time online yet -> 0, no division by zero");
	CHECK(tickrate_tenths(4000000000u, 1000) == UINT_MAX, "absurd count saturates instead of wrapping");

	// rate in hundredths (@whobot shows the slow farms as 0.08/s, not 0.0/s)
	CHECK(tickrate_hundredths(15, 60000) == 25, "BornRok, one tick every 4 s -> 0.25/s");
	CHECK(tickrate_hundredths(5, 60000) == 8, "one tick every 12 s -> 0.08/s");
	CHECK(tickrate_hundredths(1940, 23450000) == 8, "HoeDini 20.11: 1940 ticks in 6.5 h -> 0.08/s");
	CHECK(tickrate_hundredths(0, 60000) == 0, "no ticks -> 0.00/s");
	CHECK(tickrate_hundredths(5, 0) == 0, "hundredths: no time online yet -> 0");
	CHECK(tickrate_hundredths(4000000000u, 1) == UINT_MAX, "hundredths: absurd count saturates");

	// thresholds
	CHECK(TICKRATE_MIN_ONLINE_MS == 60000, "a session is judged after one minute online");
	CHECK(TICKRATE_CLIENT_MAX_HUNDREDTHS == 40, "a game client sends at most 0.4 ticks/s (BornRok 0.25)");
	CHECK(TICKRATE_OKORE_SLOW_HUNDREDTHS == 15, "OpenKore's walk padding under 0.15 ticks/s = not BornRok");

	// faster than: online >= TICKRATE_MIN_ONLINE_MS and more than hundredths/100 ticks a second
	CHECK(tickrate_faster(59, 60000, 40), "0.98/s (the 20.11 farm under the old 1/s threshold) -> faster than 0.4");
	CHECK(!tickrate_faster(24, 60000, 40), "exactly 0.4/s -> not faster than 0.4");
	CHECK(tickrate_faster(25, 60000, 40), "25 ticks in a minute -> faster than 0.4");
	CHECK(!tickrate_faster(15, 60000, 40), "BornRok (0.25/s) -> not faster than 0.4");
	CHECK(!tickrate_faster(6, 60000, 40), "the original client (0.1/s) -> not faster than 0.4");
	CHECK(!tickrate_faster(599, 59999, 40), "10/s but online under a minute -> not judged yet");
	CHECK(tickrate_faster(600, 60000, 40), "10/s after exactly a minute -> faster");
	CHECK(!tickrate_faster(60, 60000, 100), "exactly one tick a second -> not faster than 1/s");
	CHECK(tickrate_faster(61, 60000, 100), "61 ticks in a minute -> faster than 1/s");
	CHECK(!tickrate_faster(0, 0, 40), "nothing measured -> not faster");
	CHECK(tickrate_faster(4000000000u, 4000000000u - 1, 40), "big numbers do not overflow the comparison");

	// slower than: online >= TICKRATE_MIN_ONLINE_MS and fewer than hundredths/100 ticks a second
	CHECK(tickrate_slower(5, 60000, 15), "one tick every 12 s -> slower than 0.15");
	CHECK(!tickrate_slower(9, 60000, 15), "exactly 0.15/s -> not slower than 0.15");
	CHECK(tickrate_slower(8, 60000, 15), "8 ticks in a minute -> slower than 0.15");
	CHECK(!tickrate_slower(15, 60000, 15), "BornRok (0.25/s) -> not slower than 0.15");
	CHECK(!tickrate_slower(0, 59999, 15), "no tick but online under a minute -> not judged yet");
	CHECK(tickrate_slower(0, 60000, 15), "no tick in a whole minute -> slower");
	CHECK(tickrate_slower(1, 4000000000u, 15), "slower: big numbers do not overflow the comparison");
	CHECK(!tickrate_slower(4000000000u, 4000000000u, 15), "1000 ticks/s -> not slower");

	// OpenKore's walk padding
	CHECK(tickrate_okore_walk_pad(okore_pad, 3), "00 00 44 -> OpenKore's walk padding");
	CHECK(!tickrate_okore_walk_pad(marker_pad, 3), "BornRok 0.0.53.0+ marker -> not OpenKore's");
	CHECK(!tickrate_okore_walk_pad(orig_pad, 3), "the original client's bytes -> not OpenKore's");
	CHECK(!tickrate_okore_walk_pad(zero_pad, 3), "all zero -> not OpenKore's");
	CHECK(!tickrate_okore_walk_pad(okore_pad, 2), "another padding length -> not OpenKore's");
	CHECK(!tickrate_okore_walk_pad(NULL, 0), "no walk yet -> not OpenKore's");

	// verdict = why @whobot lists a session (1 h online unless noted)
	CHECK(tickrate_verdict(32400, 3600000, 100, okore_pad, 3) == TICKRATE_FAST, "OpenKore default (9/s) -> fast");
	CHECK(tickrate_verdict(3528, 3600000, 9000, okore_pad, 3) == TICKRATE_FAST, "the ~1/s farm (0.98/s) -> fast");
	CHECK(tickrate_verdict(32400, 3600000, 100, orig_pad, 3) == TICKRATE_FAST, "9/s with any padding -> fast");
	CHECK(tickrate_verdict(300, 3600000, 7000, okore_pad, 3) == TICKRATE_OKORE_SLOW,
		"OpenKore's padding at one tick every 12 s (5.83.145.35) -> okore + slow");
	CHECK(tickrate_verdict(0, 3600000, 7000, okore_pad, 3) == TICKRATE_OKORE_SLOW,
		"OpenKore's padding and no tick at all -> okore + slow");
	CHECK(tickrate_verdict(900, 3600000, 500, okore_pad, 3) == TICKRATE_CLIENT,
		"BornRok before 0.0.53.0 (OpenKore's padding, a tick every 4 s) -> client");
	CHECK(tickrate_verdict(900, 3600000, 500, marker_pad, 3) == TICKRATE_CLIENT, "BornRok 0.0.53.0+ -> client");
	CHECK(tickrate_verdict(300, 3600000, 300, orig_pad, 3) == TICKRATE_CLIENT,
		"the original client (its own padding, a tick every 12 s) -> client");
	CHECK(tickrate_verdict(300, 3600000, 0, NULL, 0) == TICKRATE_CLIENT, "slow ticks but no walk yet -> client");
	CHECK(tickrate_verdict(0, 59000, 10, okore_pad, 3) == TICKRATE_CLIENT, "okore + slow but under a minute -> not judged");
	CHECK(tickrate_verdict(600, 59999, 10, okore_pad, 3) == TICKRATE_CLIENT, "fast but under a minute -> not judged");

	printf("%s (%d failure(s))\n", failures ? "FAILED" : "PASSED", failures);
	return failures ? 1 : 0;
}
