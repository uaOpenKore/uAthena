// Standalone unit test for the async_db write engine.
//
// Not part of `make sql`. Build & run with:
//   gcc -DASYNC_DB_TEST -I src/map -o /tmp/test_async_db src/map/async_db.c src/map/test_async_db.c -lpthread
//   /tmp/test_async_db
//
// Drives the producer/consumer with a recording sink (no real MySQL), so the
// concurrency-critical logic - FIFO order, overflow drop, connection-loss
// requeue, drain-on-shutdown - is verified deterministically.

// ASYNC_DB_TEST is provided on the compiler command line (-DASYNC_DB_TEST).
#include "async_db.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

int main(void)
{
	AsyncDB* h = async_db_create("test", "", "", "", "", 0, "", 15);
	CHECK(h != NULL, "async_db_create returns an engine");

	// 1. FIFO order: enqueue then one synchronous drain executes all in order.
	async_db_test_reset();
	async_db__enqueue(h, "A");
	async_db__enqueue(h, "B");
	async_db__enqueue(h, "C");
	async_db__drain_once(h);
	CHECK(async_db_test_count() == 3, "drain executes all queued statements");
	CHECK(async_db_test_count() == 3
	   && strcmp(async_db_test_stmt(0), "A") == 0
	   && strcmp(async_db_test_stmt(1), "B") == 0
	   && strcmp(async_db_test_stmt(2), "C") == 0, "FIFO order preserved");

	// 2. Connection lost -> batch requeued, delivered on the next cycle.
	async_db_test_reset();
	async_db_test_fail_servergone(1);   // first exec reports the server gone
	async_db__enqueue(h, "X");
	async_db__drain_once(h);            // fails -> X requeued, nothing executed
	CHECK(async_db_test_count() == 0, "connection-lost: nothing executed yet");
	async_db__drain_once(h);            // reconnect -> X delivered
	CHECK(async_db_test_count() == 1
	   && strcmp(async_db_test_stmt(0), "X") == 0, "requeued statement delivered next cycle");

	// 3. Overflow: the queue caps and drops beyond the hard limit.
	async_db_test_reset();
	{
		int i, dropped_at = -1;
		for (i = 0; i < 65536 + 50; i++) {
			if (!async_db__enqueue(h, "Q")) { dropped_at = i; break; }
		}
		CHECK(dropped_at >= 65536, "queue caps at the hard limit (drops beyond)");
	}
	async_db__drain_once(h);            // clear the backlog

	// 4. Real worker thread: submit, then destroy drains before join.
	async_db_test_reset();
	async_db__start_worker(h);
	async_db_submit(h, "T1");
	async_db_submit(h, "T2");
	async_db_destroy(h);                // joins worker, draining the queue
	CHECK(async_db_test_count() == 2, "destroy drains the worker queue");
	CHECK(async_db_test_count() == 2
	   && strcmp(async_db_test_stmt(0), "T1") == 0
	   && strcmp(async_db_test_stmt(1), "T2") == 0, "worker preserves FIFO order");

	printf(failures ? "\n%d CHECK(S) FAILED\n" : "\nALL CHECKS PASSED\n", failures);
	return failures ? 1 : 0;
}
