// Copyright (c) uAthena / bornrok.com
// Discord webhook relay (background thread). Mirrors rare-drop global announces (the same
// messages as battle_config.rare_drop_announce, i.e. drops with chance <= 0.01%) to a Discord
// channel through an incoming webhook, off the single game loop. The webhook URL is read from
// conf/discord.conf so it never lives in source. Delivery is best-effort: a message is dropped
// if the bounded queue is full or curl is unavailable, and nothing ever blocks the caller.
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "discord.h"
#include "../common/showmsg.h"

#define DISCORD_QUEUE_MAX 256
#define DISCORD_MSG_MAX   256
#define DISCORD_URL_MAX   512
#define DISCORD_NAME_MAX  64

// Error-mirroring throttle: collapse the common flood where one fault (e.g. a dropped SQL
// connection) fires the SAME message hundreds of times/sec, without losing distinct errors.
#define DISCORD_ERR_DEDUP  120   // suppress an IDENTICAL error seen again within this many sec
#define DISCORD_ERR_MINGAP 3     // min seconds between ANY two error posts (burst guard)

static char g_webhook[DISCORD_URL_MAX];
static char g_username[DISCORD_NAME_MAX] = "uAthena";
static int  g_enabled = 0;   // config master switch + valid webhook
static int  g_errors_enabled = 0;  // also mirror critical server errors (discord_errors)
static int  g_running = 0;   // worker thread is up
static int  g_shutdown = 0;  // asked to stop

// error-throttle state (guarded by g_mtx)
static char   g_last_err[DISCORD_MSG_MAX];
static time_t g_last_err_time = 0;   // when g_last_err was last posted
static time_t g_last_any_err_time = 0;  // when ANY error was last posted

// Single-producer (game loop) / single-consumer (worker) ring buffer.
static char g_queue[DISCORD_QUEUE_MAX][DISCORD_MSG_MAX];
static int  g_head = 0, g_tail = 0, g_count = 0;

static pthread_t       g_thread;
static pthread_mutex_t g_mtx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  g_cv  = PTHREAD_COND_INITIALIZER;

// Append src to dst as a JSON string body, escaping what a JSON string must escape. Stops
// before overflowing cap (reserving room for the longest single escape + NUL). Returns new len.
static size_t json_escape_append(char* dst, size_t dstlen, size_t cap, const char* src)
{
	size_t o = dstlen;
	const unsigned char* p = (const unsigned char*)src;
	for( ; *p && o + 7 < cap; ++p ) {
		unsigned char c = *p;
		switch( c ) {
			case '\"': dst[o++] = '\\'; dst[o++] = '\"'; break;
			case '\\': dst[o++] = '\\'; dst[o++] = '\\'; break;
			case '\n': dst[o++] = '\\'; dst[o++] = 'n';  break;
			case '\r': dst[o++] = '\\'; dst[o++] = 'r';  break;
			case '\t': dst[o++] = '\\'; dst[o++] = 't';  break;
			default:
				if( c < 0x20 )
					o += sprintf(dst + o, "\\u%04x", c);  // other control chars
				else
					dst[o++] = (char)c;
		}
	}
	dst[o] = '\0';
	return o;
}

// POST one message to the webhook via curl. Blocking, so it only runs on the worker thread.
static void discord_post(const char* text)
{
	char cmd[DISCORD_URL_MAX + 160];
	// Worst case: both strings fully \uXXXX-escaped (x6) plus the fixed JSON scaffolding. Sized
	// well above that so json_escape_append never hits its cap guard and the closing "\"}" fits.
	char body[DISCORD_MSG_MAX * 6 + DISCORD_NAME_MAX * 6 + 64];
	size_t n = 0;
	FILE* fp;

	// Build {"username":"<name>","content":"<text>"} with both values JSON-escaped.
	n += sprintf(body + n, "{\"username\":\"");
	n  = json_escape_append(body, n, sizeof(body), g_username);
	n += sprintf(body + n, "\",\"content\":\"");
	n  = json_escape_append(body, n, sizeof(body), text);
	n += sprintf(body + n, "\"}");

	// The webhook URL comes from our own config and is validated (https, no single quote) at
	// init, so single-quoting it here is safe. The message body travels on stdin
	// (--data-binary @-), never the command line, so its contents can't break the shell.
	snprintf(cmd, sizeof(cmd),
		"curl -s -o /dev/null --max-time 10 "
		"-H \"Content-Type: application/json\" "
		"-X POST --data-binary @- '%s'", g_webhook);

	fp = popen(cmd, "w");
	if( fp == NULL )
		return;
	fwrite(body, 1, strlen(body), fp);
	pclose(fp);
}

