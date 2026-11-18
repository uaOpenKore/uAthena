// Standalone unit test for the main-loop stall measure (stallguard.h). Not part of the build.
//   gcc -Wall -I src/common -o /tmp/test_stallguard src/common/test_stallguard.c
//   /tmp/test_stallguard
//
// A loop round is: start -> run timers / parse packets -> wait for sockets (at most `asked` ms, the time to
// the next timer) -> next start. Sleeping in that wait is the server doing its job; the rest of the round,
// and any time the wait took beyond `asked` (a VM/host pause while it slept), is the server being gone.

#include "stallguard.h"

#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

int main(void)
{
	// The login-server false alarm (live logs 2026-11-18): nothing to do, it sleeps 5 s until its next timer.
	CHECK(stallguard_gone_ms(5004, 5000, 5000) == 4, "idle sleep of 5 s up to the next timer is not a stall");
	CHECK(stallguard_gone_ms(60010, 60000, 60000) == 10, "a 60 s sleep asked by the timers is not a stall");

	// Traffic wakes the wait early: only the work counts.
	CHECK(stallguard_gone_ms(120, 20, 5000) == 100, "woken early by a packet: the round minus the wait");

	// The loop itself froze (a slow handler, a long timer).
	CHECK(stallguard_gone_ms(4050, 50, 50) == 4000, "4 s of work between two waits is a 4 s stall");

	// A pause while it slept: the wait returned long after its timeout.
	CHECK(stallguard_gone_ms(6000, 6000, 1000) == 5000, "a wait asked for 1 s that took 6 s is a 5 s stall");
	CHECK(stallguard_gone_ms(70000, 69000, 1000) == 69000, "work and overrun add up");

	// The tick wraps at 2^32 ms: the caller passes unsigned differences, they stay right across the wrap.
	{
		unsigned int prev = 0xFFFFF000u, now = prev + 7000u; // wrapped
		CHECK(stallguard_gone_ms(now - prev, 2000, 2000) == 5000, "difference across the tick wrap");
	}

	// Clock oddities never yield a huge unsigned number.
	CHECK(stallguard_gone_ms(100, 300, 5000) == 0, "a wait longer than the whole round counts as no stall");

	// A freeze while the loop sleeps only shows as the wait running past its timeout, so the wait is kept
	// short: an idle login-server would otherwise sleep up to 60 s (ip_ban_flush) and a 10 s freeze in that
	// sleep went unseen on the local stand.
	CHECK(stallguard_wait_ms(60000) == 1000, "a 60 s wait until the next timer is cut to 1 s");
	CHECK(stallguard_wait_ms(1000) == 1000, "a 1 s wait stays");
	CHECK(stallguard_wait_ms(50) == 50, "a short wait (busy map-server) stays");
	CHECK(stallguard_gone_ms(11000, 10900, stallguard_wait_ms(60000)) == 10000,
		"a 10 s freeze inside a would-be 60 s sleep is a 10 s stall");

	printf("%s (%d failure%s)\n", failures ? "FAILED" : "PASSED", failures, failures == 1 ? "" : "s");
	return failures ? 1 : 0;
}
