// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Asynchronous character-load lane for the char-server.
//
// This is the READ counterpart to the map server's async_db write line, built
// by the same proven pattern (worker thread + its own MySQL connection + a
// request queue drained FIFO + a completion queue), but generalised to run an
// arbitrary *job* so it can execute the 8 dependent SELECTs of a full character
// load in a single round-trip.
//
// A job has two halves:
//   * work_fn(conn, ctx) runs on the WORKER thread with the lane's OWN MySQL
//     connection. It may run any number of queries and must write its results
//     ONLY into ctx (a caller-owned struct). It must NEVER touch live game
//     state (no shared caches, no session[], no sending) - that is not thread
//     safe.
//   * done_fn(ctx) runs on the GAME thread when poll() dispatches the finished
//     job. All game-state mutation and all network sends happen here. done_fn
//     owns ctx and must free it.
//
// So the game loop is never blocked on a character load, yet every byte of
// game-state mutation still happens single-threaded on the game thread.

#ifndef _CHAR_ASYNC_LOAD_H_
#define _CHAR_ASYNC_LOAD_H_

#ifndef CHAR_ASYNC_LOAD_TEST
#include <mysql.h>
#endif

typedef struct ACharLane ACharLane;

#ifdef CHAR_ASYNC_LOAD_TEST
typedef void MYSQL; // test build: the worker never dereferences the connection
#endif

// Runs on the worker thread with the lane's own connection. Fill ctx only.
typedef void (*acl_work_fn)(MYSQL* conn, void* ctx);
// Runs on the game thread via acl_poll(). Owns ctx; must free it.
typedef void (*acl_done_fn)(void* ctx);

// Create and start the lane with its own DB connection. Returns NULL on failure
// (the caller should then fall back to a synchronous load).
ACharLane* acl_create(const char* name, const char* ip, const char* user,
                      const char* pw, const char* db, int port, const char* codepage,
                      acl_work_fn work_fn, acl_done_fn done_fn);

// Enqueue one job. ctx is owned by the caller until done_fn frees it. Returns 1
// if queued, 0 if dropped (NULL lane/ctx or queue full). Game thread only.
int acl_submit(ACharLane* h, void* ctx);

// Dispatch all finished jobs to done_fn on the calling (game) thread. Returns
// the number dispatched. Call once per tick; cheap when nothing is ready.
int acl_poll(ACharLane* h);

// Jobs submitted but not yet dispatched by poll(). For metrics.
unsigned int acl_pending(ACharLane* h);

// Stop and join the worker, discard anything in flight WITHOUT calling done_fn
// (so the caller must not rely on done_fn for cleanup at shutdown). NULL-safe.
void acl_destroy(ACharLane* h);

#ifdef CHAR_ASYNC_LOAD_TEST
void     acl_test_run_worker_once(ACharLane* h); // process one queued job synchronously
unsigned acl_test_submitted(void);
#endif

#endif /* _CHAR_ASYNC_LOAD_H_ */