static void* discord_worker(void* arg)
{
	(void)arg;
	for( ;; ) {
		char msg[DISCORD_MSG_MAX];
		pthread_mutex_lock(&g_mtx);
		while( g_count == 0 && !g_shutdown )
			pthread_cond_wait(&g_cv, &g_mtx);
		if( g_count == 0 && g_shutdown ) {
			pthread_mutex_unlock(&g_mtx);
			break;
		}
		memcpy(msg, g_queue[g_head], DISCORD_MSG_MAX);
		g_head = (g_head + 1) % DISCORD_QUEUE_MAX;
		--g_count;
		pthread_mutex_unlock(&g_mtx);

		discord_post(msg);
	}
	return NULL;
}

void discord_announce(const char* text)
{
	if( !g_enabled || !g_running || text == NULL )
		return;
	pthread_mutex_lock(&g_mtx);
	if( g_count < DISCORD_QUEUE_MAX ) {
		strncpy(g_queue[g_tail], text, DISCORD_MSG_MAX - 1);
		g_queue[g_tail][DISCORD_MSG_MAX - 1] = '\0';
		g_tail = (g_tail + 1) % DISCORD_QUEUE_MAX;
		++g_count;
		pthread_cond_signal(&g_cv);
	}  // queue full -> drop this announce (best-effort)
	pthread_mutex_unlock(&g_mtx);
}

// Copy src to dst, dropping ANSI colour escapes (\033[...m) and folding any newlines/tabs to
// single spaces, so a console error line renders cleanly in Discord. Always NUL-terminates.
static void strip_ansi(const char* src, char* dst, size_t cap)
{
	size_t o = 0;
	const unsigned char* p = (const unsigned char*)src;
	for( ; *p && o + 1 < cap; ++p ) {
		if( *p == 0x1b ) {           // ESC: skip "\033[ ... <final letter>"
			if( p[1] == '[' ) {
				p += 2;
				while( *p && !(*p >= '@' && *p <= '~') ) ++p;
				if( !*p ) break;     // ran off the end mid-sequence
			}
			continue;                // drop ESC (and the consumed sequence)
		}
		if( *p == '\n' || *p == '\r' || *p == '\t' )
			dst[o++] = ' ';
		else
			dst[o++] = (char)*p;
	}
	// trim trailing spaces
	while( o && dst[o-1] == ' ' ) --o;
	dst[o] = '\0';
}

// Mirror one critical server error to Discord (registered as showmsg's error hook when
// discord_errors is on). Throttled: identical errors are suppressed for DISCORD_ERR_DEDUP sec,
// and no more than one error is posted per DISCORD_ERR_MINGAP sec. Non-blocking.
void discord_announce_error(const char* text)
{
	char clean[DISCORD_MSG_MAX];
	time_t now;

	if( !g_errors_enabled || !g_running || text == NULL )
		return;
	strip_ansi(text, clean, sizeof(clean));
	if( clean[0] == '\0' )
		return;
	now = time(NULL);

	pthread_mutex_lock(&g_mtx);
	// drop an identical error repeated within the dedup window (the SQL-outage flood)
	if( strcmp(clean, g_last_err) == 0 && (now - g_last_err_time) < DISCORD_ERR_DEDUP ) {
		pthread_mutex_unlock(&g_mtx);
		return;
	}
	// burst guard: never post errors faster than one per MINGAP sec
	if( g_last_any_err_time != 0 && (now - g_last_any_err_time) < DISCORD_ERR_MINGAP ) {
		pthread_mutex_unlock(&g_mtx);
		return;
	}
	strncpy(g_last_err, clean, sizeof(g_last_err) - 1);
	g_last_err[sizeof(g_last_err) - 1] = '\0';
	g_last_err_time = now;
	g_last_any_err_time = now;

	if( g_count < DISCORD_QUEUE_MAX ) {
		// U+26A0 U+FE0F warning sign + the cleaned message (snprintf truncates safely)
		snprintf(g_queue[g_tail], DISCORD_MSG_MAX, "\xE2\x9A\xA0\xEF\xB8\x8F %s", clean);
		g_tail = (g_tail + 1) % DISCORD_QUEUE_MAX;
		++g_count;
		pthread_cond_signal(&g_cv);
	}
	pthread_mutex_unlock(&g_mtx);
}

