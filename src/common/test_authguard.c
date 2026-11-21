// Unit test of authguard.h (S. 2026-11-21). Build and run:
//   gcc -O1 -Wall -I src/common -o /tmp/test_authguard src/common/test_authguard.c && /tmp/test_authguard
#include <stdbool.h>
#include <stdio.h>
#include "authguard.h"

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void)
{
	struct ag_config c = { 5, 600, 300, 3600, 30 * 86400 };
	struct ag_state s;
	time_t t = 1000000;
	int i, r;

	memset(&s, 0, sizeof(s));
	for (i = 0; i < 4; i++)
		CHECK(ag_fail(&s, &c, 100 + i, t + i) == 0, "fail %d: no lock yet", i + 1);
	CHECK(!ag_locked(&s, t + 4), "4 failures: not locked");
	r = ag_fail(&s, &c, 104, t + 5);
	CHECK(r == 300, "the 5th failure locks 300 s: %d", r);
	CHECK(ag_locked(&s, t + 6) && ag_locked(&s, t + 304) && !ag_locked(&s, t + 305), "locked until +305");
	CHECK(s.lock_ips == 5 && s.lock_fails == 5, "5 failures from 5 addresses: %d/%d", s.lock_fails, s.lock_ips);
	CHECK(ag_fail(&s, &c, 105, t + 10) == 0, "a failure while locked starts no new lock");

	// the window: 4 old failures do not count
	memset(&s, 0, sizeof(s));
	for (i = 0; i < 4; i++)
		ag_fail(&s, &c, 1, t + i);
	CHECK(ag_fail(&s, &c, 1, t + 700) == 0, "failures older than 10 min are gone");
	CHECK(s.fails == 1, "one left: %d", s.fails);

	// doubling within a day, capped
	memset(&s, 0, sizeof(s));
	{
		int want[] = { 300, 600, 1200, 2400, 3600, 3600 };
		time_t now = t;
		for (i = 0; i < 6; i++) {
			int k;
			now = (s.lock_until > now ? s.lock_until : now) + 1;
			for (k = 0; k < 4; k++)
				ag_fail(&s, &c, 7, now + k);
			r = ag_fail(&s, &c, 7, now + 4);
			CHECK(r == want[i], "lock %d: %d s, want %d", i + 1, r, want[i]);
			now += 4;
		}
		// a day without a lock: back to 300
		now = s.last_lock + 86400 + 1;
		for (i = 0; i < 4; i++)
			ag_fail(&s, &c, 7, now + i);
		r = ag_fail(&s, &c, 7, now + 4);
		CHECK(r == 300, "a day later the lock starts at 300 again: %d", r);
	}

	// trusted addresses
	memset(&s, 0, sizeof(s));
	ag_success(&s, 42, t);
	for (i = 0; i < 5; i++)
		ag_fail(&s, &c, 900 + i, t + 10 + i);
	CHECK(ag_locked(&s, t + 20), "locked by others");
	CHECK(ag_trusted(&s, &c, 42, t + 20), "the owner's address is trusted");
	CHECK(!ag_trusted(&s, &c, 900, t + 20), "a guessing address is not");
	CHECK(!ag_trusted(&s, &c, 42, t + 31 * 86400), "trust ends after 30 days");
	ag_success(&s, 42, t + 30);
	CHECK(!ag_locked(&s, t + 31) && s.fails == 0 && s.locks == 0, "a success clears the lock and the count");
	for (i = 0; i < 7; i++)
		ag_success(&s, 200 + i, t + 100 + i);
	CHECK(!ag_trusted(&s, &c, 42, t + 200) && ag_trusted(&s, &c, 206, t + 200) && ag_trusted(&s, &c, 202, t + 200),
		"5 addresses kept, the oldest go");

	// a flood of failures keeps only the newest AG_FAILS
	memset(&s, 0, sizeof(s));
	c.limit = 100; // over AG_FAILS: capped to it
	for (i = 0; i < 40; i++)
		r = ag_fail(&s, &c, i, t + i);
	CHECK(s.fails <= AG_FAILS && ag_locked(&s, t + 40), "a limit over %d is %d: locked", AG_FAILS, AG_FAILS);
	c.limit = 5;

	// idle
	memset(&s, 0, sizeof(s));
	CHECK(ag_idle(&s, &c, t), "empty is idle");
	ag_fail(&s, &c, 1, t);
	CHECK(!ag_idle(&s, &c, t + 10) && ag_idle(&s, &c, t + 601), "a recent failure is kept, an old one not");
	ag_success(&s, 1, t);
	CHECK(!ag_idle(&s, &c, t + 86400), "a trusted address is kept");

	printf(fails ? "%d FAILED\n" : "ALL PASSED\n", fails);
	return fails != 0;
}
