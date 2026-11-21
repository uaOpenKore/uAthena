// Online statistics (S. 2026-11-21), see onlinestat.h. One worker thread owns the spool file and the Mongo
// connection; the game thread only adds sums to a mutex-guarded list. Raw malloc/free (not aMalloc), like
// char_async_load, keeps the worker off the game loop's allocator. The worker never prints: its messages are
// passed to the game thread, which shows them (onlinestat_poll).
#include <errno.h>
#include <stdarg.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "../common/cbasetypes.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "../common/timer.h"
#include "onlinestat.h"
#include "onlinestat_rules.h"

#ifdef ONLINESTAT_MONGO
#include <mongoc/mongoc.h>
#endif

static char os_uri[512] = "";
static char os_dbname[64] = "uaro";
static char os_collname[64] = "online_daily";
static char os_spool[256] = "log/online_spool.jsonl";
static int os_interval = 600; // seconds between the worker's rounds
static int os_ttl_days = 365;

#define OS_BUCKETS 1024
#define OS_RETRY_SECS 30

struct os_node {
	struct os_line l;
	struct os_node* next;
};

static pthread_t os_tid;
static pthread_mutex_t os_mx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t os_cv = PTHREAD_COND_INITIALIZER;
static bool os_running = false, os_stop = false;
static struct os_node* os_pending[OS_BUCKETS]; // the game thread's sums since the worker's last round
static char os_msg[8][256]; // the worker's messages for the game thread
static int os_msgs = 0;

static int os_clamp(int v, int lo, int hi)
{
	return v < lo ? lo : v > hi ? hi : v;
}

static int onlinestat_config(const char* w1, const char* w2)
{
	if (strcmpi(w1, "onlinestat_mongo_uri") == 0)
		safestrncpy(os_uri, w2, sizeof(os_uri));
	else if (strcmpi(w1, "onlinestat_mongo_db") == 0)
		safestrncpy(os_dbname, w2, sizeof(os_dbname));
	else if (strcmpi(w1, "onlinestat_mongo_collection") == 0)
		safestrncpy(os_collname, w2, sizeof(os_collname));
	else if (strcmpi(w1, "onlinestat_spool") == 0)
		safestrncpy(os_spool, w2, sizeof(os_spool));
	else if (strcmpi(w1, "onlinestat_interval") == 0)
		os_interval = os_clamp(atoi(w2), 10, 3600);
	else if (strcmpi(w1, "onlinestat_ttl_days") == 0)
		os_ttl_days = os_clamp(atoi(w2), 1, 3650);
	else
		return 0;
	return 1;
}

// conf/mongo_athena.conf: the onlinestat_* keys; `import:` reads another file (conf/mongo_conf.txt, not in
// git, holds the URI with the password). A missing import file is not an error: the statistics are just off.
void onlinestat_read_conf(const char* path, int depth)
{
	char line[1024], w1[1024], w2[1024];
	FILE* fp = fopen(path, "r");
	if (fp == NULL) {
		if (depth == 0)
			ShowWarning("[ONLINESTAT] %s not found: online statistics are OFF.\n", path);
		return;
	}
	while (fgets(line, sizeof(line), fp)) {
		if (line[0] == '/' && line[1] == '/')
			continue;
		if (sscanf(line, "%1023[^:]: %1023[^\r\n]", w1, w2) != 2)
			continue;
		trim(w1);
		trim(w2);
		if (strcmpi(w1, "import") == 0) {
			if (depth < 4)
				onlinestat_read_conf(w2, depth + 1);
		} else if (!onlinestat_config(w1, w2))
			ShowWarning("[ONLINESTAT] %s: unknown key '%s'\n", path, w1);
	}
	fclose(fp);
}

static unsigned int os_hash(int date, int char_id)
{
	return ((unsigned int)char_id * 2654435761u ^ (unsigned int)date) % OS_BUCKETS;
}

