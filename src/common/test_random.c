// Standalone sanity test for the rnd() PRNG module. Not part of the build.
//   gcc -I src/common -o /tmp/test_random src/common/test_random.c src/common/random.c
//   /tmp/test_random
#include "random.h"
#include <stdio.h>

int main(void)
{
	int i;
	long buckets[10] = {0};
	int distfail = 0, neg_ok = 1, rnd_nonneg = 1, secure_ok, fails;
	unsigned char sb[32];

	rnd_init();

	for (i = 0; i < 2000000; i++)
		if (rnd() < 0) { rnd_nonneg = 0; break; }

	for (i = 0; i < 1000000; i++) {
		int v = rnd_value(0, 9);
		if (v < 0 || v > 9) { distfail = 1; break; }
		buckets[v]++;
	}
	for (i = 0; i < 10; i++)
		if (buckets[i] < 90000 || buckets[i] > 110000) distfail = 1; // ~100k +/-10%

	for (i = 0; i < 200000; i++) {
		int v = rnd_value(-5, 5);
		if (v < -5 || v > 5) { neg_ok = 0; break; }
	}

	secure_ok = rnd_secure_fill(sb, sizeof(sb));

	printf("rnd() always >= 0          : %s\n", rnd_nonneg ? "ok" : "FAIL");
	printf("rnd_value(0,9) uniform-ish : %s [", distfail ? "FAIL" : "ok");
	for (i = 0; i < 10; i++) printf("%ld ", buckets[i]);
	printf("]\n");
	printf("rnd_value(-5,5) in bounds  : %s\n", neg_ok ? "ok" : "FAIL");
	printf("rnd_secure_fill(32)        : %s\n", secure_ok ? "ok" : "FAIL");

	fails = !rnd_nonneg || distfail || !neg_ok || !secure_ok;
	printf(fails ? "\nFAILED\n" : "\nALL PASSED\n");
	return fails;
}
