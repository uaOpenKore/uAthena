// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Generic asynchronous SQL *read* engine for the map server.
//
// The write engine (async_db.c) is fire-and-forget: the game never needs the
// result back. Reads are different -- the caller needs the rows to continue --
// so blocking the single-threaded game loop on a SELECT round-trip is exactly
// what we must avoid during a login storm.
//
// This engine mirrors async_db.c but adds a RESULT path:
//   1. The game thread calls async_read_submit() with a fully-formed SELECT, a
//      callback and an opaque context. The call returns immediately.
//   2. A dedicated worker thread (its OWN MySQL connection) runs the query,
//      copies the ENTIRE result set into a self-contained snapshot (every cell
//      strdup'd), frees the live MySQL result, and parks the snapshot on a
//      completion queue.
//   3. The game thread calls async_read_poll() once per tick; for each finished
//      request it invokes the callback WITH THE SNAPSHOT, ON THE GAME THREAD,
//      then frees the snapshot.
//
// INVARIANT (same as async_db): the worker thread only ever touches the SQL
// text it was handed, its own connection, and the snapshot it allocates. It
// NEVER reads or writes live game state. All game-state mutation happens in the
// callback, which runs on the game thread via async_read_poll(). The callback
// must not block.
//
// Connection loss is retried once inside the worker; if it still fails the
// snapshot is delivered with err=1 so the callback can fall back gracefully
// (the game thread is never blocked and the player is never hard-refused).

#ifndef _MAP_ASYNC_READ_H_
#define _MAP_ASYNC_READ_H_

typedef struct AsyncRead AsyncRead;

// A self-contained snapshot of a result set, owned by the engine and valid only
// for the duration of the callback. Cells are row-major (row*nfields+col). A
// cell may be NULL (SQL NULL). On error, err=1 and nrows=0.
typedef struct AsyncReadResult {
	int err;        // 0 = ok, 1 = query/connection error (rows empty)
	int nrows;
	int nfields;
	char** cell;    // nrows*nfields entries; cell[r*nfields+c], may be NULL
} AsyncReadResult;

// Callback invoked on the GAME THREAD by async_read_poll(). ctx is whatever was
// passed to submit(); res is owned by the engine and freed right after return.
typedef void (*async_read_cb)(void* ctx, const AsyncReadResult* res);

// Create and start a reader with its own connection. Returns NULL on failure
// (callers should then fall back to a synchronous query).
AsyncRead* async_read_create(const char* name, const char* ip, const char* user,
                             const char* pw, const char* db, int port,
                             const char* codepage);

// Enqueue one SELECT (text copied). cb is required. Returns 1 if queued, 0 if
// dropped (NULL engine/cb or queue full). Call from the game thread only.
int async_read_submit(AsyncRead* h, const char* sql, async_read_cb cb, void* ctx);

// Dispatch all finished reads to their callbacks on the calling (game) thread.
// Returns the number dispatched. Call once per tick. Cheap when nothing is ready.
int async_read_poll(AsyncRead* h);

// Number of requests still in flight (queued or running). For metrics.
unsigned int async_read_pending(AsyncRead* h);

// Stop and join the worker, discard anything in flight (pending callbacks are
// NOT invoked), free the engine. NULL-safe.
void async_read_destroy(AsyncRead* h);

#ifdef ASYNC_READ_TEST
// Test seam (no real MySQL): a canned result is returned for every query.
void     async_read_test_reset(void);
void     async_read_test_set_rows(int nrows, int nfields, const char* const* cells); // row-major
void     async_read_test_fail_servergone(int n); // next n execs report conn-lost
unsigned async_read_test_submitted(void);
void     async_read__run_worker_once(AsyncRead* h); // process one queued req synchronously
#endif

#endif /* _MAP_ASYNC_READ_H_ */