// Adds l into the table (a new node or the sums of the same character and day).
static void os_merge(struct os_node** table, const struct os_line* l)
{
	unsigned int h = os_hash(l->date, l->char_id);
	struct os_node* n;
	for (n = table[h]; n; n = n->next)
		if (n->l.date == l->date && n->l.char_id == l->char_id)
			break;
	if (n == NULL) {
		if ((n = (struct os_node*)calloc(1, sizeof(*n))) == NULL)
			return;
		n->l.date = l->date;
		n->l.char_id = l->char_id;
		n->next = table[h];
		table[h] = n;
	}
	n->l.account_id = l->account_id;
	if (l->name[0])
		memcpy(n->l.name, l->name, sizeof(n->l.name));
	n->l.online += l->online;
	n->l.paid_buy += l->paid_buy;
	n->l.paid_auto += l->paid_auto;
}

static void os_free(struct os_node** table)
{
	int i;
	for (i = 0; i < OS_BUCKETS; i++) {
		while (table[i]) {
			struct os_node* n = table[i];
			table[i] = n->next;
			free(n);
		}
	}
}

void onlinestat_add(int date, int char_id, int account_id, const char* name, int online, int paid_buy, int paid_auto)
{
	struct os_line l;
	if (!os_running || char_id <= 0)
		return;
	memset(&l, 0, sizeof(l));
	l.date = date;
	l.char_id = char_id;
	l.account_id = account_id;
	os_name_utf8(name ? name : "", l.name, sizeof(l.name));
	l.online = online;
	l.paid_buy = paid_buy;
	l.paid_auto = paid_auto;
	pthread_mutex_lock(&os_mx);
	os_merge(os_pending, &l);
	pthread_mutex_unlock(&os_mx);
}

// worker -> game thread
static void os_say(const char* fmt, ...)
{
	va_list ap;
	pthread_mutex_lock(&os_mx);
	if (os_msgs < 8) {
		va_start(ap, fmt);
		vsnprintf(os_msg[os_msgs++], sizeof(os_msg[0]), fmt, ap);
		va_end(ap);
	}
	pthread_mutex_unlock(&os_mx);
}

static void onlinestat_poll(void)
{
	char msg[8][256];
	int i, n;
	pthread_mutex_lock(&os_mx);
	n = os_msgs;
	memcpy(msg, os_msg, sizeof(msg));
	os_msgs = 0;
	pthread_mutex_unlock(&os_mx);
	for (i = 0; i < n; i++)
		ShowInfo("[ONLINESTAT] %s\n", msg[i]);
}

// The worker's round, part 1: the sums taken from the game thread go to the end of the spool file.
static int os_append(struct os_node** table)
{
	char buf[1024];
	int i, lines = 0;
	FILE* f = fopen(os_spool, "a");
	if (f == NULL) {
		os_say("cannot write %s (%s): %s", os_spool, strerror(errno), "these minutes are lost");
		return -1;
	}
	for (i = 0; i < OS_BUCKETS; i++) {
		struct os_node* n;
		for (n = table[i]; n; n = n->next) {
			os_line_format(&n->l, buf, sizeof(buf));
			fputs(buf, f);
			lines++;
		}
	}
	fflush(f);
	fsync(fileno(f));
	fclose(f);
	return lines;
}

#ifdef ONLINESTAT_MONGO
static mongoc_client_t* os_client = NULL;
static bool os_indexes = false;

static bool os_create_indexes(mongoc_collection_t* coll, bson_error_t* err)
{
	bson_t* cmd = BCON_NEW("createIndexes", BCON_UTF8(os_collname), "indexes", "[",
		"{", "key", "{", "day", BCON_INT32(1), "}", "name", BCON_UTF8("ttl_day"),
			"expireAfterSeconds", BCON_INT64((int64_t)os_ttl_days * 86400), "}",
		"{", "key", "{", "char_id", BCON_INT32(1), "date", BCON_INT32(1), "}", "name", BCON_UTF8("char_date"), "}",
		"{", "key", "{", "account_id", BCON_INT32(1), "date", BCON_INT32(1), "}", "name", BCON_UTF8("account_date"), "}",
		"]");
	bool ok = mongoc_collection_write_command_with_opts(coll, cmd, NULL, NULL, err);
	bson_destroy(cmd);
	return ok;
}

