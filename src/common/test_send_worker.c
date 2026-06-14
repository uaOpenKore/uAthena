// Standalone correctness test for the off-thread send worker. Not in the build.
// Uses real socketpairs so send()/EAGAIN/partial paths are exercised for real.
//
//   gcc -O1 -g -fsanitize=thread   -I. -o /tmp/tsw_tsan test_send_worker.c send_worker.c -lpthread && /tmp/tsw_tsan
//   gcc -O1 -g -fsanitize=address  -I. -o /tmp/tsw_asan test_send_worker.c send_worker.c -lpthread && /tmp/tsw_asan
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <errno.h>
#include <signal.h>
#include <time.h>
#include <sys/socket.h>
#include "send_worker.h"

static int fails = 0;

static void set_nonblock(int fd){ int fl=fcntl(fd,F_GETFL,0); fcntl(fd,F_SETFL,fl|O_NONBLOCK); }

// read exactly n bytes (or until timeout); returns bytes read
static size_t read_n(int fd, unsigned char *buf, size_t n, int tmo_ms)
{
	size_t got = 0;
	while( got < n ) {
		struct pollfd p; ssize_t k;
		p.fd = fd; p.events = POLLIN; p.revents = 0;
		if( poll(&p, 1, tmo_ms) <= 0 ) break;
		k = read(fd, buf + got, n - got);
		if( k <= 0 ) { if(k<0 && errno==EINTR) continue; break; }
		got += (size_t)k;
	}
	return got;
}

// fill chunk i with a deterministic pattern
static void pat(unsigned char *b, size_t len, unsigned id){ size_t j; for(j=0;j<len;j++) b[j]=(unsigned char)(id*7u + j); }

// Test 1: many chunks on one fd arrive in order, byte-exact.
static void t_order(void)
{
	int sv[2]; unsigned char sent[200000], *rcv; size_t total=0; int i;
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	set_nonblock(sv[0]);
	for(i=0;i<300;i++){
		size_t len = 1 + ((i*37)%900);
		unsigned char tmp[1024];
		pat(tmp, len, (unsigned)i);
		memcpy(sent+total, tmp, len);
		sendworker_send(sv[0], tmp, len);
		total += len;
	}
	rcv = malloc(total);
	{ size_t got = read_n(sv[1], rcv, total, 3000);
	  int ok = (got==total) && (memcmp(sent, rcv, total)==0);
	  printf("1. ordered integrity (300 chunks, %zuB) : %s (got %zu)\n", total, ok?"ok":"FAIL", got);
	  fails += !ok; }
	free(rcv); close(sv[0]); close(sv[1]);
}

// Test 2: backpressure — tiny SO_SNDBUF + delayed reader forces EAGAIN/partial;
//         all bytes must still arrive exactly once, in order.
static void t_backpressure(void)
{
	int sv[2]; int sndbuf=2048; size_t total=0,i; unsigned char *sent,*rcv; size_t got;
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	set_nonblock(sv[0]);
	setsockopt(sv[0], SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf));
	sent = malloc(400000);
	for(i=0;i<400;i++){
		size_t len = 800 + (i%200);
		pat(sent+total, len, (unsigned)(i+1));
		sendworker_send(sv[0], sent+total, len);  // floods past SO_SNDBUF -> EAGAIN in worker
		total += len;
	}
	// now drain slowly; worker must retry the backlog and deliver everything
	rcv = malloc(total);
	got = read_n(sv[1], rcv, total, 5000);
	{ int ok = (got==total) && (memcmp(sent, rcv, total)==0);
	  printf("2. backpressure no loss/dup (%zuB)       : %s (got %zu)\n", total, ok?"ok":"FAIL", got);
	  fails += !ok; }
	free(sent); free(rcv); close(sv[0]); close(sv[1]);
}

// Test 3: release while data may be in flight must not crash/hang.
static void t_release(void)
{
	int sv[2]; int i;
	for(i=0;i<50;i++){
		unsigned char tmp[512];
		socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
		set_nonblock(sv[0]);
		pat(tmp,sizeof tmp,(unsigned)i);
		sendworker_send(sv[0], tmp, sizeof tmp);
		sendworker_send(sv[0], tmp, sizeof tmp);
		sendworker_release(sv[0]);   // must return promptly, no UAF
		sendworker_reset(sv[0]);
		close(sv[0]); close(sv[1]);
	}
	printf("3. release+reset x50 (no crash/hang)     : ok\n");
}

