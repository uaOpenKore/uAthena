// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef	_TIMER_H_
#define	_TIMER_H_

#ifndef _CBASETYPES_H_
#include "../common/cbasetypes.h"
#endif

#define BASE_TICK 5

#define TIMER_ONCE_AUTODEL 0x1
#define TIMER_INTERVAL 0x2
#define TIMER_REMOVE_HEAP 0x10

// [tick64] The tick is a 64-bit count of milliseconds (S. 2026-11-20). The 32-bit tick wrapped every 49.7 days
// and DIFF_TICK flipped its sign for any two ticks more than 24.8 days apart: mobs on a map nobody visited for
// that long never thought, walked, attacked or respawned again. A 64-bit tick never wraps, so DIFF_TICK is a
// plain difference, right for any two ticks however far apart. (t_tick itself is in cbasetypes.h.)

#define DIFF_TICK(a,b) ((t_tick)(a) - (t_tick)(b))

// A tick difference as int, for the places that store or send one as int (durations, delays, packet fields):
// one beyond the int range (> 24.8 days) is clamped instead of being cut to its low 32 bits.
static inline int diff_tick32(t_tick a, t_tick b)
{
	t_tick d = a - b;
	return d > INT_MAX ? INT_MAX : d < INT_MIN ? INT_MIN : (int)d;
}
#define DIFF_TICK32(a,b) diff_tick32((t_tick)(a), (t_tick)(b))

// [clock] What gettick() returns right after the process starts (one day, in ms); see gettick_nocache.
#define TICK_START_MS 86400000

// The tick as the client and the network see it: their fields are 32-bit (the client only compares ticks it
// gets from us with each other, so the low 32 bits are all it needs).
#define TICK32(t) ((uint32)(t))

#define INVALID_TIMER -1

// Struct declaration

typedef int (*TimerFunc)(int tid, t_tick tick, intptr_t id, intptr_t data);

struct TimerData {
	t_tick tick;
	TimerFunc func;
	intptr_t id;
	intptr_t data;
	int type;
	int interval;
	int heap_pos;
};

// Function prototype declaration

t_tick gettick_nocache(void);
t_tick gettick(void);

int add_timer(t_tick tick, TimerFunc f, intptr_t id, intptr_t data);
int add_timer_interval(t_tick tick, TimerFunc func, intptr_t id, intptr_t data, int interval);
int delete_timer(int tid, TimerFunc f);

t_tick addtick_timer(int tid, t_tick tick);
t_tick settick_timer(int tid, t_tick tick);
struct TimerData *get_timer(int tid);

int do_timer(t_tick tick);

int add_timer_func_list(TimerFunc func, char* name);
char* search_timer_func_list(TimerFunc f);

unsigned long get_uptime(void);

// [metrics] LOOPMETRIC (core.c)
extern int metrics_log;
extern unsigned int timer_metric_run;
extern t_tick timer_metric_slow_ms;
extern TimerFunc timer_metric_slow_func;
int timer_live_count(void);
void timer_foreach_func(TimerFunc func, void (*cb)(int tid, struct TimerData* td, void* arg), void* arg);
void timer_metric_reset_slow(void);

void timer_init(void);
void timer_final(void);

#endif /* _TIMER_H_ */
