// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include <sys/types.h>

#include "../common/cbasetypes.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "timer.h"

#include <sys/socket.h>
#include <sys/time.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// ^C}[ulBX^[ANCAg
// T[o[ATIMER_MIN_INTERVAL B

// If the server shows no reaction when processing thousands of monsters
// or connected by many clients, please increase TIMER_MIN_INTERVAL.

#define TIMER_MIN_INTERVAL 50

// timers
static struct TimerData* timer_data	= NULL;
static int timer_data_max	= 0;
static int timer_data_num	= 0;

// free timers
static int* free_timer_list		= NULL;
static int free_timer_list_max	= 0;
static int free_timer_list_pos	= 0;

// timer min-heap: timer_heap[] holds tid's ordered so the soonest-to-expire
// sits at the root (index 0). timer_data[tid].heap_pos is the back-reference to
// each tid's slot, so settick/delete can relocate a timer in O(log n).
// Replaces the old O(n) insertion-sorted array (the [FlavioJS] TODO).
static int timer_heap_num = 0;
static int timer_heap_max = 0;
static int* timer_heap = NULL;

// for debug
struct timer_func_list {
	struct timer_func_list* next;
	TimerFunc func;
	char* name;
};
static struct timer_func_list* tfl_root = NULL;

time_t start_time;

/// Sets the name of a timer function.
int add_timer_func_list(TimerFunc func, char* name)
{
	struct timer_func_list* tfl;

	if (name) {
		for( tfl=tfl_root; tfl != NULL; tfl=tfl->next )
		{// check suspicious cases
			if( func == tfl->func )
				ShowWarning("add_timer_func_list: duplicating function %p(%s) as %s.\n",(void*)tfl->func,tfl->name,name);
			else if( strcmp(name,tfl->name) == 0 )
				ShowWarning("add_timer_func_list: function %p has the same name as %p(%s)\n",(void*)func,(void*)tfl->func,tfl->name);
		}
		CREATE(tfl,struct timer_func_list,1);
		tfl->next = tfl_root;
		tfl->func = func;
		tfl->name = aStrdup(name);
		tfl_root = tfl;
	}
	return 0;
}

/// Returns the name of the timer function.
char* search_timer_func_list(TimerFunc func)
{
	struct timer_func_list* tfl;

	for( tfl=tfl_root; tfl != NULL; tfl=tfl->next )
		if (func == tfl->func)
			return tfl->name;

	return "unknown timer function";
}

/*----------------------------
 * 	Get tick time
 *----------------------------*/
static unsigned int gettick_cache;
static int gettick_count;

unsigned int gettick_nocache(void)
{
	struct timeval tval;

	gettimeofday(&tval, NULL);
	gettick_count = 256;

	return gettick_cache = tval.tv_sec * 1000 + tval.tv_usec / 1000;
}

unsigned int gettick(void)
{
	if (--gettick_count < 0)
		return gettick_nocache();

	return gettick_cache;
}

/*======================================
 * 	CORE : Timer min-heap
 *--------------------------------------*/
/// Moves the timer at heap position pos up toward the root until the heap
/// property holds, updating heap_pos for every timer it shifts.
static void heap_sift_up(int pos)
{
	int tid = timer_heap[pos];
	while (pos > 0) {
		int parent = (pos - 1) / 2;
		if (DIFF_TICK(timer_data[tid].tick, timer_data[timer_heap[parent]].tick) >= 0)
			break; // parent already expires no later -> heap ok
		timer_heap[pos] = timer_heap[parent];
		timer_data[timer_heap[pos]].heap_pos = pos;
		pos = parent;
	}
	timer_heap[pos] = tid;
	timer_data[tid].heap_pos = pos;
}

/// Moves the timer at heap position pos down toward the leaves until the heap
/// property holds, updating heap_pos for every timer it shifts.
static void heap_sift_down(int pos)
{
	int tid = timer_heap[pos];
	int half = timer_heap_num / 2; // first leaf index
	while (pos < half) {
		int child = 2 * pos + 1; // left child
		if (child + 1 < timer_heap_num &&
			DIFF_TICK(timer_data[timer_heap[child+1]].tick, timer_data[timer_heap[child]].tick) < 0)
			child++; // right child expires sooner
		if (DIFF_TICK(timer_data[timer_heap[child]].tick, timer_data[tid].tick) >= 0)
			break; // soonest child expires no sooner -> heap ok
		timer_heap[pos] = timer_heap[child];
		timer_data[timer_heap[pos]].heap_pos = pos;
		pos = child;
	}
	timer_heap[pos] = tid;
	timer_data[tid].heap_pos = pos;
}

