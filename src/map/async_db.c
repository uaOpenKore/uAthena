// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Generic asynchronous SQL write engine. See async_db.h for the contract.
//
// Modelled on log_async.c: a linked-list queue guarded by a mutex/cond, a
// producer (game thread) that copies each statement into an owned node, and a
// worker thread that owns its own MySQL connection and drains the queue in
// FIFO order. The queue deliberately uses raw malloc/free: although the memory
// manager is now mutex-protected, going straight to libc keeps the worker off
// the game loop's allocator lock.

#include <pthread.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "async_db.h"

#define ASYNC_DB_WAKE_LEN    4096   // flush early once this many entries pile up
#define ASYNC_DB_MAX_QUEUE   65536  // hard cap: drop new entries beyond this

#ifndef ASYNC_DB_TEST
#include "../common/showmsg.h"
#include <mysql.h>
#include <errmsg.h>
#endif

struct async_db_node {
	struct async_db_node* next;
	char sql[1]; // statement text, allocated to fit
};

struct AsyncDB {
	char name[32];
	char ip[32], user[32], pw[32], db[32], codepage[32];
	int  port;
	int  flush_sec;

	struct async_db_node* q_head;
	struct async_db_node* q_tail;
	unsigned int q_len;
	unsigned int q_dropped;
	int q_flush_request;
	int q_shutdown;

	pthread_mutex_t mutex;
	pthread_cond_t  cond;
	pthread_t       tid;
	int             running;
	int             connected;

#ifndef ASYNC_DB_TEST
	MYSQL mysql;
#endif
};

/*==========================================
 * DB seam - real MySQL vs. recording test sink
 *------------------------------------------*/
#ifndef ASYNC_DB_TEST

static int adb_thread_setup(void)   { mysql_thread_init(); return 0; }
static void adb_thread_teardown(void){ mysql_thread_end(); }

static int adb_connect(AsyncDB* h)
{
	mysql_init(&h->mysql);
	if (!mysql_real_connect(&h->mysql, h->ip, h->user, h->pw, h->db, h->port, NULL, 0)) {
		ShowSQL("async_db[%s]: connect to %s:%d failed - %s\n", h->name, h->ip, h->port, mysql_error(&h->mysql));
		mysql_close(&h->mysql);
		return 0;
	}
	if (h->codepage[0] != '\0') {
		char buf[64];
		snprintf(buf, sizeof(buf), "SET NAMES %s", h->codepage);
		if (mysql_query(&h->mysql, buf))
			ShowSQL("async_db[%s]: %s failed - %s\n", h->name, buf, mysql_error(&h->mysql));
	}
	return 1;
}

static int adb_ping(AsyncDB* h)  { return mysql_ping(&h->mysql); } // 0 = alive
static void adb_close(AsyncDB* h){ mysql_close(&h->mysql); }

// 0 = success, 1 = statement error (skip), 2 = connection lost (requeue)
static int adb_exec(AsyncDB* h, const char* sql)
{
	if (!mysql_query(&h->mysql, sql))
		return 0;
	{
		unsigned int err = mysql_errno(&h->mysql);
		if (err == CR_SERVER_GONE_ERROR || err == CR_SERVER_LOST)
			return 2;
		// statement-level error (bad data etc.): report and move on.
		// %.1800s keeps the message inside showmsg's stack buffer.
		ShowSQL("async_db[%s]: DB error - %s\n", h->name, mysql_error(&h->mysql));
		ShowDebug("async_db[%s]: failed statement: %.1800s\n", h->name, sql);
		return 1;
	}
}

#else /* ASYNC_DB_TEST: no real MySQL, record into a sink */

#define ShowSQL(...)     ((void)0)
#define ShowDebug(...)   ((void)0)
#define ShowWarning(...) ((void)0)
#define ShowStatus(...)  ((void)0)

#define ADB_SINK_MAX 70000
static char* adb_sink[ADB_SINK_MAX];
static unsigned adb_sink_n = 0;
static int adb_fail_servergone = 0;

void async_db_test_reset(void)
{
	unsigned i;
	for (i = 0; i < adb_sink_n; i++) free(adb_sink[i]);
	adb_sink_n = 0;
	adb_fail_servergone = 0;
}
unsigned    async_db_test_count(void)        { return adb_sink_n; }
const char* async_db_test_stmt(unsigned i)   { return (i < adb_sink_n) ? adb_sink[i] : ""; }
void        async_db_test_fail_servergone(int n) { adb_fail_servergone = n; }

