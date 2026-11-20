// Standalone test: the send worker's coalesce / EAGAIN-retry deadlines must not depend on the wall clock.
// A step of CLOCK_REALTIME (NTP, a VM resumed from a pause) between computing a deadline and waiting for it kept
// every deferred client packet for the size of the step. Build send_worker.c with clock_gettime renamed so this
// test can put the wall clock 3 s ahead of the kernel's (the same as the kernel clock stepping back 3 s):
//   gcc -O1 -g -I. -Dclock_gettime=test_clock_gettime -c send_worker.c -o /tmp/sw_fake.o
//   gcc -O1 -g -I. -o /tmp/tswc test_send_worker_clock.c /tmp/sw_fake.o -lpthread && /tmp/tswc
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <sys/socket.h>
#include "send_worker.h"

static long long realtime_offset_ms = 0;

int test_clock_gettime(clockid_t clk, struct timespec *ts)
{
	int r = clock_gettime(clk, ts);
	if( r == 0 && clk == CLOCK_REALTIME && realtime_offset_ms ) {
		long long ns = (long long)ts->tv_nsec + (realtime_offset_ms % 1000) * 1000000LL;
		ts->tv_sec += (time_t)(realtime_offset_ms / 1000) + (time_t)(ns / 1000000000LL);
		ts->tv_nsec = (long)(ns % 1000000000LL);
	}
	return r;
}

static double now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }

int main(void)
{
	int sv[2], fails = 0;
	unsigned char msg[64], got[64];
	double t0, dt;
	struct pollfd p;
	signal(SIGPIPE, SIG_IGN);
	memset(msg, 0x42, sizeof msg);
	sendworker_init();
	sendworker_set_coalesce(10);                 // small packets wait up to 10 ms for company
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	fcntl(sv[0], F_SETFL, fcntl(sv[0], F_GETFL, 0) | O_NONBLOCK);
	sendworker_reset(sv[0]);
	realtime_offset_ms = 3000;                   // wall clock 3 s ahead of the kernel's
	t0 = now_ms();
	sendworker_send(sv[0], msg, sizeof msg);     // sub-segment: deferred by the coalesce window
	p.fd = sv[1]; p.events = POLLIN; p.revents = 0;
	poll(&p, 1, 5000);
	dt = now_ms() - t0;
	{ ssize_t n = read(sv[1], got, sizeof got);
	  int ok = n == (ssize_t)sizeof msg && dt < 500;
	  printf("a deferred packet goes out after its 10 ms window, not after a wall-clock step: %s (%.0f ms)\n",
	         ok ? "ok" : "FAIL", dt);
	  fails += !ok; }
	realtime_offset_ms = 0;
	sendworker_release(sv[0]);
	close(sv[0]); close(sv[1]);
	sendworker_final();
	printf(fails ? "FAILED\n" : "ALL PASSED\n");
	return fails;
}
