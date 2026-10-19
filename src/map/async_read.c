// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// Generic asynchronous SQL read engine. See async_read.h for the contract.
//
// Modelled on async_db.c (the write engine): a mutex/cond-guarded request queue
// drained by a dedicated worker thread that owns its own MySQL connection. The
// difference is the RESULT path: the worker copies each result set into a
// self-contained snapshot and parks it on a completion queue; the game thread
// drains that queue in async_read_poll() and runs the callbacks itself, so all
// game-state mutation stays on the game thread. Raw malloc/free keeps the worker
// off the game loop's allocator lock, exactly like async_db.c.

#include <pthread.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "async_read.h"

#define ASYNC_READ_MAX_QUEUE 65536 // hard cap on requests in flight: drop beyond this

#ifndef ASYNC_READ_TEST
#include "../common/showmsg.h"
#include <mysql.h>
#include <errmsg.h>
#endif

struct async_read_node {
	struct async_read_node* next;
	async_read_cb cb;
	void* ctx;
	AsyncReadResult res; // filled by the worker, consumed by poll()
	char sql[1];         // statement text, allocated to fit
};

struct AsyncRead {
	char name[32];
	char ip[32], user[32], pw[32], db[32], codepage[32];
	int  port;

	// request queue (game thread -> worker)
	struct async_read_node* q_head;
	struct async_read_node* q_tail;
	unsigned int q_len;
	unsigned int q_dropped;
	// completion queue (worker -> game thread)
	struct async_read_node* done_head;
	struct async_read_node* done_tail;
	unsigned int inflight; // submitted but not yet dispatched by poll()

	int q_shutdown;

	pthread_mutex_t mutex;
	pthread_cond_t  cond;
	pthread_t       tid;
	int             running;
	int             connected;

#ifndef ASYNC_READ_TEST
	MYSQL mysql;
#endif
};

/*==========================================
 * DB seam - real MySQL vs. canned test rows
 *------------------------------------------*/
#ifndef ASYNC_READ_TEST

static void arr_thread_setup(void)    { mysql_thread_init(); }
static void arr_thread_teardown(void) { mysql_thread_end(); }

static int arr_connect(AsyncRead* h)
{
	mysql_init(&h->mysql);
	if (!mysql_real_connect(&h->mysql, h->ip, h->user, h->pw, h->db, h->port, NULL, 0)) {
		ShowSQL("async_read[%s]: connect to %s:%d failed - %s\n", h->name, h->ip, h->port, mysql_error(&h->mysql));
		mysql_close(&h->mysql);
		return 0;
	}
	if (h->codepage[0] != '\0') {
		char buf[64];
		snprintf(buf, sizeof(buf), "SET NAMES %s", h->codepage);
		if (mysql_query(&h->mysql, buf))
			ShowSQL("async_read[%s]: %s failed - %s\n", h->name, buf, mysql_error(&h->mysql));
	}
	return 1;
}

static int arr_ping(AsyncRead* h)  { return mysql_ping(&h->mysql); } // 0 = alive
static void arr_close(AsyncRead* h){ mysql_close(&h->mysql); }

// Run one SELECT and build a snapshot into *out.
// Returns: 0 = success, 1 = statement error (deliver err), 2 = connection lost (retry).
static int arr_exec(AsyncRead* h, const char* sql, AsyncReadResult* out)
{
	MYSQL_RES* r;
	MYSQL_ROW row;
	int nrows, nfields, i;

	out->err = 1; out->nrows = 0; out->nfields = 0; out->cell = NULL;

	if (mysql_query(&h->mysql, sql)) {
		unsigned int err = mysql_errno(&h->mysql);
		if (err == CR_SERVER_GONE_ERROR || err == CR_SERVER_LOST)
			return 2;
		ShowSQL("async_read[%s]: DB error - %s\n", h->name, mysql_error(&h->mysql));
		ShowDebug("async_read[%s]: failed statement: %.1800s\n", h->name, sql);
		return 1;
	}

	r = mysql_store_result(&h->mysql);
	if (r == NULL) {
		// A SELECT with no result set, or store error. Treat empty/ok.
		if (mysql_errno(&h->mysql)) {
			ShowSQL("async_read[%s]: store_result error - %s\n", h->name, mysql_error(&h->mysql));
			return 1;
		}
		out->err = 0; // query ran, no rows
		return 0;
	}

	nrows   = (int)mysql_num_rows(r);
	nfields = (int)mysql_num_fields(r);
	out->nrows = nrows;
	out->nfields = nfields;
	if (nrows > 0 && nfields > 0) {
		out->cell = (char**)calloc((size_t)nrows * nfields, sizeof(char*));
		if (out->cell == NULL) { // OOM: deliver as error, free live result
			mysql_free_result(r);
			out->nrows = 0; out->nfields = 0; out->err = 1;
			return 1;
		}
		i = 0;
		while ((row = mysql_fetch_row(r)) != NULL) {
			int c;
			for (c = 0; c < nfields; c++) {
				if (row[c] != NULL) {
					size_t len = strlen(row[c]);
					char* s = (char*)malloc(len + 1);
					if (s) { memcpy(s, row[c], len + 1); }
					out->cell[i * nfields + c] = s; // s==NULL on OOM is acceptable (reads as SQL NULL)
				}
			}
			if (++i >= nrows) break;
		}
	}
	mysql_free_result(r);
	out->err = 0;
	return 0;
}