// Minimal "key: value" reader for one config file. Keys: discord_announce (yes/no),
// discord_webhook (URL), discord_username (display name). Lines starting with // are comments.
// Missing file is silently fine (lets the import override be optional).
static void discord_config_parse(const char* path)
{
	char line[1024];
	FILE* fp = fopen(path, "r");
	if( fp == NULL )
		return;
	while( fgets(line, sizeof(line), fp) ) {
		char key[64], val[960];
		size_t L;
		if( line[0] == '/' && line[1] == '/' )
			continue;
		if( sscanf(line, " %63[^:]: %959[^\r\n]", key, val) != 2 )
			continue;
		// trim trailing whitespace on key and value
		L = strlen(key);  while( L && (key[L-1] == ' ' || key[L-1] == '\t') ) key[--L] = '\0';
		L = strlen(val);  while( L && (val[L-1] == ' ' || val[L-1] == '\t' || val[L-1] == '\r') ) val[--L] = '\0';

		if( strcmp(key, "discord_announce") == 0 )
			g_enabled = (strcmp(val, "yes") == 0 || strcmp(val, "1") == 0 || strcmp(val, "true") == 0);
		else if( strcmp(key, "discord_errors") == 0 )
			g_errors_enabled = (strcmp(val, "yes") == 0 || strcmp(val, "1") == 0 || strcmp(val, "true") == 0);
		else if( strcmp(key, "discord_webhook") == 0 ) {
			strncpy(g_webhook, val, sizeof(g_webhook) - 1);
			g_webhook[sizeof(g_webhook) - 1] = '\0';
		} else if( strcmp(key, "discord_username") == 0 && val[0] ) {
			strncpy(g_username, val, sizeof(g_username) - 1);
			g_username[sizeof(g_username) - 1] = '\0';
		}
	}
	fclose(fp);
}

// Read the shipped template first, then the local import override (kept out of git), whose
// keys win. The webhook URL is a secret, so it belongs in conf/import/discord_conf.txt on the
// host, never committed to the repo.
static void discord_config_read(void)
{
	discord_config_parse("conf/discord.conf");
	discord_config_parse("conf/import/discord_conf.txt");
}

void discord_init(void)
{
	discord_config_read();
	if( !g_enabled )
		return;
	if( g_webhook[0] == '\0' || strncmp(g_webhook, "https://", 8) != 0 || strchr(g_webhook, '\'') != NULL ) {
		ShowWarning("Discord relay: missing or invalid webhook URL (need https://, no quote); relay disabled.\n");
		g_enabled = 0;
		return;
	}
	g_shutdown = 0;
	if( pthread_create(&g_thread, NULL, discord_worker, NULL) != 0 ) {
		ShowError("Discord relay: failed to start worker thread; relay disabled.\n");
		g_enabled = 0;
		return;
	}
	g_running = 1;
	// Mirror critical server errors too, if asked (registered AFTER g_running so the hook never
	// fires into a not-yet-started worker).
	if( g_errors_enabled )
		showmsg_set_error_hook(discord_announce_error);
	ShowStatus("Discord relay enabled (bot '%s'%s).\n", g_username,
		g_errors_enabled ? ", mirroring errors" : "");
	discord_announce("\xF0\x9F\x9F\xA2 Сервер запущен");  // U+1F7E2 green circle
}

void discord_final(void)
{
	if( !g_running )
		return;
	// Stop mirroring errors first, so shutdown-time error spam can't flood the queue or race the
	// worker teardown.
	showmsg_set_error_hook(NULL);
	// Queue the stop notice first, then signal shutdown: the worker drains the queue (sending
	// this message) before it exits, and the pthread_join below waits for that send to finish.
	discord_announce("\xF0\x9F\x94\xB4 Сервер остановлен");  // U+1F534 red circle
	pthread_mutex_lock(&g_mtx);
	g_shutdown = 1;
	pthread_cond_signal(&g_cv);
	pthread_mutex_unlock(&g_mtx);
	pthread_join(g_thread, NULL);
	g_running = 0;
}
