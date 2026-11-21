// Daily play-time limit (S. 2026-11-21): the pure rules, shared by the char- and map-server and unit tested by
// test_playlimit.c. A character may stay on the map-server `daily_play_limit` hours a day; the minutes are kept
// with the date of the reset they belong to (char.play_minutes / char.play_date, play_reset.reset_date). The
// char-server resets at 00:00 server time or 24 h after the last reset by the monotonic clock, whichever comes
// first; minutes stamped with another date count as 0, so a row the reset never touched is right at load.
#ifndef _PLAYLIMIT_H_
#define _PLAYLIMIT_H_

#include <time.h>

#define PLAYLIMIT_DAY_MS ((t_tick)24 * 3600 * 1000)

enum playlimit_reset { PLAYLIMIT_RESET_NONE = 0, PLAYLIMIT_RESET_MIDNIGHT, PLAYLIMIT_RESET_24H };

// The server's local date of `t` as YYYYMMDD.
static inline int playlimit_date(time_t t)
{
	struct tm tm;
	localtime_r(&t, &tm);
	return (tm.tm_year + 1900) * 10000 + (tm.tm_mon + 1) * 100 + tm.tm_mday;
}

// Minutes played: the stored ones plus the whole minutes since the map login (the seconds are dropped).
static inline int playlimit_minutes(int base, t_tick login_tick, t_tick now)
{
	t_tick d = now - login_tick;
	return base + (d > 0 ? (int)(d / 60000) : 0);
}

// Does the limit apply to an account of this GM level? (limit 0 = the mechanism is off)
static inline bool playlimit_applies(int limit_hours, int gm_level)
{
	return limit_hours > 0 && gm_level <= 1;
}

// Minutes left today, never negative. With the limit off there is always time left.
static inline int playlimit_left(int limit_hours, int minutes)
{
	int left;
	if (limit_hours <= 0)
		return 0x7fffffff;
	left = limit_hours * 60 - minutes;
	return left > 0 ? left : 0;
}

// The warning to give at `left` minutes left: 30, 10 or 1 when that mark was just reached (the smallest one
// crossed since the last call), else 0. `warned` keeps the marks already given; 0 = none (a new day).
static inline int playlimit_warning(int left, int *warned)
{
	static const int marks[] = { 1, 10, 30 };
	int i;
	if (left <= 0)
		return 0;
	for (i = 0; i < 3; i++) {
		if (left <= marks[i]) {
			if (*warned & (1 << i))
				return 0;
			*warned |= 7 & ~((1 << i) - 1); // this mark and every larger one: 29 -> 5 gives only the 10-minute one
			return marks[i];
		}
	}
	return 0;
}

// Must the char-server reset now? `last_date` is the date of the last reset, `today` the current date,
// `since_reset` the monotonic time since it.
static inline enum playlimit_reset playlimit_reset_reason(int last_date, int today, t_tick since_reset)
{
	if (today != last_date)
		return PLAYLIMIT_RESET_MIDNIGHT;
	if (since_reset >= PLAYLIMIT_DAY_MS)
		return PLAYLIMIT_RESET_24H;
	return PLAYLIMIT_RESET_NONE;
}

// After a restart: how long ago was the stored reset, by the wall clock, in [0, 24 h].
static inline t_tick playlimit_since_reset(time_t reset_at, time_t now)
{
	t_tick d = (t_tick)(now - reset_at) * 1000;
	if (d < 0)
		return 0;
	return d > PLAYLIMIT_DAY_MS ? PLAYLIMIT_DAY_MS : d;
}

// The minutes a save stamped `save_date` may write when the current reset date is `cur_date`: a save of an
// older day (sent before a reset, arriving after it) keeps what the current day already has.
static inline int playlimit_saved_minutes(int save_date, int cur_date, int save_minutes, int cur_minutes)
{
	return save_date == cur_date ? save_minutes : cur_minutes;
}

// The minutes of a character row stamped `row_date` when the current reset date is `cur_date`.
static inline int playlimit_loaded_minutes(int row_date, int cur_date, int row_minutes)
{
	return row_date == cur_date ? row_minutes : 0;
}

#endif /* _PLAYLIMIT_H_ */