#else /* ASYNC_READ_TEST: no real MySQL, return canned rows */

#define ShowSQL(...)     ((void)0)
#define ShowDebug(...)   ((void)0)
#define ShowWarning(...) ((void)0)
#define ShowStatus(...)  ((void)0)

static int   art_rows = 0, art_fields = 0;
static char* art_cells_src[4096];
static int   art_fail_servergone = 0;
static unsigned art_submitted = 0;

void async_read_test_reset(void)
{
	int i;
	for (i = 0; i < art_rows * art_fields; i++) { free(art_cells_src[i]); art_cells_src[i] = NULL; }
	art_rows = art_fields = 0; art_fail_servergone = 0; art_submitted = 0;
}
void async_read_test_set_rows(int nrows, int nfields, const char* const* cells)
{
	int i;
	async_read_test_reset();
	art_rows = nrows; art_fields = nfields;
	for (i = 0; i < nrows * nfields; i++) {
		if (cells[i]) { art_cells_src[i] = (char*)malloc(strlen(cells[i]) + 1); if (art_cells_src[i]) strcpy(art_cells_src[i], cells[i]); }
	}
}
void     async_read_test_fail_servergone(int n) { art_fail_servergone = n; }
unsigned async_read_test_submitted(void)        { return art_submitted; }

static void arr_thread_setup(void)    { }
static void arr_thread_teardown(void) { }
static int  arr_connect(AsyncRead* h) { (void)h; return 1; }
static int  arr_ping(AsyncRead* h)    { (void)h; return 0; }
static void arr_close(AsyncRead* h)   { (void)h; }

static int arr_exec(AsyncRead* h, const char* sql, AsyncReadResult* out)
{
	int i;
	(void)h; (void)sql;
	out->err = 1; out->nrows = 0; out->nfields = 0; out->cell = NULL;
	if (art_fail_servergone > 0) { art_fail_servergone--; return 2; }
	out->nrows = art_rows; out->nfields = art_fields;
	if (art_rows > 0 && art_fields > 0) {
		out->cell = (char**)calloc((size_t)art_rows * art_fields, sizeof(char*));
		if (!out->cell) { out->nrows = out->nfields = 0; return 1; }
		for (i = 0; i < art_rows * art_fields; i++) {
			if (art_cells_src[i]) { out->cell[i] = (char*)malloc(strlen(art_cells_src[i]) + 1); if (out->cell[i]) strcpy(out->cell[i], art_cells_src[i]); }
		}
	}
	out->err = 0;
	return 0;
}
#endif

/*==========================================
 * Snapshot / node lifecycle
 *------------------------------------------*/
static void arr_free_result(AsyncReadResult* res)
{
	if (res->cell) {
		int n = res->nrows * res->nfields, i;
		for (i = 0; i < n; i++) free(res->cell[i]);
		free(res->cell);
		res->cell = NULL;
	}
	res->nrows = res->nfields = 0;
}

static void arr_free_node(struct async_read_node* n)
{
	if (n == NULL) return;
	arr_free_result(&n->res);
	free(n);
}

/*==========================================
 * Worker
 *------------------------------------------*/
// Run the query for one node, then move it to the completion queue.
static void arr_process(AsyncRead* h, struct async_read_node* node)
{
	int rc;

	if (!h->connected)
		h->connected = arr_connect(h);
	else if (arr_ping(h)) {
		arr_close(h);
		h->connected = arr_connect(h);
	}

	if (h->connected) {
		rc = arr_exec(h, node->sql, &node->res);
		if (rc == 2) { // connection lost: reconnect and retry once
			arr_close(h);
			h->connected = arr_connect(h);
			if (h->connected)
				rc = arr_exec(h, node->sql, &node->res);
			else
				rc = 2;
		}
		if (rc != 0) { node->res.err = 1; node->res.nrows = node->res.nfields = 0; }
	} else {
		node->res.err = 1; node->res.nrows = node->res.nfields = 0;
	}

	pthread_mutex_lock(&h->mutex);
	node->next = NULL;
	if (h->done_tail) h->done_tail->next = node;
	else              h->done_head = node;
	h->done_tail = node;
	pthread_mutex_unlock(&h->mutex);
}

