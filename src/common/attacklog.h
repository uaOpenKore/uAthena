// Abnormal packets and connections: one line each in log/attack-<server>.log (S. 2026-11-21), to see attempts on
// the login/char/map-servers. At most ATTACKLOG_PER_MIN lines a minute per address; the rest becomes one
// "... N more" line, so a flood cannot fill the disk.
#ifndef _ATTACKLOG_H_
#define _ATTACKLOG_H_

#include "cbasetypes.h"

#define ATTACKLOG_PER_MIN 20

// server: "login", "char" or "map"; the file is log/attack-login.log, log/attack-char.log, log/attack-map<N>.log
// (N from the UA_MAP_INSTANCE environment variable that ua-start.sh sets, 1 without it).
void attacklog_init(const char* server);
void attacklog_final(void);

// One line: "<date> <time> [ATTACK] <server> <ip> <who> <what>"; who is "acc=.. cid=.." or "-".
void attacklog(uint32 ip, const char* who, const char* fmt, ...);

// The same for a packet of session fd: its address, and the first bytes of what it sent (head=..).
void attacklog_packet(int fd, const char* who, const char* fmt, ...);

#endif /* _ATTACKLOG_H_ */
