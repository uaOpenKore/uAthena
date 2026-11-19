// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef _INT_QUEST_H_
#define _INT_QUEST_H_

int inter_quest_init(void);
void inter_quest_final(void);
int inter_quest_save(void);
int inter_quest_delete(int char_id);

int inter_quest_parse_frommap(int fd);

extern char quest_txt[1024];

#endif /* _INT_QUEST_H_ */