static int adb_thread_setup(void)    { return 0; }
static void adb_thread_teardown(void){ }
static int adb_connect(AsyncDB* h)   { (void)h; return 1; }
static int adb_ping(AsyncDB* h)      { (void)h; return 0; }
static void adb_close(AsyncDB* h)    { (void)h; }

static int adb_exec(AsyncDB* h, const char* sql)
{
	(void)h;
	if (adb_fail_servergone > 0) { adb_fail_servergone--; return 2; } // connection lost
	if (adb_sink_n < ADB_SINK_MAX) {
		adb_sink[adb_sink_n] = (char*)malloc(strlen(sql) + 1);
		if (adb_sink[adb_sink_n]) { strcpy(adb_sink[adb_sink_n], sql); adb_sink_n++; }
	}
	return 0;
}
#endif

/*==========================================
 * Queue plumbing (shared by both builds)
 *------------------------------------------*/

// Execute one detached batch. Returns 1 on success, 0 if the connection died
// (caller requeues the remaining nodes starting at *remain).
static int adb_run_batch(AsyncDB* h, struct async_db_node* batch, struct async_db_node** remain)
{
	while (batch) {
		struct async_db_node* next = batch->next;
		if (adb_exec(h, batch->sql) == 2) {
			*remain = batch; // connection lost: keep this and the rest for retry
			return 0;
		}
		free(batch);
		batch = next;
	}
	*remain = NULL;
	return 1;
}

// Put a batch that could not be executed back at the head, preserving order.
static void adb_requeue(AsyncDB* h, struct async_db_node* batch)
{
	struct async_db_node* tail = batch;
	unsigned int n = 1;
	if (batch == NULL)
		return;
	while (tail->next) { tail = tail->next; n++; }
	pthread_mutex_lock(&h->mutex);
	tail->next = h->q_head;
	h->q_head = batch;
	if (h->q_tail == NULL)
		h->q_tail = tail;
	h->q_len += n;
	pthread_mutex_unlock(&h->mutex);
}

// Grab the whole queue and flush it. Returns the shutdown flag seen this cycle.
static int adb_flush_once(AsyncDB* h)
{
	struct async_db_node* batch;
	struct async_db_node* remain;
	unsigned int dropped;
	int quit;

	pthread_mutex_lock(&h->mutex);
	h->q_flush_request = 0;
	quit = h->q_shutdown;
	batch = h->q_head;
	h->q_head = h->q_tail = NULL;
	h->q_len = 0;
	dropped = h->q_dropped;
	h->q_dropped = 0;
	pthread_mutex_unlock(&h->mutex);

	if (dropped)
		ShowWarning("async_db[%s]: queue overflow, %u statements dropped.\n", h->name, dropped);

	if (batch) {
		if (!h->connected)
			h->connected = adb_connect(h);
		else if (adb_ping(h)) {
			adb_close(h);
			h->connected = adb_connect(h);
		}
		if (h->connected) {
			if (!adb_run_batch(h, batch, &remain)) {
				adb_close(h);
				h->connected = 0;
				batch = remain;
			} else
				batch = NULL;
		}
		if (batch) { // DB unreachable: keep for the next cycle (unless quitting)
			if (quit) {
				unsigned int lost = 0;
				while (batch) {
					struct async_db_node* next = batch->next;
					free(batch);
					batch = next;
					lost++;
				}
				ShowWarning("async_db[%s]: DB unreachable on shutdown, %u statements lost.\n", h->name, lost);
			} else
				adb_requeue(h, batch);
		}
	}
	return quit;
}

static void* adb_worker(void* arg)
{
	AsyncDB* h = (AsyncDB*)arg;

	adb_thread_setup();
	h->connected = adb_connect(h);

	for (;;) {
		struct timespec deadline;
		int quit;

		clock_gettime(CLOCK_REALTIME, &deadline);
		deadline.tv_sec += h->flush_sec;

		pthread_mutex_lock(&h->mutex);
		while (!h->q_shutdown && !h->q_flush_request) {
			if (pthread_cond_timedwait(&h->cond, &h->mutex, &deadline) == ETIMEDOUT)
				break;
		}
		pthread_mutex_unlock(&h->mutex);

		quit = adb_flush_once(h);
		if (quit)
			break;
	}

	if (h->connected)
		adb_close(h);
	adb_thread_teardown();
	return NULL;
}