// Test 4: stress across many fds concurrently.
static void t_many(void)
{
	enum { NF = 40 };
	int sv[NF][2]; size_t tot[NF]; unsigned char *snt[NF]; int f,i; int ok=1;
	for(f=0;f<NF;f++){
		socketpair(AF_UNIX, SOCK_STREAM, 0, sv[f]);
		set_nonblock(sv[f][0]);
		snt[f]=malloc(60000); tot[f]=0;
	}
	for(i=0;i<200;i++) for(f=0;f<NF;f++){
		size_t len = 50 + ((i*13+f)%250);
		pat(snt[f]+tot[f], len, (unsigned)(i*NF+f));
		sendworker_send(sv[f][0], snt[f]+tot[f], len);
		tot[f]+=len;
	}
	for(f=0;f<NF;f++){
		unsigned char *r=malloc(tot[f]);
		size_t got=read_n(sv[f][1], r, tot[f], 5000);
		if(got!=tot[f] || memcmp(snt[f],r,tot[f])!=0) ok=0;
		free(r); free(snt[f]); close(sv[f][0]); close(sv[f][1]);
	}
	printf("4. %d concurrent fds integrity          : %s\n", NF, ok?"ok":"FAIL");
	fails += !ok;
}

// elapsed-ms helper for the timing tests
static long ms_since(struct timespec t0)
{
	struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
	return (t1.tv_sec - t0.tv_sec)*1000L + (t1.tv_nsec - t0.tv_nsec)/1000000L;
}

// Test 5: with a coalesce window, a lone sub-segment packet is HELD for ~the
//         window (not sent immediately) but still arrives byte-exact afterwards.
static void t_window(void)
{
	int sv[2]; unsigned char msg[64], rcv[64]; int win = 80; struct timespec t0;
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	set_nonblock(sv[0]);
	sendworker_set_coalesce(win);
	pat(msg, sizeof msg, 123u);
	clock_gettime(CLOCK_MONOTONIC, &t0);
	sendworker_send(sv[0], msg, sizeof msg);
	// a fraction into the window: nothing should have arrived yet
	{ size_t early = read_n(sv[1], rcv, sizeof msg, win/4);
	  int ok = (early == 0);
	  printf("5. sub-seg packet held for window (%dms): %s (early %zu)\n", win, ok?"ok":"FAIL", early);
	  fails += !ok; }
	// well past it: must arrive, byte-exact, and not before the window
	{ size_t got = read_n(sv[1], rcv, sizeof msg, win*5); long dt = ms_since(t0);
	  int ok = (got==sizeof msg) && (memcmp(msg,rcv,sizeof msg)==0) && (dt >= win/2);
	  printf("   ...then flushed after ~%ldms          : %s (got %zu)\n", dt, ok?"ok":"FAIL", got);
	  fails += !ok; }
	sendworker_set_coalesce(0);
	close(sv[0]); close(sv[1]);
}

// Test 6: a bulk packet (>= ~1 TCP segment) is sent IMMEDIATELY despite the
//         window, so map-entry/spawn bursts are never throttled (the regression
//         that the old timer-based coalescing caused).
static void t_window_bulk(void)
{
	int sv[2]; unsigned char *msg, *rcv; size_t len = 2000; int win = 300; struct timespec t0;
	socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
	set_nonblock(sv[0]);
	sendworker_set_coalesce(win);
	msg = malloc(len); rcv = malloc(len);
	pat(msg, len, 77u);
	clock_gettime(CLOCK_MONOTONIC, &t0);
	sendworker_send(sv[0], msg, len);
	{ size_t got = read_n(sv[1], rcv, len, win); long dt = ms_since(t0);
	  int ok = (got==len) && (memcmp(msg,rcv,len)==0) && (dt < win/2);
	  printf("6. bulk packet bypasses window (%dms)  : %s (got %zu, %ldms)\n", win, ok?"ok":"FAIL", got, dt);
	  fails += !ok; }
	sendworker_set_coalesce(0);
	free(msg); free(rcv); close(sv[0]); close(sv[1]);
}

int main(void)
{
	signal(SIGPIPE, SIG_IGN);  // a closed peer must not kill us (the server ignores it too)
	sendworker_init();

	int win[2] = { 0, 10 }, pass;
	for( pass = 0; pass < 2; pass++ ) {
		sendworker_set_coalesce(win[pass]);  // 0 = off, >0 = flush window in ms
		printf("--- coalesce_ms=%d ---\n", win[pass]);
		t_order();
		t_backpressure();
		t_release();
		t_many();
	}

	printf("--- timing ---\n");
	t_window();
	t_window_bulk();

	sendworker_final();
	printf(fails ? "\nFAILED\n" : "\nALL PASSED\n");
	return fails;
}
