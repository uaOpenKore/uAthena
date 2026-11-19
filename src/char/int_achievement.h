// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef _INT_ACHIEVEMENT_H_
#define _INT_ACHIEVEMENT_H_

int inter_achievement_init(void);
void inter_achievement_final(void);
int inter_achievement_save(void);
int inter_achievement_delete(int char_id);

int inter_achievement_parse_frommap(int fd);

extern char achievement_txt[1024];

#endif /* _INT_ACHIEVEMENT_H_ */