/// Adds a timer to the heap. O(log n).
static void push_timer_heap(int tid)
{
	// check number of element
	if (timer_heap_num >= timer_heap_max) {
		if (timer_heap_max == 0) {
			timer_heap_max = 256;
			CREATE(timer_heap, int, 256);
		} else {
			timer_heap_max += 256;
			RECREATE(timer_heap, int, timer_heap_max);
			memset(timer_heap + (timer_heap_max - 256), 0, sizeof(int) * 256);
		}
	}

	timer_heap[timer_heap_num] = tid;
	timer_data[tid].heap_pos = timer_heap_num;
	timer_heap_num++;
	heap_sift_up(timer_heap_num - 1);
}

/// Removes and returns the soonest-to-expire timer id (the heap root). O(log n).
static int pop_timer_heap(void)
{
	int tid = timer_heap[0];
	timer_data[tid].heap_pos = -1;
	timer_heap_num--;
	if (timer_heap_num > 0) {
		timer_heap[0] = timer_heap[timer_heap_num];
		timer_data[timer_heap[0]].heap_pos = 0;
		heap_sift_down(0);
	}
	return tid;
}

/*==========================
 * 	Timer Management
 *--------------------------*/

/// Returns a free timer id.
static int acquire_timer(void)
{
	int tid;

	if (free_timer_list_pos) {
		do {
			tid = free_timer_list[--free_timer_list_pos];
		} while(tid >= timer_data_num && free_timer_list_pos > 0);
	} else
		tid = timer_data_num;

	if (tid >= timer_data_num)
		for (tid = timer_data_num; tid < timer_data_max && timer_data[tid].type; tid++);
	if (tid >= timer_data_num && tid >= timer_data_max)
	{// expand timer array
		if (timer_data_max == 0)
		{// create timer data (1st time)
			timer_data_max = 256;
			CREATE(timer_data, struct TimerData, timer_data_max);
		} else
		{// add more timers
			timer_data_max += 256;
			RECREATE(timer_data, struct TimerData, timer_data_max);
			memset(timer_data + (timer_data_max - 256), 0, sizeof(struct TimerData) * 256);
		}
	}

	if (tid >= timer_data_num)
		timer_data_num = tid + 1;

	return tid;
}

int add_timer(unsigned int tick,TimerFunc func, intptr_t id, intptr_t data)
{
	int tid = acquire_timer();

	timer_data[tid].tick	= tick;
	timer_data[tid].func	= func;
	timer_data[tid].id		= id;
	timer_data[tid].data	= data;
	timer_data[tid].type	= TIMER_ONCE_AUTODEL;
	timer_data[tid].interval = 1000;
	push_timer_heap(tid);

	return tid;
}

int add_timer_interval(unsigned int tick, TimerFunc func, intptr_t id, intptr_t data, int interval)
{
	int tid;

	if (interval < 1) {
		ShowError("add_timer_interval : function %p(%s) has invalid interval %d!\n",
			 (void*)func, search_timer_func_list(func), interval);
		return -1;
	}
	
	tid = acquire_timer();
	timer_data[tid].tick	= tick;
	timer_data[tid].func	= func;
	timer_data[tid].id		= id;
	timer_data[tid].data	= data;
	timer_data[tid].type	= TIMER_INTERVAL;
	timer_data[tid].interval = interval;
	push_timer_heap(tid);

	return tid;
}

int delete_timer(int id, TimerFunc func)
{
	if (id <= 0 || id >= timer_data_num) {
		ShowError("delete_timer error : no such timer %d (%p(%s))\n", id, (void*)func, search_timer_func_list(func));
		return -1;
	}
	if (timer_data[id].func != func) {
		ShowError("delete_timer error : function mismatch %p(%s) != %p(%s)\n",
			 (void*)timer_data[id].func, search_timer_func_list(timer_data[id].func),
			 (void*)func, search_timer_func_list(func));
		return -2;
	}
	// 
	timer_data[id].func = NULL;
	timer_data[id].type = TIMER_ONCE_AUTODEL;

	return 0;
}

int addtick_timer(int tid, unsigned int tick)
{
	// Doesn't adjust the timer position. Might be the root of the FIXME in settick_timer. [FlavioJS]
	//return timer_data[tid].tick += tick;
	return settick_timer(tid, timer_data[tid].tick+tick);
}