// The worker's round, part 2: the whole file into Mongo; emptied once Mongo took it. -1 = not now.
static int os_push(int* docs)
{
	struct os_node** table;
	FILE* f;
	char* line = NULL;
	size_t cap = 0;
	int i, n = 0;
	bool ok = true;
	bson_error_t err;
	mongoc_collection_t* coll;
	mongoc_bulk_operation_t* bulk;
	bson_t* bopts;
	struct stat st;

	*docs = 0;
	if (stat(os_spool, &st) != 0 || st.st_size == 0)
		return 0;
	if ((f = fopen(os_spool, "r")) == NULL)
		return -1;
	table = (struct os_node**)calloc(OS_BUCKETS, sizeof(*table));
	if (table == NULL) {
		fclose(f);
		return -1;
	}
	while (getline(&line, &cap, f) > 0) {
		struct os_line l;
		if (os_line_parse(line, &l))
			os_merge(table, &l);
	}
	free(line);
	fclose(f);

	if (os_client == NULL) {
		mongoc_uri_t* uri = mongoc_uri_new_with_error(os_uri, &err);
		if (uri == NULL) {
			os_say("onlinestat_mongo_uri is not a MongoDB URI: %s", err.message);
			os_free(table);
			free(table);
			return -1;
		}
		mongoc_uri_set_option_as_int32(uri, MONGOC_URI_SERVERSELECTIONTIMEOUTMS, 5000);
		mongoc_uri_set_option_as_int32(uri, MONGOC_URI_CONNECTTIMEOUTMS, 5000);
		os_client = mongoc_client_new_from_uri(uri);
		mongoc_uri_destroy(uri);
		if (os_client == NULL) {
			os_free(table);
			free(table);
			return -1;
		}
		mongoc_client_set_appname(os_client, "uathena-char-server");
		os_indexes = false;
	}
	coll = mongoc_client_get_collection(os_client, os_dbname, os_collname);
	if (!os_indexes && !(os_indexes = os_create_indexes(coll, &err)))
		ok = false;
	if (ok) {
		bopts = BCON_NEW("ordered", BCON_BOOL(false));
		bulk = mongoc_collection_create_bulk_operation_with_opts(coll, bopts);
		bson_destroy(bopts);
		for (i = 0; i < OS_BUCKETS && ok; i++) {
			struct os_node* nd;
			for (nd = table[i]; nd && ok; nd = nd->next) {
				char id[32], date[16];
				bson_t* sel;
				bson_t* upd;
				bson_t* uopts;
				snprintf(id, sizeof(id), "%d:%d", nd->l.date, nd->l.char_id);
				os_date_text(nd->l.date, date, sizeof(date));
				sel = BCON_NEW("_id", BCON_UTF8(id));
				upd = BCON_NEW(
					"$inc", "{", "online", BCON_INT32(nd->l.online), "paid_buy", BCON_INT32(nd->l.paid_buy),
						"paid_auto", BCON_INT32(nd->l.paid_auto), "}",
					"$setOnInsert", "{", "date", BCON_UTF8(date), "day", BCON_DATE_TIME(os_date_ms(nd->l.date)),
						"char_id", BCON_INT32(nd->l.char_id), "}");
				{	// $set: an unknown name (not cached) does not blank the one already there
					bson_t set;
					BSON_APPEND_DOCUMENT_BEGIN(upd, "$set", &set);
					BSON_APPEND_INT32(&set, "account_id", nd->l.account_id);
					if (nd->l.name[0])
						BSON_APPEND_UTF8(&set, "name", nd->l.name);
					BSON_APPEND_DATE_TIME(&set, "updated", (int64_t)time(NULL) * 1000);
					bson_append_document_end(upd, &set);
				}
				uopts = BCON_NEW("upsert", BCON_BOOL(true));
				ok = mongoc_bulk_operation_update_one_with_opts(bulk, sel, upd, uopts, &err);
				bson_destroy(sel);
				bson_destroy(upd);
				bson_destroy(uopts);
				n++;
			}
		}
		if (ok && n > 0) {
			bson_t reply;
			ok = mongoc_bulk_operation_execute(bulk, &reply, &err) != 0;
			bson_destroy(&reply);
		}
		mongoc_bulk_operation_destroy(bulk);
	}
	mongoc_collection_destroy(coll);
	os_free(table);
	free(table);
	if (!ok) {
		mongoc_client_destroy(os_client); // a new connection next time
		os_client = NULL;
		os_say("MongoDB not reached (%s): the minutes wait in %s (%ld bytes), next try in %d s",
			err.message, os_spool, (long)st.st_size, OS_RETRY_SECS);
		return -1;
	}
	// Mongo has them: the file starts over (only this thread writes it, so nothing came in meanwhile)
	if (truncate(os_spool, 0) != 0)
		os_say("cannot empty %s (%s): its minutes would be counted again", os_spool, strerror(errno));
	*docs = n;
	return n;
}
#endif

