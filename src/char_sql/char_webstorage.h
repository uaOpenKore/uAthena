// Copyright (c) uAthena / bornrok.com
#ifndef _CHAR_WEBSTORAGE_H_
#define _CHAR_WEBSTORAGE_H_
// [webstorage] Item requests from the web site (char_webstorage.c).
#include "../common/timer.h"
int char_webstorage_config(const char* w1, const char* w2);
void char_webstorage_init(void);
int char_webstorage_timer(int tid, t_tick tick, intptr_t id, intptr_t data);
#endif
