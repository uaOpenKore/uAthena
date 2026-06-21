// Standalone regression harness for the timer min-heap (timer.c).
// Drives the public API with controlled tick values to verify heap correctness:
// ordering, selective expiry, interval re-arm, lazy delete, settick relocation,
// 2000-timer stress, tick wraparound, and add-during-callback re-entrancy.
//
// Not wired into the default build. To run (after `make sql`):
//   cd src/common
//   gcc -O2 -o /tmp/timer_test timer_test.c \
//       obj/timer.o obj/showmsg.o obj/malloc.o obj/strlib.o obj/utils.o
//   /tmp/timer_test    # prints per-test results; exit 0 = all pass
#include "timer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// stubs for common/malloc.o link deps
char* SERVER_NAME = "test_timer";
const char* get_svn_revision(void) { return "test"; }

#define MAXREC 8192
static intptr_t fire_id[MAXREC];
static int fire_n = 0;
static int rec_func(int tid, unsigned int tick, intptr_t id, intptr_t data) {
	if (fire_n < MAXREC) fire_id[fire_n++] = id;
	return 0;
}
static void reset(void) { fire_n = 0; }

// callback that, on its first fire, schedules a follow-up timer from *inside*
// do_timer() — exercises push-during-pop on the heap (the AI re-arm pattern)
static int chain_added = 0;
static int rec_chain(int tid, unsigned int tick, intptr_t id, intptr_t data) {
	if (fire_n < MAXREC) fire_id[fire_n++] = id;
	if (data && !chain_added) { chain_added = 1; add_timer((unsigned int)data, rec_func, 999, 0); }
	return 0;
}

static int failures = 0;
#define CHECK(cond, msg) do { \
	if (!(cond)) { printf("  FAIL: %s\n", msg); failures++; } \
} while(0)

// fire everything by pushing the clock far ahead, in one sweep
#define BIG 0x40000000u

