// Standalone regression test for showmsg: a message of 2048 bytes or more (the static buffer) must still be
// formatted from the right arguments. The overflow path printed it a second time from the va_list the first
// vsnprintf had already used up: garbage, or a crash on a %s (any long SQL statement in a ShowDebug).
//
// Not part of `make sql`. Build & run from src/common:
//   gcc -I. -o /tmp/test_showmsg test_showmsg.c showmsg.c utils.c malloc.c strlib.c timer.c
//   /tmp/test_showmsg
#include "showmsg.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// stubs for common/malloc.o link deps
char* SERVER_NAME = "test_showmsg";
const char* get_svn_revision(void) { return "test"; }

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { fprintf(stderr, "FAIL: %s\n", (msg)); failures++; } \
		else         { fprintf(stderr, "ok  : %s\n", (msg)); } \
	} while (0)

static int count_char(const char* s, char c) { int n = 0; for (; *s; s++) n += (*s == c); return n; }

int main(void)
{
	static char big[3001], out[16384];
	const char* path = "/tmp/test_showmsg.out";
	FILE* f;
	size_t n;

	memset(big, 'x', 3000);
	big[3000] = '\0';
	if (freopen(path, "w", stdout) == NULL) { perror("freopen"); return 2; }
	ShowInfo("A%sB%dC%sD\n", big, 12345, "tail");     // 3000+ bytes: the dynamic buffer path
	ShowInfo("short %d %s\n", 7, "ok");               // the static buffer path still works
	fflush(stdout);
	f = fopen(path, "r");
	n = f ? fread(out, 1, sizeof(out) - 1, f) : 0;
	if (f) fclose(f);
	out[n] = '\0';

	CHECK(strstr(out, "B12345CtailD") != NULL, "a 3000-byte message keeps the arguments after the long one");
	CHECK(count_char(out, 'x') == 3000, "... and the long argument itself, all 3000 bytes");
	CHECK(strstr(out, "short 7 ok") != NULL, "a short message is still formatted");
	fprintf(stderr, "%s (%d failure(s))\n", failures ? "FAILED" : "PASSED", failures);
	return failures ? 1 : 0;
}