//Sets the tick at which the timer triggers directly (a replacement of delete_timer + add_timer) [Skotlex]
//Reworked for the min-heap: the timer is located in O(1) via its heap_pos
//back-reference, then sifted up or down in O(log n). (The old sorted-array
//version was buggy - it did not reorganize the heap correctly.)
int settick_timer(int tid, unsigned int tick)
{
	int pos;

	if( timer_data[tid].tick == tick )
		return tick;

	pos = timer_data[tid].heap_pos;
	if( pos < 0 || pos >= timer_heap_num || timer_heap[pos] != tid )
	{
		ShowError("settick_timer: no such timer %d (%p(%s))\n", tid, (void*)timer_data[tid].func, search_timer_func_list(timer_data[tid].func));
		return -1;
	}

	timer_data[tid].tick = tick;
	// If the new tick is sooner than the parent's, the timer rises toward the
	// root; otherwise it may sink toward the leaves (sift_down is a no-op if it
	// is already correctly placed).
	if( pos > 0 && DIFF_TICK(tick, timer_data[timer_heap[(pos-1)/2]].tick) < 0 )
		heap_sift_up(pos);
	else
		heap_sift_down(pos);
	return tick;
}

struct TimerData* get_timer(int tid)
{
	return &timer_data[tid];
}

//Correcting the heap when the tick overflows is an idea taken from jA to
//prevent timer problems. Thanks to [End of Exam] for providing the required data. [Skotlex]
//This funtion will rearrange the heap and assign new tick values.
static void fix_timer_heap(unsigned int tick)
{
	int i, any = 0;

	if (timer_heap_num <= 0 || tick >= 0x00010000)
		return;

	//Pre-wrap leftovers: timers scheduled just before the tick wrapped now look
	//like they are ~49 days in the future. Reset them to fire now.
	//(not perfect, but works as long as no timer is genuinely expected 50+ days out)
	for (i = 0; i < timer_heap_num; i++) {
		if (timer_data[timer_heap[i]].tick > 0xf0000000) {
			timer_data[timer_heap[i]].tick = 0;
			any = 1;
		}
	}
	//Many ticks changed -> rebuild the heap (build-heap, O(n); happens at most
	//once per ~49-day tick wrap).
	if (any)
		for (i = timer_heap_num/2 - 1; i >= 0; i--)
			heap_sift_down(i);
}

int do_timer(unsigned int tick)
{
	static int fix_heap_flag = 0; //Fix the heap only once per tick wrap. [Skotlex]
	int nextmin = 1000;

	if (tick < 0x010000 && fix_heap_flag)
	{
		fix_timer_heap(tick);
		fix_heap_flag = 0;
	}

	while(timer_heap_num) {
		int i = timer_heap[0]; // soonest-to-expire (heap root)
		if ((nextmin = DIFF_TICK(timer_data[i].tick, tick)) > 0)
			break;

		pop_timer_heap(); // remove it from the heap
		timer_data[i].type |= TIMER_REMOVE_HEAP;
		if (timer_data[i].func) {
			if (nextmin < -1000) {
				// fired far too late: pass the current tick rather than the
				// (long past) scheduled one, so the callback doesn't over-rewind
				timer_data[i].func(i, tick, timer_data[i].id, timer_data[i].data);
			} else {
				timer_data[i].func(i, timer_data[i].tick, timer_data[i].id, timer_data[i].data);
			}
		}
		if (timer_data[i].type & TIMER_REMOVE_HEAP) {
			switch(timer_data[i].type & ~TIMER_REMOVE_HEAP) {
			case TIMER_ONCE_AUTODEL:
				timer_data[i].type = 0;
				if (free_timer_list_pos >= free_timer_list_max) {
					free_timer_list_max += 256;
					RECREATE(free_timer_list,int,free_timer_list_max);
					memset(free_timer_list + (free_timer_list_max - 256), 0, 256 * sizeof(int));
				}
				free_timer_list[free_timer_list_pos++] = i;
				break;
			case TIMER_INTERVAL:
				if (DIFF_TICK(timer_data[i].tick , tick) < -1000) {
					timer_data[i].tick = tick + timer_data[i].interval;
				} else {
					timer_data[i].tick += timer_data[i].interval;
				}
				timer_data[i].type &= ~TIMER_REMOVE_HEAP;
				push_timer_heap(i);
				break;
			}
		}
	}

	if (nextmin < TIMER_MIN_INTERVAL)
		nextmin = TIMER_MIN_INTERVAL;

	if (UINT_MAX - nextmin < tick) //Tick will loop, rearrange the heap on the next iteration.
		fix_heap_flag = 1;
	return nextmin;
}

unsigned long get_uptime(void)
{
	return (unsigned long)difftime(time(NULL), start_time);
}

void timer_init(void)
{
	time(&start_time);
}

void timer_final(void)
{
	struct timer_func_list *tfl;
	struct timer_func_list *next;

	for( tfl=tfl_root; tfl != NULL; tfl = next ) {
		next = tfl->next;	// copy next pointer
		aFree(tfl->name);	// free structures
		aFree(tfl);
	}

	if (timer_data) aFree(timer_data);
	if (timer_heap) aFree(timer_heap);
	if (free_timer_list) aFree(free_timer_list);
}
