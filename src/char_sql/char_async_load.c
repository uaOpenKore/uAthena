// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Asynchronous character-load lane. See char_async_load.h for the contract.
//
// Same producer/consumer shape as the map server's async_db/async_read: a
// mutex/cond-guarded request queue drained by one worker thread that owns its
// MySQL connection, plus a completion queue the game thread drains in poll().
// The difference from async_read is that a job carries a caller work_fn/done_fn
// pair instead of a single SQL string, so one job can run the whole multi-query
// character load in a single round-trip. Raw malloc/free keeps the worker off
// the game loop's allocator lock, exactly like async_db.

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "char_async_load.h"

#define ACL_MAX_QUEUE 65536 // hard cap on jobs in flight

#ifndef CHAR_ASYNC_LOAD_TEST
#include "../common/showmsg.h"
#include <mysql.h>
#endif

struct acl_node {
	struct acl_node* next;
	void* ctx;
};

struct ACharLane {
	char name[32];
	char ip[32], user[32], pw[32], db[32], codepage[32];
	int  port;
	acl_work_fn work_fn;
	acl_done_fn done_fn;

	struct acl_node* q_head;
	struct acl_node* q_tail;
	unsigned int q_len;
	unsigned int q_dropped;
	struct acl_node* done_head;
	struct acl_node* done_tail;
	unsigned int inflight;

	int q_shutdown;
	pthread_mutex_t mutex;
	pthread_cond_t  cond;
	pthread_t       tid;
	int             running;
	int             connected;

#ifndef CHAR_ASYNC_LOAD_TEST
	MYSQL mysql;
#endif
};

/*==========================================
 * DB connection seam (real vs test)
 *------------------------------------------*/
#ifndef CHAR_ASYNC_LOAD_TEST

static void acl_thread_setup(void)    { mysql_thread_init(); }
static void acl_thread_teardown(void) { mysql_thread_end(); }

static int acl_connect(ACharLane* h)
{
	mysql_init(&h->mysql);
	if (!mysql_real_connect(&h->mysql, h->ip, h->user, h->pw, h->db, h->port, NULL, 0)) {
		ShowSQL("char_async_load[%s]: connect to %s:%d failed - %s\n", h->name, h->ip, h->port, mysql_error(&h->mysql));
		mysql_close(&h->mysql);
		return 0;
	}
	if (h->codepage[0] != '\0') {
		char buf[64];
		snprintf(buf, sizeof(buf), "SET NAMES %s", h->codepage);
		if (mysql_query(&h->mysql, buf))
			ShowSQL("char_async_load[%s]: %s failed - %s\n", h->name, buf, mysql_error(&h->mysql));
	}
	return 1;
}
static int  acl_ping(ACharLane* h)  { return mysql_ping(&h->mysql); } // 0 = alive
static void acl_close(ACharLane* h) { mysql_close(&h->mysql); }
static MYSQL* acl_conn(ACharLane* h){ return &h->mysql; }

#else /* CHAR_ASYNC_LOAD_TEST */

#define ShowSQL(...)     ((void)0)
#define ShowWarning(...) ((void)0)
#define ShowStatus(...)  ((void)0)
static unsigned acl_submitted = 0;
static void acl_thread_setup(void)    { }
static void acl_thread_teardown(void) { }
static int  acl_connect(ACharLane* h) { (void)h; return 1; }
static int  acl_ping(ACharLane* h)    { (void)h; return 0; }
static void acl_close(ACharLane* h)   { (void)h; }
static MYSQL* acl_conn(ACharLane* h)  { (void)h; return (MYSQL*)0; }

#endif

/*==========================================
 * Worker
 *------------------------------------------*/
static void acl_process(ACharLane* h, struct acl_node* node)
{
	if (!h->connected)
		h->connected = acl_connect(h);
	else if (acl_ping(h)) {
		acl_close(h);
		h->connected = acl_connect(h);
	}

	// Run the caller's work even if the connection is down: work_fn is expected
	// to detect a NULL/failed query via its own error path and mark ctx as
	// failed, so done_fn can fall back gracefully. We still pass the connection
	// (valid or not) exactly once.
	h->work_fn(acl_conn(h), node->ctx);

	pthread_mutex_lock(&h->mutex);
	node->next = NULL;
	if (h->done_tail) h->done_tail->next = node;
	else              h->done_head = node;
	h->done_tail = node;
	pthread_mutex_unlock(&h->mutex);
}

static void* acl_worker(void* arg)
{
	ACharLane* h = (ACharLane*)arg;
	acl_thread_setup();
	h->connected = acl_connect(h);

	for (;;) {
		struct acl_node* node;
		pthread_mutex_lock(&h->mutex);
		while (!h->q_shutdown && h->q_head == NULL)
			pthread_cond_wait(&h->cond, &h->mutex);
		if (h->q_shutdown && h->q_head == NULL) {
			pthread_mutex_unlock(&h->mutex);
			break;
		}
		node = h->q_head;
		h->q_head = node->next;
		if (h->q_head == NULL) h->q_tail = NULL;
		h->q_len--;
		pthread_mutex_unlock(&h->mutex);

		node->next = NULL;
		acl_process(h, node);
	}

	if (h->connected) acl_close(h);
	acl_thread_teardown();
	return NULL;
}

