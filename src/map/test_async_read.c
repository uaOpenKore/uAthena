// Standalone unit test for the async_read read engine.
//
// Not part of `make sql`. Build & run with:
//   gcc -DASYNC_READ_TEST -I src/map -o /tmp/test_async_read src/map/async_read.c src/map/test_async_read.c -lpthread
//   /tmp/test_async_read
//
// Uses the canned-row test seam (no real MySQL) and drives the worker
// synchronously via async_read__run_worker_once(), so the result-snapshot path,
// callback dispatch on the game thread, empty results and connection-loss retry
// are verified deterministically.

#include "async_read.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

// Callback capture
static int cb_calls = 0;
static int cb_err = -1;
static int cb_nrows = -1, cb_nfields = -1;
static char cb_00[64], cb_11[64];

static void on_result(void* ctx, const AsyncReadResult* res)
{
	int* tag = (int*)ctx;
	cb_calls++;
	if (tag) *tag = 1;
	cb_err = res->err;
	cb_nrows = res->nrows;
	cb_nfields = res->nfields;
	cb_00[0] = cb_11[0] = '\0';
	if (!res->err && res->nrows >= 1 && res->nfields >= 1 && res->cell[0])
		{ strncpy(cb_00, res->cell[0], sizeof(cb_00)-1); cb_00[sizeof(cb_00)-1]='\0'; }
	if (!res->err && res->nrows >= 2 && res->nfields >= 2 && res->cell[1*res->nfields+1])
		{ strncpy(cb_11, res->cell[1*res->nfields+1], sizeof(cb_11)-1); cb_11[sizeof(cb_11)-1]='\0'; }
}

static void reset_capture(void){ cb_calls=0; cb_err=-1; cb_nrows=cb_nfields=-1; cb_00[0]=cb_11[0]='\0'; }

int main(void)
{
	AsyncRead* h = async_read_create("test", "", "", "", "", 0, "");
	CHECK(h != NULL, "async_read_create returns an engine");

	// 1. A 2x2 result set is snapshotted and delivered to the callback verbatim.
	{
		const char* rows[] = { "r0c0","r0c1", "r1c0","r1c1" };
		int tag = 0;
		async_read_test_set_rows(2, 2, rows);
		reset_capture();
		async_read_submit(h, "SELECT ...", on_result, &tag);
		CHECK(async_read_pending(h) == 1, "pending == 1 after submit, before poll");
		CHECK(cb_calls == 0, "callback NOT called before poll (stays off game thread)");
		async_read__run_worker_once(h);          // worker builds the snapshot
		CHECK(cb_calls == 0, "callback still not called until poll()");
		async_read_poll(h);                       // game thread dispatches
		CHECK(cb_calls == 1 && tag == 1, "callback fired exactly once on poll");
		CHECK(cb_err == 0, "result marked ok");
		CHECK(cb_nrows == 2 && cb_nfields == 2, "dimensions preserved (2x2)");
		CHECK(strcmp(cb_00, "r0c0") == 0, "cell[0][0] preserved");
		CHECK(strcmp(cb_11, "r1c1") == 0, "cell[1][1] preserved");
		CHECK(async_read_pending(h) == 0, "pending back to 0 after dispatch");
	}

	// 2. Empty result set: ok, zero rows, callback still fires.
	{
		const char* none[] = { NULL };
		async_read_test_set_rows(0, 0, none);
		reset_capture();
		async_read_submit(h, "SELECT ... WHERE 0", on_result, NULL);
		async_read__run_worker_once(h);
		async_read_poll(h);
		CHECK(cb_calls == 1 && cb_err == 0 && cb_nrows == 0, "empty result delivered ok with 0 rows");
	}

	// 3. Connection lost on first try -> engine retries; still lost -> err delivered.
	{
		const char* rows[] = { "x" };
		async_read_test_set_rows(1, 1, rows);
		async_read_test_fail_servergone(2); // both the initial exec and the retry fail
		reset_capture();
		async_read_submit(h, "SELECT ...", on_result, NULL);
		async_read__run_worker_once(h);
		async_read_poll(h);
		CHECK(cb_calls == 1 && cb_err == 1, "persistent connection loss -> err=1 delivered (never blocks)");
	}

	// 4. Connection lost once then recovers -> result delivered ok.
	{
		const char* rows[] = { "y" };
		async_read_test_set_rows(1, 1, rows);
		async_read_test_fail_servergone(1); // only the first exec fails; retry succeeds
		reset_capture();
		async_read_submit(h, "SELECT ...", on_result, NULL);
		async_read__run_worker_once(h);
		async_read_poll(h);
		CHECK(cb_calls == 1 && cb_err == 0 && strcmp(cb_00, "y") == 0, "one-shot conn loss recovered on retry");
	}

	// 5. FIFO: three submits, processed and dispatched in order.
	{
		const char* rows[] = { "Z" };
		async_read_test_set_rows(1, 1, rows);
		reset_capture();
		async_read_submit(h, "Q1", on_result, NULL);
		async_read_submit(h, "Q2", on_result, NULL);
		async_read_submit(h, "Q3", on_result, NULL);
		CHECK(async_read_pending(h) == 3, "three in flight");
		async_read__run_worker_once(h);
		async_read__run_worker_once(h);
		async_read__run_worker_once(h);
		async_read_poll(h);
		CHECK(cb_calls == 3 && async_read_pending(h) == 0, "all three dispatched, pending drained");
	}

	async_read_destroy(h);
	printf(failures ? "\n%d FAILURE(S)\n" : "\nALL TESTS PASSED\n", failures);
	return failures ? 1 : 0;
}
