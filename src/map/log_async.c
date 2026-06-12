// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Asynchronous SQL log writer.
//
// The map server's log_* functions used to call mysql_query() directly,
// stalling the whole game loop for a DB round-trip on every logged item
// pick, chat line or GM command. Instead they now enqueue the statement
// here, and a dedicated worker thread (with its OWN MySQL connection -
// handles must never be shared between threads) flushes the queue every
// LOG_ASYNC_FLUSH_SEC seconds, or earlier if the queue grows large.
//
// On shutdown (do_final -> log_async_final) the queue is drained before
// the thread is joined, so a SIGTERM stop loses nothing. A SIGKILL can
// lose up to the flush interval of log entries - logs only, never game
// state, which is persisted through the char-server.
//
// While the DB is unreachable the worker keeps the batch queued and
// retries on the next cycle; enqueueing beyond LOG_ASYNC_MAX_QUEUE drops
// new entries (reported once per flush). If the worker thread could not
// be started at all, log_async_query falls back to the old synchronous
// path on logmysql_handle.
//
// NOTE: the queue deliberately uses raw malloc/free, NOT aMalloc/aFree -
// the custom memory manager in common/malloc.c is not thread-safe.

#include "../common/showmsg.h"
#include "map.h"
#include "log.h"

#include <mysql.h>
#include <errmsg.h>
#include <pthread.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define LOG_ASYNC_FLUSH_SEC   15     // periodic flush interval
#define LOG_ASYNC_WAKE_LEN    4096   // flush early when this many entries pile up
#define LOG_ASYNC_MAX_QUEUE   65536  // hard cap: drop new entries beyond this

struct log_async_node {
	struct log_async_node* next;
	char sql[1]; // statement text, allocated to fit
};

static struct log_async_node* q_head = NULL;
static struct log_async_node* q_tail = NULL;
static unsigned int q_len = 0;
static unsigned int q_dropped = 0;
static int q_flush_request = 0;
static int q_shutdown = 0;

static pthread_mutex_t q_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t q_cond = PTHREAD_COND_INITIALIZER;
static pthread_t worker_tid;
static int worker_running = 0;

// connection settings owned by map.c (read-only once the server is up)
extern char log_db_ip[32];
extern int log_db_port;
extern char log_db_id[32];
extern char log_db_pw[32];
extern char log_db[32];
extern char default_codepage[32];

/*==========================================
 * Worker-side connection management
 *------------------------------------------*/
static int log_async_connect(MYSQL* handle)
{
	mysql_init(handle);
	if (!mysql_real_connect(handle, log_db_ip, log_db_id, log_db_pw, log_db, log_db_port, NULL, 0)) {
		ShowSQL("log_async: connect to %s:%d failed - %s\n", log_db_ip, log_db_port, mysql_error(handle));
		mysql_close(handle);
		return 0;
	}
	if (default_codepage[0] != '\0') {
		char buf[64];
		snprintf(buf, sizeof(buf), "SET NAMES %s", default_codepage);
		if (mysql_query(handle, buf))
			ShowSQL("log_async: %s failed - %s\n", buf, mysql_error(handle));
	}
	return 1;
}

// Execute one detached batch. Returns 1 on success, 0 if the connection is
// down (caller should requeue the remaining nodes starting at *remain).
static int log_async_run_batch(MYSQL* handle, struct log_async_node* batch, struct log_async_node** remain)
{
	while (batch) {
		struct log_async_node* next = batch->next;
		if (mysql_query(handle, batch->sql)) {
			unsigned int err = mysql_errno(handle);
			if (err == CR_SERVER_GONE_ERROR || err == CR_SERVER_LOST) {
				*remain = batch; // connection died: keep this and the rest for retry
				return 0;
			}
			// statement-level error (bad data etc.): report and move on.
			// %.1800s keeps the message inside showmsg's 2048-byte stack
			// buffer - the aMalloc fallback is not thread-safe.
			ShowSQL("log_async: DB error - %s\n", mysql_error(handle));
			ShowDebug("log_async: failed statement: %.1800s\n", batch->sql);
		}
		free(batch);
		batch = next;
	}
	*remain = NULL;
	return 1;
}

// put a batch (that could not be executed) back at the head of the queue,
// preserving order
static void log_async_requeue(struct log_async_node* batch)
{
	struct log_async_node* tail = batch;
	unsigned int n = 1;
	if (batch == NULL)
		return;
	while (tail->next) {
		tail = tail->next;
		n++;
	}
	pthread_mutex_lock(&q_mutex);
	tail->next = q_head;
	q_head = batch;
	if (q_tail == NULL)
		q_tail = tail;
	q_len += n;
	pthread_mutex_unlock(&q_mutex);
}

