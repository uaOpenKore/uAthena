// Abnormal packets and connections log (S. 2026-11-21), see attacklog.h.
#include "attacklog.h"
#include "socket.h"
#include "showmsg.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>

static FILE* attack_fp = NULL;
static char attack_server[16] = "?";
static char attack_path[256] = "";
static int attack_day = 0;   // YYYYMMDD the open file belongs to (daily rotation, S. 2026-11-21)

static int attack_date(time_t t)
{
	struct tm tm;
	localtime_r(&t, &tm);
	return (tm.tm_year + 1900) * 10000 + (tm.tm_mon + 1) * 100 + tm.tm_mday;
}

// The file of day `day` goes to <name>-<day>.log; a new one is opened for today.
static void attacklog_rotate(int day)
{
	char old[300];
	size_t n = strlen(attack_path);
	if (attack_fp)
		fclose(attack_fp);
	attack_fp = NULL;
	if (day && n > 4) {
		snprintf(old, sizeof(old), "%.*s-%d.log", (int)(n - 4), attack_path, day);
		rename(attack_path, old);
	}
	attack_day = attack_date(time(NULL));
	if ((attack_fp = fopen(attack_path, "a")) != NULL)
		setvbuf(attack_fp, NULL, _IOLBF, 0);
}

// per address: the minute it is counted in, the lines written in it and the ones held back
#define ATTACK_SLOTS 512
static struct { uint32 ip; time_t minute; int lines; int held; } attack_slot[ATTACK_SLOTS];

void attacklog_init(const char* server)
{
	char path[256];
	const char* inst;
	snprintf(attack_server, sizeof(attack_server), "%s", server);
	if (strcmp(server, "map") == 0) {
		inst = getenv("UA_MAP_INSTANCE");
		snprintf(path, sizeof(path), "log/attack-map%s.log", inst && *inst ? inst : "1");
	} else
		snprintf(path, sizeof(path), "log/attack-%s.log", server);
	snprintf(attack_path, sizeof(attack_path), "%s", path);
	{	// a file left from an earlier day goes to its archive first
		struct stat st;
		int day = stat(path, &st) == 0 ? attack_date(st.st_mtime) : 0;
		attacklog_rotate(day && day != attack_date(time(NULL)) ? day : 0);
	}
	if (attack_fp == NULL) {
		ShowWarning("attacklog: cannot open %s, abnormal packets go to the console only\n", path);
		return;
	}
	ShowStatus("Abnormal packets are logged to '%s' (a new file every day).\n", path);
}

void attacklog_final(void)
{
	if (attack_fp)
		fclose(attack_fp);
	attack_fp = NULL;
}

static void attacklog_write(uint32 ip, const char* who, const char* what)
{
	char stamp[32];
	time_t now = time(NULL);
	struct tm tm;
	localtime_r(&now, &tm);
	strftime(stamp, sizeof(stamp), "%Y-%m-%d %H:%M:%S", &tm);
	if (attack_fp && attack_day != attack_date(now))
		attacklog_rotate(attack_day); // a new day: yesterday's file to its archive
	if (attack_fp)
		fprintf(attack_fp, "%s [ATTACK] %s %u.%u.%u.%u %s %s\n", stamp, attack_server, CONVIP(ip), who && *who ? who : "-", what);
	else
		ShowWarning("[ATTACK] %s %u.%u.%u.%u %s %s\n", attack_server, CONVIP(ip), who && *who ? who : "-", what);
}

// Whether this line may be written (and the "N more" line of the previous minute first).
static bool attacklog_allow(uint32 ip)
{
	time_t minute = time(NULL) / 60;
	unsigned int h = (ip ^ (ip >> 13) ^ (ip >> 22)) % ATTACK_SLOTS;
	if (attack_slot[h].ip != ip || attack_slot[h].minute != minute) {
		if (attack_slot[h].held > 0) {
			char more[96];
			snprintf(more, sizeof(more), "... %d more line(s) from this address held back in that minute", attack_slot[h].held);
			attacklog_write(attack_slot[h].ip, "-", more);
		}
		attack_slot[h].ip = ip;
		attack_slot[h].minute = minute;
		attack_slot[h].lines = 0;
		attack_slot[h].held = 0;
	}
	if (attack_slot[h].lines >= ATTACKLOG_PER_MIN) {
		attack_slot[h].held++;
		return false;
	}
	attack_slot[h].lines++;
	return true;
}

void attacklog(uint32 ip, const char* who, const char* fmt, ...)
{
	char what[512];
	va_list ap;
	if (!attacklog_allow(ip))
		return;
	va_start(ap, fmt);
	vsnprintf(what, sizeof(what), fmt, ap);
	va_end(ap);
	attacklog_write(ip, who, what);
}

void attacklog_packet(int fd, const char* who, const char* fmt, ...)
{
	char what[512], head[3 * 16 + 1];
	size_t n, i, len = 0;
	uint32 ip;
	va_list ap;
	if (fd <= 0 || fd >= SOCKET_MAX || session[fd] == NULL)
		return;
	ip = session[fd]->client_addr;
	if (!attacklog_allow(ip))
		return;
	va_start(ap, fmt);
	len = vsnprintf(what, sizeof(what), fmt, ap);
	va_end(ap);
	n = RFIFOREST(fd) < 16 ? RFIFOREST(fd) : 16;
	head[0] = '\0';
	for (i = 0; i < n; i++)
		snprintf(head + 3 * i, sizeof(head) - 3 * i, "%02x ", RFIFOB(fd, i));
	if (n && len < sizeof(what))
		snprintf(what + len, sizeof(what) - len, " head=%s(%u byte(s) waiting)", head, (unsigned int)RFIFOREST(fd));
	attacklog_write(ip, who, what);
}
