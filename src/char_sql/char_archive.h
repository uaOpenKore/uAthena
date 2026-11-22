// Copyright (c) uAthena / bornrok.com
#ifndef _CHAR_ARCHIVE_H_
#define _CHAR_ARCHIVE_H_
// [archive] Inactive accounts into the archive tables and back on a login (char_archive.c).
#include "../common/timer.h"
int char_archive_config(const char* w1, const char* w2);
void char_archive_init(void);
int char_archive_timer(int tid, t_tick tick, intptr_t id, intptr_t data);
void char_archive_restore(int account_id);
int char_archive_name_taken(const char* esc_name);
#include <mysql.h>
MYSQL* char_archive_login_db(void);
#endif
