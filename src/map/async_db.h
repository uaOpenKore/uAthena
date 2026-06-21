// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Generic asynchronous SQL *write* engine for the map server.
//
// The single-threaded game loop must never block on a DB round-trip. With
// this engine the game thread serialises a fully-formed SQL statement (an
// owned copy of the text) and hands it to a dedicated worker thread that owns
// its OWN MySQL connection and drains the queue in FIFO order, every
// flush_sec seconds (or earlier once the queue grows). This mirrors the proven
// log_async.c, generalised to an instance so several independent writers can
// coexist (e.g. one per DB).
//
// INVARIANT: the worker thread only ever touches the strings handed to it and
// its own connection - it NEVER reads or writes live game state. Anything that
// needs live state must be serialised on the game thread before submit().
//
// This engine is for writes whose result the game does not need back (INSERT/
// UPDATE/DELETE). Reads, which must return data, are handled separately.

#ifndef _MAP_ASYNC_DB_H_
#define _MAP_ASYNC_DB_H_

typedef struct AsyncDB AsyncDB;

// Create and start a writer with its own connection to the given database.
// flush_sec <= 0 falls back to a sane default. Returns NULL on failure (the
// caller should then fall back to a synchronous query).
AsyncDB* async_db_create(const char* name, const char* ip, const char* user,
                         const char* pw, const char* db, int port,
                         const char* codepage, int flush_sec);

// Enqueue one statement (the text is copied). Returns 1 if queued, 0 if it was
// dropped (NULL engine or queue full). Call from the game thread only.
int async_db_submit(AsyncDB* h, const char* sql);

// Drain the queue, stop and join the worker, free the engine. NULL-safe.
void async_db_destroy(AsyncDB* h);

#ifdef ASYNC_DB_TEST
// Test-only seam, compiled out of the production binary. Lets a single-thread
// test drive the producer/consumer deterministically and inspect what the
// worker "executed" through a recording sink instead of a real DB.
void        async_db_test_reset(void);             // clear sink + fail counter
unsigned    async_db_test_count(void);             // # statements the sink ran
const char* async_db_test_stmt(unsigned i);        // i-th executed statement
void        async_db_test_fail_servergone(int n);  // next n execs report conn-lost
int         async_db__enqueue(AsyncDB* h, const char* sql); // raw producer (no worker)
void        async_db__drain_once(AsyncDB* h);      // one synchronous flush cycle
void        async_db__start_worker(AsyncDB* h);    // spawn the real worker thread
#endif

#endif /* _MAP_ASYNC_DB_H_ */
