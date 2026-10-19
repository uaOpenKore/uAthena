// Standalone unit test for the async character-load lane (queue/poll/threading
// logic, independent of MySQL). Build & run with:
//   gcc -DCHAR_ASYNC_LOAD_TEST -I src/char_sql -o /tmp/test_char_async_load \
//       src/char_sql/char_async_load.c src/char_sql/test_char_async_load.c -lpthread
//   /tmp/test_char_async_load
//
// The work_fn/done_fn pair is driven synchronously via acl_test_run_worker_once()
// so FIFO order, the "callback only on poll" rule, pending accounting and ctx
// ownership (freed in done_fn) are verified deterministically.

#include "char_async_load.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

struct job { int seq; int worked; };

static int worked_count = 0;
static int done_count = 0;
static int done_seq[16];

static void work_fn(MYSQL* conn, void* ctx)
{
	struct job* j = (struct job*)ctx;
	(void)conn;        // test build: never dereferenced
	j->worked = 1;
	worked_count++;
}

static void done_fn(void* ctx)
{
	struct job* j = (struct job*)ctx;
	if (done_count < 16) done_seq[done_count] = j->seq;
	done_count++;
	free(j); // done_fn owns ctx
}

int main(void)
{
	ACharLane* h = acl_create("t", "", "", "", "", 0, "", work_fn, done_fn);
	CHECK(h != NULL, "acl_create returns a lane");
	CHECK(acl_create("t", "", "", "", "", 0, "", NULL, done_fn) == NULL, "acl_create rejects NULL work_fn");

	// 1. One job: worker runs work_fn, poll runs done_fn. Callbacks never early.
	{
		struct job* j = (struct job*)calloc(1, sizeof(struct job));
		j->seq = 1;
		worked_count = done_count = 0;
		acl_submit(h, j);
		CHECK(acl_pending(h) == 1, "pending==1 after submit");
		CHECK(worked_count == 0 && done_count == 0, "no callback before worker runs");
		acl_test_run_worker_once(h);
		CHECK(worked_count == 1, "work_fn ran on worker");
		CHECK(done_count == 0, "done_fn NOT run until poll (stays off game thread)");
		CHECK(acl_poll(h) == 1, "poll dispatches one");
		CHECK(done_count == 1, "done_fn ran on poll");
		CHECK(acl_pending(h) == 0, "pending back to 0");
	}

	// 2. FIFO over three jobs.
	{
		int k;
		worked_count = done_count = 0;
		for (k = 0; k < 3; k++) { struct job* j = (struct job*)calloc(1,sizeof(struct job)); j->seq = 10+k; acl_submit(h, j); }
		CHECK(acl_pending(h) == 3, "three pending");
		for (k = 0; k < 3; k++) acl_test_run_worker_once(h);
		acl_poll(h);
		CHECK(done_count == 3, "all three done");
		CHECK(done_seq[0]==10 && done_seq[1]==11 && done_seq[2]==12, "FIFO order preserved");
		CHECK(acl_pending(h) == 0, "pending drained");
	}

	// 3. NULL ctx rejected.
	CHECK(acl_submit(h, NULL) == 0, "submit rejects NULL ctx");

	acl_destroy(h);
	printf(failures ? "\n%d FAILURE(S)\n" : "\nALL TESTS PASSED\n", failures);
	return failures ? 1 : 0;
}
