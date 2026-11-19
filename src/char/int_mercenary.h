// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef _INT_MERCENARY_H_
#define _INT_MERCENARY_H_

int inter_mercenary_init(void);
void inter_mercenary_final(void);
int inter_mercenary_save(void);
int inter_mercenary_delete_char(int char_id);

int inter_mercenary_parse_frommap(int fd);

extern char mercenary_txt[1024];

#endif /* _INT_MERCENARY_H_ */