static void* os_worker(void* arg)
{
	struct os_node* table[OS_BUCKETS];
	bool failing = false, stop = false;
#ifdef ONLINESTAT_MONGO
	int docs;
#endif
	(void)arg;
#ifdef ONLINESTAT_MONGO
	mongoc_init();
	if (os_push(&docs) > 0) // what an earlier run left in the file
		os_say("%d record(s) left in %s from before went to MongoDB", docs, os_spool);
#endif
	while (!stop) {
		struct timespec ts;
		clock_gettime(CLOCK_REALTIME, &ts);
		ts.tv_sec += failing ? OS_RETRY_SECS : os_interval;
		pthread_mutex_lock(&os_mx);
		while (!os_stop && pthread_cond_timedwait(&os_cv, &os_mx, &ts) != ETIMEDOUT)
			;
		stop = os_stop;
		memcpy(table, os_pending, sizeof(table));
		memset(os_pending, 0, sizeof(os_pending));
		pthread_mutex_unlock(&os_mx);
		os_append(table);
		os_free(table);
#ifdef ONLINESTAT_MONGO
		{
			int r = os_push(&docs);
			if (r >= 0 && failing)
				os_say("MongoDB is back: %d record(s) from the file went in", docs);
			failing = r < 0;
		}
#endif
	}
#ifdef ONLINESTAT_MONGO
	if (os_client)
		mongoc_client_destroy(os_client);
	os_client = NULL;
	mongoc_cleanup();
#endif
	return NULL;
}

static int onlinestat_poll_timer(int tid, t_tick tick, intptr_t id, intptr_t data)
{
	onlinestat_poll();
	return 0;
}

void onlinestat_init(void)
{
	if (os_uri[0] == '\0') {
		ShowStatus("[ONLINESTAT] online statistics are OFF (no onlinestat_mongo_uri).\n");
		return;
	}
#ifndef ONLINESTAT_MONGO
	ShowWarning("[ONLINESTAT] this char-server was built without libmongoc: the minutes are kept in %s, "
		"nothing goes to MongoDB (install libmongoc-dev and rebuild).\n", os_spool);
#endif
	os_running = true;
	if (pthread_create(&os_tid, NULL, os_worker, NULL) != 0) {
		os_running = false;
		ShowError("[ONLINESTAT] cannot start the worker thread: online statistics are OFF.\n");
		return;
	}
	add_timer_func_list(onlinestat_poll_timer, "onlinestat_poll_timer");
	add_timer_interval(gettick() + 5000, onlinestat_poll_timer, 0, 0, 5000);
	ShowStatus("[ONLINESTAT] online statistics to %s, MongoDB %s.%s every %d s (kept %d days).\n",
		os_spool, os_dbname, os_collname, os_interval, os_ttl_days);
}

void onlinestat_final(void)
{
	if (!os_running)
		return;
	pthread_mutex_lock(&os_mx);
	os_stop = true;
	pthread_cond_signal(&os_cv);
	pthread_mutex_unlock(&os_mx);
	pthread_join(os_tid, NULL);
	os_running = false;
	onlinestat_poll();
	ShowStatus("[ONLINESTAT] stopped.\n");
}
