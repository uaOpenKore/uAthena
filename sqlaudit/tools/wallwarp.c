// LD_PRELOAD shim for the play-limit e2e: the wall clock (time, gettimeofday, CLOCK_REALTIME) runs ahead by the
// number of seconds in $WALL_FILE (may be negative), so a test can put the servers at 23:59 or set their clock
// back. CLOCK_MONOTONIC (server ticks) is untouched. Build: gcc -shared -fPIC -O2 -o wallwarp.so wallwarp.c -ldl
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <time.h>

static int (*real_cg)(clockid_t, struct timespec *);

static long long offset_s(void)
{
	static long long off = 0, next = 0;
	struct timespec m;
	const char *p;
	FILE *f;
	if (!real_cg) real_cg = (int (*)(clockid_t, struct timespec *))dlsym(RTLD_NEXT, "clock_gettime");
	real_cg(CLOCK_MONOTONIC, &m);
	long long ms = (long long)m.tv_sec * 1000 + m.tv_nsec / 1000000;
	if (ms < next) return off;
	next = ms + 200;
	if ((p = getenv("WALL_FILE")) && (f = fopen(p, "r"))) { long long v; if (fscanf(f, "%lld", &v) == 1) off = v; fclose(f); }
	return off;
}

int clock_gettime(clockid_t clk, struct timespec *ts)
{
	int r;
	if (!real_cg) real_cg = (int (*)(clockid_t, struct timespec *))dlsym(RTLD_NEXT, "clock_gettime");
	r = real_cg(clk, ts);
	if (r == 0 && (clk == CLOCK_REALTIME || clk == CLOCK_REALTIME_COARSE)) ts->tv_sec += offset_s();
	return r;
}

int gettimeofday(struct timeval *tv, void *tz)
{
	struct timespec ts;
	(void)tz;
	clock_gettime(CLOCK_REALTIME, &ts);
	if (tv) { tv->tv_sec = ts.tv_sec; tv->tv_usec = ts.tv_nsec / 1000; }
	return 0;
}

time_t time(time_t *t)
{
	struct timespec ts;
	clock_gettime(CLOCK_REALTIME, &ts);
	if (t) *t = ts.tv_sec;
	return ts.tv_sec;
}