static int adb_enqueue(AsyncDB* h, const char* sql)
{
	struct async_db_node* node;
	size_t len;

	if (h == NULL)
		return 0;

	len = strlen(sql);
	node = (struct async_db_node*)malloc(sizeof(struct async_db_node) + len);
	if (node == NULL)
		return 0;
	memcpy(node->sql, sql, len + 1);
	node->next = NULL;

	pthread_mutex_lock(&h->mutex);
	if (h->q_len >= ASYNC_DB_MAX_QUEUE) {
		h->q_dropped++;
		pthread_mutex_unlock(&h->mutex);
		free(node);
		return 0;
	}
	if (h->q_tail)
		h->q_tail->next = node;
	else
		h->q_head = node;
	h->q_tail = node;
	if (++h->q_len == ASYNC_DB_WAKE_LEN) {
		h->q_flush_request = 1;
		pthread_cond_signal(&h->cond);
	}
	pthread_mutex_unlock(&h->mutex);
	return 1;
}

/*==========================================
 * Public API
 *------------------------------------------*/

static void adb_copy(char* dst, const char* src, size_t n)
{
	if (src == NULL) { dst[0] = '\0'; return; }
	strncpy(dst, src, n - 1);
	dst[n - 1] = '\0';
}

AsyncDB* async_db_create(const char* name, const char* ip, const char* user,
                         const char* pw, const char* db, int port,
                         const char* codepage, int flush_sec)
{
	AsyncDB* h = (AsyncDB*)calloc(1, sizeof(AsyncDB));
	if (h == NULL)
		return NULL;

	adb_copy(h->name, name ? name : "async_db", sizeof(h->name));
	adb_copy(h->ip, ip, sizeof(h->ip));
	adb_copy(h->user, user, sizeof(h->user));
	adb_copy(h->pw, pw, sizeof(h->pw));
	adb_copy(h->db, db, sizeof(h->db));
	adb_copy(h->codepage, codepage, sizeof(h->codepage));
	h->port = port;
	h->flush_sec = (flush_sec > 0) ? flush_sec : 15;

	pthread_mutex_init(&h->mutex, NULL);
	pthread_cond_init(&h->cond, NULL);

#ifndef ASYNC_DB_TEST
	if (pthread_create(&h->tid, NULL, adb_worker, h) != 0) {
		ShowWarning("async_db[%s]: pthread_create failed - writes will be lost.\n", h->name);
		pthread_mutex_destroy(&h->mutex);
		pthread_cond_destroy(&h->cond);
		free(h);
		return NULL;
	}
	h->running = 1;
	ShowStatus("async_db[%s]: writer started (flush every %d seconds).\n", h->name, h->flush_sec);
#endif
	return h;
}

int async_db_submit(AsyncDB* h, const char* sql)
{
	return adb_enqueue(h, sql);
}

void async_db_destroy(AsyncDB* h)
{
	if (h == NULL)
		return;

	if (h->running) {
		pthread_mutex_lock(&h->mutex);
		h->q_shutdown = 1;
		pthread_cond_signal(&h->cond);
		pthread_mutex_unlock(&h->mutex);
		pthread_join(h->tid, NULL);
		h->running = 0;
	} else {
		// No worker was started (test path / failed create): drain inline.
		pthread_mutex_lock(&h->mutex);
		h->q_shutdown = 1;
		pthread_mutex_unlock(&h->mutex);
		while (h->q_head)
			adb_flush_once(h);
		if (h->connected)
			adb_close(h);
	}

	// Free anything left (paranoia - the worker should have drained it).
	while (h->q_head) {
		struct async_db_node* next = h->q_head->next;
		free(h->q_head);
		h->q_head = next;
	}
	pthread_mutex_destroy(&h->mutex);
	pthread_cond_destroy(&h->cond);
	free(h);
}

#ifdef ASYNC_DB_TEST
int  async_db__enqueue(AsyncDB* h, const char* sql) { return adb_enqueue(h, sql); }
void async_db__drain_once(AsyncDB* h)               { adb_flush_once(h); }
void async_db__start_worker(AsyncDB* h)
{
	if (h && !h->running && pthread_create(&h->tid, NULL, adb_worker, h) == 0)
		h->running = 1;
}
#endif