static void* log_async_worker(void* arg)
{
	MYSQL handle;
	int connected;

	mysql_thread_init();
	connected = log_async_connect(&handle);

	for (;;) {
		struct log_async_node* batch;
		struct log_async_node* remain;
		unsigned int dropped;
		int quit;
		struct timespec deadline;

		clock_gettime(CLOCK_REALTIME, &deadline);
		deadline.tv_sec += LOG_ASYNC_FLUSH_SEC;

		pthread_mutex_lock(&q_mutex);
		while (!q_shutdown && !q_flush_request) {
			if (pthread_cond_timedwait(&q_cond, &q_mutex, &deadline) == ETIMEDOUT)
				break;
		}
		q_flush_request = 0;
		quit = q_shutdown;
		batch = q_head;
		q_head = q_tail = NULL;
		q_len = 0;
		dropped = q_dropped;
		q_dropped = 0;
		pthread_mutex_unlock(&q_mutex);

		if (dropped)
			ShowWarning("log_async: queue overflow, %u log entries dropped.\n", dropped);

		if (batch) {
			if (!connected)
				connected = log_async_connect(&handle);
			else if (mysql_ping(&handle)) {
				mysql_close(&handle);
				connected = log_async_connect(&handle);
			}
			if (connected) {
				if (!log_async_run_batch(&handle, batch, &remain)) {
					mysql_close(&handle);
					connected = 0;
					batch = remain;
				} else
					batch = NULL;
			}
			if (batch) { // DB unreachable: keep for the next cycle (unless quitting)
				if (quit) {
					unsigned int lost = 0;
					while (batch) {
						struct log_async_node* next = batch->next;
						free(batch);
						batch = next;
						lost++;
					}
					ShowWarning("log_async: DB unreachable on shutdown, %u log entries lost.\n", lost);
				} else
					log_async_requeue(batch);
			}
		}

		if (quit)
			break;
	}

	if (connected)
		mysql_close(&handle);
	mysql_thread_end();
	return NULL;
}

/*==========================================
 * Main-thread API
 *------------------------------------------*/

// Enqueue one statement for the worker; falls back to a synchronous query
// on logmysql_handle if the worker is not running.
int log_async_query(const char* sql)
{
	struct log_async_node* node;
	size_t len;

	if (!worker_running) {
		if (mysql_query(&logmysql_handle, sql)) {
			ShowSQL("DB error - %s\n", mysql_error(&logmysql_handle));
			ShowDebug("at %s:%d - %s\n", __FILE__, __LINE__, sql);
			return 0;
		}
		return 1;
	}

	len = strlen(sql);
	node = (struct log_async_node*)malloc(sizeof(struct log_async_node) + len);
	if (node == NULL)
		return 0;
	memcpy(node->sql, sql, len + 1);
	node->next = NULL;

	pthread_mutex_lock(&q_mutex);
	if (q_len >= LOG_ASYNC_MAX_QUEUE) {
		q_dropped++;
		pthread_mutex_unlock(&q_mutex);
		free(node);
		return 0;
	}
	if (q_tail)
		q_tail->next = node;
	else
		q_head = node;
	q_tail = node;
	if (++q_len == LOG_ASYNC_WAKE_LEN) {
		q_flush_request = 1;
		pthread_cond_signal(&q_cond);
	}
	pthread_mutex_unlock(&q_mutex);
	return 1;
}

int log_async_init(void)
{
	int ret;
	if (worker_running)
		return 1;
	ret = pthread_create(&worker_tid, NULL, log_async_worker, NULL);
	if (ret != 0) {
		ShowWarning("log_async: pthread_create failed (%d), falling back to synchronous SQL logs.\n", ret);
		return 0;
	}
	worker_running = 1;
	ShowStatus("Asynchronous SQL log writer started (flush every %d seconds).\n", LOG_ASYNC_FLUSH_SEC);
	return 1;
}

void log_async_final(void)
{
	if (!worker_running)
		return;
	pthread_mutex_lock(&q_mutex);
	q_shutdown = 1;
	pthread_cond_signal(&q_cond);
	pthread_mutex_unlock(&q_mutex);
	pthread_join(worker_tid, NULL);
	worker_running = 0; // later log calls fall back to the sync path
	ShowStatus("Asynchronous SQL log writer stopped, queue flushed.\n");
}