static void* arr_worker(void* arg)
{
	AsyncRead* h = (AsyncRead*)arg;
	arr_thread_setup();
	h->connected = arr_connect(h);

	for (;;) {
		struct async_read_node* node;

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
		arr_process(h, node);
	}

	if (h->connected) arr_close(h);
	arr_thread_teardown();
	return NULL;
}

/*==========================================
 * Public API
 *------------------------------------------*/
static void arr_copy(char* dst, const char* src, size_t n)
{
	if (src == NULL) { dst[0] = '\0'; return; }
	strncpy(dst, src, n - 1);
	dst[n - 1] = '\0';
}

AsyncRead* async_read_create(const char* name, const char* ip, const char* user,
                             const char* pw, const char* db, int port,
                             const char* codepage)
{
	AsyncRead* h = (AsyncRead*)calloc(1, sizeof(AsyncRead));
	if (h == NULL) return NULL;

	arr_copy(h->name, name ? name : "async_read", sizeof(h->name));
	arr_copy(h->ip, ip, sizeof(h->ip));
	arr_copy(h->user, user, sizeof(h->user));
	arr_copy(h->pw, pw, sizeof(h->pw));
	arr_copy(h->db, db, sizeof(h->db));
	arr_copy(h->codepage, codepage, sizeof(h->codepage));
	h->port = port;

	pthread_mutex_init(&h->mutex, NULL);
	pthread_cond_init(&h->cond, NULL);

#ifndef ASYNC_READ_TEST
	if (pthread_create(&h->tid, NULL, arr_worker, h) != 0) {
		ShowWarning("async_read[%s]: pthread_create failed - reads unavailable.\n", h->name);
		pthread_mutex_destroy(&h->mutex);
		pthread_cond_destroy(&h->cond);
		free(h);
		return NULL;
	}
	h->running = 1;
	ShowStatus("async_read[%s]: reader started.\n", h->name);
#endif
	return h;
}

int async_read_submit(AsyncRead* h, const char* sql, async_read_cb cb, void* ctx)
{
	struct async_read_node* node;
	size_t len;

	if (h == NULL || cb == NULL || sql == NULL)
		return 0;

	len = strlen(sql);
	node = (struct async_read_node*)malloc(sizeof(struct async_read_node) + len);
	if (node == NULL)
		return 0;
	memcpy(node->sql, sql, len + 1);
	node->next = NULL;
	node->cb = cb;
	node->ctx = ctx;
	node->res.err = 0; node->res.nrows = 0; node->res.nfields = 0; node->res.cell = NULL;

	pthread_mutex_lock(&h->mutex);
	if (h->q_len >= ASYNC_READ_MAX_QUEUE) {
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
#ifdef ASYNC_READ_TEST
	art_submitted++;
#endif
	pthread_cond_signal(&h->cond);
	pthread_mutex_unlock(&h->mutex);
	return 1;
}

int async_read_poll(AsyncRead* h)
{
	struct async_read_node* done;
	int dispatched = 0;

	if (h == NULL)
		return 0;

	pthread_mutex_lock(&h->mutex);
	done = h->done_head;
	h->done_head = h->done_tail = NULL;
	pthread_mutex_unlock(&h->mutex);

	while (done) {
		struct async_read_node* next = done->next;
		done->cb(done->ctx, &done->res); // game thread: safe to touch game state
		arr_free_node(done);
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

unsigned int async_read_pending(AsyncRead* h)
{
	unsigned int n;
	if (h == NULL) return 0;
	pthread_mutex_lock(&h->mutex);
	n = h->inflight;
	pthread_mutex_unlock(&h->mutex);
	return n;
}

void async_read_destroy(AsyncRead* h)
{
	struct async_read_node* n;
	if (h == NULL) return;

	if (h->running) {
		pthread_mutex_lock(&h->mutex);
		h->q_shutdown = 1;
		pthread_cond_signal(&h->cond);
		pthread_mutex_unlock(&h->mutex);
		pthread_join(h->tid, NULL);
		h->running = 0;
	} else if (h->connected) {
		arr_close(h);
	}

	// Discard anything left in either queue (callbacks are not invoked on shutdown).
	n = h->q_head;
	while (n) { struct async_read_node* nx = n->next; arr_free_node(n); n = nx; }
	n = h->done_head;
	while (n) { struct async_read_node* nx = n->next; arr_free_node(n); n = nx; }

	pthread_mutex_destroy(&h->mutex);
	pthread_cond_destroy(&h->cond);
	free(h);
}

#ifdef ASYNC_READ_TEST
void async_read__run_worker_once(AsyncRead* h)
{
	struct async_read_node* node;
	if (h == NULL) return;
	pthread_mutex_lock(&h->mutex);
	node = h->q_head;
	if (node) { h->q_head = node->next; if (h->q_head == NULL) h->q_tail = NULL; h->q_len--; }
	pthread_mutex_unlock(&h->mutex);
	if (node) { node->next = NULL; arr_process(h, node); }
}
#endif
