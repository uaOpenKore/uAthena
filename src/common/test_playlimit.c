// Standalone unit test for the daily play-time limit rules (playlimit.h).
//
// Not part of `make sql`. Build & run with:
//   gcc -Wall -I src/common -o /tmp/test_playlimit src/common/test_playlimit.c
//   /tmp/test_playlimit
//
// The rules (S. 2026-11-21): a character may stay on the map-server `daily_play_limit` hours a day (whole
// minutes from the map login, the seconds of a session are dropped); GM accounts (level > 1) are exempt; the
// counter of every character goes back to 0 at 00:00 by the server's clock, or 24 h after the last reset by the
// monotonic clock, whichever comes first, so a clock correction never skips or doubles a day for long; a save
// sent before a reset that arrives after it must not bring the old minutes back (it carries the reset date).

#include "cbasetypes.h"
#include "playlimit.h"

#include <stdio.h>
#include <stdlib.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

static time_t local(int y, int mo, int d, int h, int mi, int s)
{
	struct tm tm = {0};
	tm.tm_year = y - 1900; tm.tm_mon = mo - 1; tm.tm_mday = d;
	tm.tm_hour = h; tm.tm_min = mi; tm.tm_sec = s; tm.tm_isdst = -1;
	return mktime(&tm);
}

int main(void)
{
	const t_tick H = 3600 * 1000;

	setenv("TZ", "Europe/Kyiv", 1);
	tzset();

	// the date
	CHECK(playlimit_date(local(2026, 11, 21, 23, 59, 59)) == 20261121, "23:59:59 is still the 21st");
	CHECK(playlimit_date(local(2026, 11, 22, 0, 0, 0)) == 20261122, "00:00:00 is the 22nd");

	// minutes played: whole minutes since the map login on top of the stored ones
	CHECK(playlimit_minutes(100, 1000, 1000) == 100, "just logged in: the stored minutes");
	CHECK(playlimit_minutes(100, 1000, 1000 + 59999) == 100, "59.999 s: no new minute yet");
	CHECK(playlimit_minutes(100, 1000, 1000 + 60000) == 101, "60 s: one more minute");
	CHECK(playlimit_minutes(0, 0, 25 * H) == 1500, "25 h in one session");
	CHECK(playlimit_minutes(5, 2000, 1000) == 5, "a tick before the login counts nothing");

	// the limit
	CHECK(playlimit_left(12, 719) == 1, "719 of 720 minutes: 1 left");
	CHECK(playlimit_left(12, 720) == 0, "720 of 720: none left");
	CHECK(playlimit_left(12, 800) == 0, "over the limit: none left, never negative");
	CHECK(playlimit_left(0, 5000) > 0, "limit 0 = off: always time left");
	CHECK(playlimit_applies(12, 0) && playlimit_applies(12, 1), "players and GM level 1 are limited");
	CHECK(!playlimit_applies(12, 2) && !playlimit_applies(12, 99), "GM level > 1 is exempt");
	CHECK(!playlimit_applies(0, 0), "limit 0 = off for everyone");

	// warnings at 30, 10 and 1 minute left: each once, the one just crossed
	{
		int w = 0;
		CHECK(playlimit_warning(31, &w) == 0, "31 left: no warning");
		CHECK(playlimit_warning(30, &w) == 30, "30 left: the 30-minute warning");
		CHECK(playlimit_warning(29, &w) == 0, "29 left: not again");
		CHECK(playlimit_warning(5, &w) == 10, "jumped from 29 to 5: the 10-minute warning (the last crossed)");
		CHECK(playlimit_warning(1, &w) == 1, "1 left: the 1-minute warning");
		CHECK(playlimit_warning(1, &w) == 0, "1 left again: not repeated");
		w = 0;
		CHECK(playlimit_warning(0, &w) == 0, "nothing left: no warning, the limit message instead");
	}

	// the reset
	CHECK(playlimit_reset_reason(20261121, 20261121, 23 * H) == PLAYLIMIT_RESET_NONE, "same day, 23 h: no reset");
	CHECK(playlimit_reset_reason(20261121, 20261122, 1000) == PLAYLIMIT_RESET_MIDNIGHT, "new date: reset");
	CHECK(playlimit_reset_reason(20261121, 20261121, 24 * H) == PLAYLIMIT_RESET_24H,
		"clock set back, same date after 24 h of real time: reset by the timer");
	CHECK(playlimit_reset_reason(20261122, 20261121, 1000) == PLAYLIMIT_RESET_MIDNIGHT,
		"clock set back across midnight: the date changed, reset");

	// the 24 h timer after a restart goes on from the stored reset time
	CHECK(playlimit_since_reset(local(2026, 11, 21, 0, 0, 0), local(2026, 11, 21, 10, 0, 0)) == 10 * H,
		"restart at 10:00 after the 00:00 reset: 10 h passed, 14 h left");
	CHECK(playlimit_since_reset(local(2026, 11, 21, 10, 0, 0), local(2026, 11, 21, 9, 0, 0)) == 0,
		"stored reset time in the future (clock set back): counts as just reset");
	CHECK(playlimit_since_reset(local(2026, 11, 19, 0, 0, 0), local(2026, 11, 21, 0, 0, 0)) == 24 * H,
		"two days down: capped at 24 h (reset now)");

	// a save carries the reset date it belongs to
	CHECK(playlimit_saved_minutes(20261121, 20261121, 700, 0) == 700, "a save of the current day: its minutes");
	CHECK(playlimit_saved_minutes(20261120, 20261121, 700, 0) == 0,
		"a save sent before the reset, arriving after it: the minutes stay 0");
	CHECK(playlimit_saved_minutes(20261120, 20261121, 700, 3) == 3,
		"an old save keeps what the current day already has");

	// a character row keeps the date its minutes belong to: minutes of another day count as 0 at load
	CHECK(playlimit_loaded_minutes(20261121, 20261121, 500) == 500, "row of the current day: its minutes");
	CHECK(playlimit_loaded_minutes(20261120, 20261121, 500) == 0, "row of an older day: 0 (reset lazily)");
	CHECK(playlimit_loaded_minutes(0, 20261121, 500) == 0, "row never stamped: 0");

	printf("%s (%d failure(s))\n", failures ? "FAILED" : "ALL PASSED", failures);
	return failures ? 1 : 0;
}
