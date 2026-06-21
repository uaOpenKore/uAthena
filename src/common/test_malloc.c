// Standalone stress/correctness + benchmark harness for the MEMMGR allocator.
// Not part of the build. Characterization test: must pass on the ORIGINAL code
// and stay green through the O(1)-freelist refactor; the benchmark shows the win.
//
//   gcc -O2 -DUSE_MEMMGR -I . -o /tmp/test_malloc test_malloc.c malloc.c -lpthread
//   /tmp/test_malloc
//
// The allocator polices its own integrity (0xdeadbeaf guards, double-free, bad
// pointer) via Show{Error,FatalError,Warning}. We stub those and FAIL if any fire.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>
#include "malloc.h"

static int g_err = 0;
#define STUB(name) void name(const char *fmt, ...){ va_list ap; va_start(ap,fmt); fprintf(stderr,"["#name"] "); vfprintf(stderr,fmt,ap); va_end(ap); }
#define STUB_ERR(name) void name(const char *fmt, ...){ g_err++; va_list ap; va_start(ap,fmt); fprintf(stderr,"["#name"] "); vfprintf(stderr,fmt,ap); va_end(ap); }
STUB_ERR(ShowError)
STUB_ERR(ShowFatalError)
STUB_ERR(ShowWarning)
STUB(ShowInfo)
STUB(ShowNotice)
STUB(ShowStatus)
STUB(ShowDebug)
STUB(ShowSQL)
void ShowMessage(const char *fmt, ...){ (void)fmt; }

// core symbols pulled in by LOG_MEMMGR's leak logger
char *SERVER_NAME = (char*)"test-memmgr";
const char *get_svn_revision(void){ return "test"; }

extern void malloc_init(void);
extern void malloc_final(void);
extern unsigned int malloc_usage(void);

static double now_sec(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec + t.tv_nsec/1e9; }

// fill a buffer with a pattern unique to (id), so any aliasing/corruption shows up
static void fill(unsigned char *p, size_t n, unsigned id){ size_t j; for(j=0;j<n;j++) p[j]=(unsigned char)(id*31u + j); }
static int  check(const unsigned char *p, size_t n, unsigned id){ size_t j; for(j=0;j<n;j++) if(p[j]!=(unsigned char)(id*31u + j)) return 0; return 1; }

#define N 4000
static void *ptr[N];
static size_t sz[N];

int main(void)
{
	int i, round, fails = 0, bad;
	double t0, secs;

	malloc_init();

	// --- 1. varied-size alloc, integrity, no aliasing -----------------------
	for(i=0;i<N;i++){
		sz[i] = 1 + ((i*97) % 2000);          // 1..2000 bytes, spread across size classes
		ptr[i] = aMalloc(sz[i]);
		fill(ptr[i], sz[i], (unsigned)i);
	}
	for(bad=0,i=0;i<N;i++) if(!check(ptr[i], sz[i], (unsigned)i)) bad++;
	printf("1. varied alloc integrity (%d allocs)   : %s\n", N, bad?"FAIL":"ok"); fails += !!bad;

	// --- 2. free every other, verify survivors, refill the holes -------------
	for(i=0;i<N;i+=2){ aFree(ptr[i]); ptr[i]=NULL; }
	for(bad=0,i=1;i<N;i+=2) if(!check(ptr[i], sz[i], (unsigned)i)) bad++;
	printf("2. survivors intact after holey free    : %s\n", bad?"FAIL":"ok"); fails += !!bad;
	for(i=0;i<N;i+=2){ sz[i]=1+((i*53)%2000); ptr[i]=aMalloc(sz[i]); fill(ptr[i],sz[i],(unsigned)(i+7)); }
	for(bad=0,i=0;i<N;i++) if(!check(ptr[i], sz[i], (unsigned)(i%2? i : i+7))) bad++;
	printf("3. refilled holes intact                : %s\n", bad?"FAIL":"ok"); fails += !!bad;

	// --- 4. realloc grow/shrink + strdup -------------------------------------
	{
		char *s = aStrdup("hello memmgr");
		bad = strcmp(s,"hello memmgr")!=0;
		ptr[0] = aRealloc(ptr[0], 4096); fill(ptr[0],4096,123);
		bad |= !check(ptr[0],4096,123);
		aFree(s);
		printf("4. realloc-grow + strdup                : %s\n", bad?"FAIL":"ok"); fails += !!bad;
	}
	for(i=0;i<N;i++){ aFree(ptr[i]); ptr[i]=NULL; }

	// --- 5. single small size class across many blocks (the O(K^2) path) ------
	//     and assert usage returns to baseline after freeing everything.
	{
		unsigned int base = malloc_usage();
		enum { M = 40000 };
		static void *big[M];
		for(i=0;i<M;i++){ big[i]=aMalloc(32); *(int*)big[i]=i; }
		for(bad=0,i=0;i<M;i++) if(*(int*)big[i]!=i) bad++;
		for(i=0;i<M;i++) aFree(big[i]);
		printf("5. 40k x 32B fill/verify/free           : %s\n", bad?"FAIL":"ok"); fails += !!bad;
		printf("6. usage back to baseline               : %s (%u -> %u KB)\n",
			malloc_usage()==base?"ok":"FAIL", base, malloc_usage());
		fails += (malloc_usage()!=base);
	}

	// --- 7. BENCHMARK: repeatedly fill+drain a small size class --------------
	//     This is exactly the alloc-side scan the refactor targets.
	{
		enum { B = 20000, ROUNDS = 60 };
		static void *bp[B];
		t0 = now_sec();
		for(round=0;round<ROUNDS;round++){
			for(i=0;i<B;i++) bp[i]=aMalloc(48);
			for(i=0;i<B;i++) aFree(bp[i]);
		}
		secs = now_sec()-t0;
		printf("7. bench: %d x (%d alloc+free of 48B)  : %.3f s  (%.1f Mops/s)\n",
			ROUNDS, B, secs, (2.0*ROUNDS*B/1e6)/secs);
	}

	printf("\nallocator self-reported errors          : %d\n", g_err);
	fails += !!g_err;
	printf(fails?"\nFAILED\n":"\nALL PASSED\n");

	malloc_final();
	return fails;
}
