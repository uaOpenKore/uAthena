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

int main(void)
{
	signal(SIGPIPE, SIG_IGN);  // a closed peer must not kill us (the server ignores it too)
	sendworker_init();
	t_order();
	t_backpressure();
	t_release();
	t_many();
	sendworker_final();
	printf(fails ? "\nFAILED\n" : "\nALL PASSED\n");
	return fails;
}