int main(void) {
	timer_init();

	// ---- Test 1: scrambled adds fire in ascending tick order ----
	reset();
	{
		unsigned int ticks[] = {500,100,900,300,700,200,800,400,600,50};
		int i, n = (int)(sizeof(ticks)/sizeof(ticks[0]));
		for (i = 0; i < n; i++)
			add_timer(ticks[i], rec_func, (intptr_t)ticks[i], 0);
		do_timer(BIG);
		CHECK(fire_n == n, "test1: all timers fired");
		int ok = 1;
		for (i = 1; i < fire_n; i++) if (fire_id[i] < fire_id[i-1]) ok = 0;
		CHECK(ok, "test1: fired in non-decreasing tick order");
		CHECK(fire_n>0 && fire_id[0]==50, "test1: soonest (50) fired first");
	}
	printf("test1 (ordering): %s\n", failures==0?"ok":"see above");

	// ---- Test 2: selective expiry by tick threshold ----
	int f2 = failures; reset();
	{
		add_timer(100, rec_func, 100, 0);
		add_timer(200, rec_func, 200, 0);
		add_timer(300, rec_func, 300, 0);
		do_timer(150); // only 100 expired
		CHECK(fire_n == 1 && fire_id[0] == 100, "test2: only tick<=150 fired");
		do_timer(250); // 200 now expired
		CHECK(fire_n == 2 && fire_id[1] == 200, "test2: tick<=250 fired next");
		do_timer(BIG); // 300
		CHECK(fire_n == 3 && fire_id[2] == 300, "test2: remainder fired");
	}
	printf("test2 (selective expiry): %s\n", failures==f2?"ok":"see above");

	// ---- Test 3: interval timer re-arms repeatedly ----
	int f3 = failures; reset();
	{
		int tid = add_timer_interval(100, rec_func, 7, 0, 100);
		CHECK(tid >= 0, "test3: interval timer created");
		do_timer(100); // fires, re-arms to 200
		do_timer(200); // fires, re-arms to 300
		do_timer(300); // fires, re-arms to 400
		CHECK(fire_n == 3, "test3: interval fired 3 times");
		int ok = 1, i; for (i=0;i<fire_n;i++) if (fire_id[i]!=7) ok=0;
		CHECK(ok, "test3: same id each fire");
		delete_timer(tid, rec_func); // stop it leaking into later tests
		do_timer(BIG);
	}
	printf("test3 (interval re-arm): %s\n", failures==f3?"ok":"see above");

	// ---- Test 4: lazy delete — deleted timer never fires ----
	int f4 = failures; reset();
	{
		int a = add_timer(100, rec_func, 111, 0);
		int b = add_timer(200, rec_func, 222, 0);
		delete_timer(a, rec_func);
		do_timer(BIG);
		CHECK(fire_n == 1 && fire_id[0] == 222, "test4: only the non-deleted timer fired");
		(void)b;
	}
	printf("test4 (lazy delete): %s\n", failures==f4?"ok":"see above");

	// ---- Test 6: stress — 2000 scrambled timers stay ordered ----
	int f6 = failures; reset();
	{
		int i, N = 2000;
		for (i = 0; i < N; i++) {
			unsigned int t = (unsigned int)(((i * 2654435761u) >> 8) % 1000000u) + 1;
			add_timer(t, rec_func, (intptr_t)t, 0);
		}
		do_timer(1000001u); // just past the max tick, within the DIFF_TICK window
		CHECK(fire_n == N, "test6: all 2000 fired");
		int ok = 1; for (i=1;i<fire_n;i++) if (fire_id[i] < fire_id[i-1]) ok=0;
		CHECK(ok, "test6: 2000 timers fired in non-decreasing order");
	}
	printf("test6 (stress 2000): %s\n", failures==f6?"ok":"see above");

	// ---- Test 7: tick wraparound (DIFF_TICK orders across the boundary) ----
	int f7 = failures; reset();
	{
		// t1 just before wrap, t2 just after; DIFF_TICK(t1,t2) < 0 so t1 is earlier
		unsigned int near = 0xFFFFFF00u, after = 0x00000010u;
		add_timer(after, rec_func, 2, 0);   // add later-firing first
		add_timer(near,  rec_func, 1, 0);
		do_timer(0x00000020u); // current tick just past wrap: both expired
		CHECK(fire_n == 2, "test7: both straddling timers fired");
		CHECK(fire_n==2 && fire_id[0]==1 && fire_id[1]==2,
		      "test7: pre-wrap timer fired before post-wrap timer");
	}
	printf("test7 (wraparound): %s\n", failures==f7?"ok":"see above");

	// ---- Test 8: a callback adds a new timer mid-do_timer (heap push-during-pop) ----
	int f8 = failures; reset(); chain_added = 0;
	{
		add_timer(100, rec_chain, 8, 150); // at 100, schedules a follow-up at 150
		do_timer(BIG);
		CHECK(fire_n == 2, "test8: original + chained timer both fired");
		CHECK(fire_n==2 && fire_id[0]==8 && fire_id[1]==999,
		      "test8: chained timer fired after its scheduler, in order");
	}
	printf("test8 (add during callback): %s\n", failures==f8?"ok":"see above");

	// ---- Test 5 (run LAST: settick corrupts the sorted-array baseline) ----
	// settick/addtick relocation — known-buggy in the baseline sorted array.
	int f5 = failures; reset();
	{
		int t1 = add_timer(100, rec_func, 1, 0);
		int t2 = add_timer(200, rec_func, 2, 0);
		int t3 = add_timer(300, rec_func, 3, 0);
		int t4 = add_timer(400, rec_func, 4, 0);
		int t5 = add_timer(500, rec_func, 5, 0);
		settick_timer(t5, 50);   // 500 -> 50: now soonest
		settick_timer(t1, 600);  // 100 -> 600: now latest
		do_timer(BIG);
		(void)t2;(void)t3;(void)t4;
		CHECK(fire_n == 5, "test5: all 5 fired after relocation");
		// expected fire order by new ticks: t5(50), t2(200), t3(300), t4(400), t1(600)
		int ok = (fire_n==5 && fire_id[0]==5 && fire_id[1]==2 &&
		          fire_id[2]==3 && fire_id[3]==4 && fire_id[4]==1);
		CHECK(ok, "test5: fired in relocated order [5,2,3,4,1]");
		if (!ok && fire_n>0) {
			int i; printf("    got order [");
			for (i=0;i<fire_n;i++) printf("%ld%s",(long)fire_id[i], i+1<fire_n?",":"");
			printf("]\n");
		}
	}
	printf("test5 (settick relocate): %s\n", failures==f5?"ok":"see above");

	timer_final();
	printf(failures==0 ? "\nALL OK\n" : "\n%d FAILURES\n", failures);
	return failures ? 1 : 0;
}
