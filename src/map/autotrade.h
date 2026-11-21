// Autotrade shops that survive a server restart (S. 2026-11-21).
#ifndef _AUTOTRADE_H_
#define _AUTOTRADE_H_

struct map_session_data;

void autotrade_open(struct map_session_data* sd);    // @autotrade: the shop is kept, the char-server told it is not online
void autotrade_sold(struct map_session_data* sd);    // a sale from an autotrade shop: the amounts kept follow
void autotrade_quit(struct map_session_data* sd);    // an autotrader leaves the map-server (owner login, sold out)
void autotrade_owner_login(struct map_session_data* sd); // a character logs in itself: its kept shop not back yet is dropped
void autotrade_restore_loaded(struct map_session_data* sd); // pc_reg_received of a restored autotrader: the shop opens
void autotrade_restore_start(void);                  // the char-server connection is up: restore the kept shops
void autotrade_restore_ack(int fd);                  // 0x2b26: a kept shop's character from the char-server
void do_init_autotrade(void);
void do_final_autotrade(void);                       // shutdown: the kept shops are written as they are now
void do_final_autotrade_db(void);                    // the end of the shutdown: the memory

#endif /* _AUTOTRADE_H_ */