/*==========================================
 * Public API
 *------------------------------------------*/
static void acl_copy(char* dst, const char* src, size_t n)
{
	if (src == NULL) { dst[0] = '\0'; return; }
	strncpy(dst, src, n - 1);
	dst[n - 1] = '\0';
}

ACharLane* acl_create(const char* name, const char* ip, const char* user,
                      const char* pw, const char* db, int port, const char* codepage,
                      acl_work_fn work_fn, acl_done_fn done_fn)
{
	ACharLane* h;
	if (work_fn == NULL || done_fn == NULL)
		return NULL;
	h = (ACharLane*)calloc(1, sizeof(ACharLane));
	if (h == NULL)
		return NULL;

	acl_copy(h->name, name ? name : "char_load", sizeof(h->name));
	acl_copy(h->ip, ip, sizeof(h->ip));
	acl_copy(h->user, user, sizeof(h->user));
	acl_copy(h->pw, pw, sizeof(h->pw));
	acl_copy(h->db, db, sizeof(h->db));
	acl_copy(h->codepage, codepage, sizeof(h->codepage));
	h->port = port;
	h->work_fn = work_fn;
	h->done_fn = done_fn;

	pthread_mutex_init(&h->mutex, NULL);
	pthread_cond_init(&h->cond, NULL);

#ifndef CHAR_ASYNC_LOAD_TEST
	if (pthread_create(&h->tid, NULL, acl_worker, h) != 0) {
		ShowWarning("char_async_load[%s]: pthread_create failed.\n", h->name);
		pthread_mutex_destroy(&h->mutex);
		pthread_cond_destroy(&h->cond);
		free(h);
		return NULL;
	}
	h->running = 1;
	ShowStatus("char_async_load[%s]: worker started.\n", h->name);
#endif
	return h;
}

int acl_submit(ACharLane* h, void* ctx)
{
	struct acl_node* node;
	if (h == NULL || ctx == NULL)
		return 0;
	node = (struct acl_node*)malloc(sizeof(struct acl_node));
	if (node == NULL)
		return 0;
	node->ctx = ctx;
	node->next = NULL;

	pthread_mutex_lock(&h->mutex);
	if (h->q_len >= ACL_MAX_QUEUE) {
		h->q_dropped++;
		pthread_mutex_unlock(&h->mutex);
		free(node);
		return 0;
	}
	if (h->q_tail) h->q_tail->next = node;
	else           h->q_head = node;
	h->q_tail = node;
	h->q_len++;
	h->inflight++;
#ifdef CHAR_ASYNC_LOAD_TEST
	acl_submitted++;
#endif
	pthread_cond_signal(&h->cond);
	pthread_mutex_unlock(&h->mutex);
	return 1;
}

int acl_poll(ACharLane* h)
{
	struct acl_node* done;
	int dispatched = 0;
	if (h == NULL)
		return 0;

	pthread_mutex_lock(&h->mutex);
	done = h->done_head;
	h->done_head = h->done_tail = NULL;
	pthread_mutex_unlock(&h->mutex);

	while (done) {
		struct acl_node* next = done->next;
		h->done_fn(done->ctx); // game thread: frees ctx, touches game state, sends
		free(done);
		dispatched++;
		done = next;
	}
	if (dispatched) {
		pthread_mutex_lock(&h->mutex);
		h->inflight -= (unsigned int)dispatched;
		pthread_mutex_unlock(&h->mutex);
	}
	return dispatched;
}

unsigned int acl_pending(ACharLane* h)
{
	unsigned int n;
	if (h == NULL) return 0;
	pthread_mutex_lock(&h->mutex);
	n = h->inflight;
	pthread_mutex_unlock(&h->mutex);
	return n;
}

void acl_destroy(ACharLane* h)
{
	struct acl_node* n;
	if (h == NULL) return;

	if (h->running) {
		pthread_mutex_lock(&h->mutex);
		h->q_shutdown = 1;
		pthread_cond_signal(&h->cond);
		pthread_mutex_unlock(&h->mutex);
		pthread_join(h->tid, NULL);
		h->running = 0;
	} else if (h->connected) {
		acl_close(h);
	}

	// Discard in-flight ctx WITHOUT done_fn: on shutdown the game state is going
	// away anyway. Note this leaks whatever done_fn would have freed, but only at
	// process exit, which is acceptable.
	n = h->q_head;
	while (n) { struct acl_node* nx = n->next; free(n); n = nx; }
	n = h->done_head;
	while (n) { struct acl_node* nx = n->next; free(n); n = nx; }

	pthread_mutex_destroy(&h->mutex);
	pthread_cond_destroy(&h->cond);
	free(h);
}

#ifdef CHAR_ASYNC_LOAD_TEST
void acl_test_run_worker_once(ACharLane* h)
{
	struct acl_node* node;
	if (h == NULL) return;
	pthread_mutex_lock(&h->mutex);
	node = h->q_head;
	if (node) { h->q_head = node->next; if (h->q_head == NULL) h->q_tail = NULL; h->q_len--; }
	pthread_mutex_unlock(&h->mutex);
	if (node) { node->next = NULL; acl_process(h, node); }
}
unsigned acl_test_submitted(void) { return acl_submitted; }
#endif
