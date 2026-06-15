// [Backport] Hired Mercenary Soldier storage (char server).

#ifndef _INT_MERCENARY_H_
#define _INT_MERCENARY_H_

struct s_mercenary;
struct mmo_charstatus;

// Loaded/saved/deleted with the character (mercenary_owner table).
bool mercenary_owner_fromsql(int char_id, struct mmo_charstatus *status);
bool mercenary_owner_tosql(int char_id, struct mmo_charstatus *status);
bool mercenary_owner_delete(int char_id);

int inter_mercenary_sql_init(void);
void inter_mercenary_sql_final(void);
int inter_mercenary_parse_frommap(int fd);

#endif /* _INT_MERCENARY_H_ */
