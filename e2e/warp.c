// LD_PRELOAD shim for e2e tests: CLOCK_MONOTONIC (the server tick and socket_clock) runs ahead by the number of
// milliseconds written in $WARP_FILE, so a test can make days pass in seconds. Only CLOCK_MONOTONIC moves:
// CLOCK_REALTIME / gettimeofday / time stay real (logs, the send worker's cond deadlines).
// Build: gcc -shared -fPIC -O2 -o warp.so warp.c -ldl
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static int (*real_clock_gettime)(clockid_t, struct timespec *);

static long long warp_offset_ms(void)
{
	static long long offset = 0;
	static long long next_read = 0; // real monotonic ms of the next file read
	struct timespec now;
	long long ms;
	const char *path;
	FILE *f;

	real_clock_gettime(CLOCK_MONOTONIC, &now);
	ms = (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
	if (ms < next_read)
		return offset;
	next_read = ms + 200; // re-read at most 5 times a second
	if ((path = getenv("WARP_FILE")) != NULL && (f = fopen(path, "r")) != NULL) {
		long long v;
		if (fscanf(f, "%lld", &v) == 1)
			offset = v;
		fclose(f);
	}
	return offset;
}

int clock_gettime(clockid_t clk, struct timespec *ts)
{
	int r;
	if (!real_clock_gettime)
		real_clock_gettime = (int (*)(clockid_t, struct timespec *))dlsym(RTLD_NEXT, "clock_gettime");
	r = real_clock_gettime(clk, ts);
	if (r == 0 && clk == CLOCK_MONOTONIC) {
		long long off = warp_offset_ms();
		long long ns = (long long)ts->tv_nsec + (off % 1000) * 1000000LL;
		ts->tv_sec += off / 1000 + ns / 1000000000LL;
		ts->tv_nsec = ns % 1000000000LL;
	}
	return r;
}
