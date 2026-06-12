// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef	_SOCKET_H_
#define _SOCKET_H_

#ifndef _CBASETYPES_H_
#include "../common/cbasetypes.h"
#endif

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include <time.h>

// Maximum socket fd the server can hold. Replaces the old FD_SETSIZE (1024)
// ceiling that select() imposed; with epoll the limit is just this array size
// (and the OS open-file limit, which socket_init raises via setrlimit).
#define SOCKET_MAX 32768


// socket I/O macros
#define RFIFOHEAD(fd)
#define WFIFOHEAD(fd, size) do{ if((fd) && session[fd]->wdata_size + (size) > session[fd]->max_wdata ) realloc_writefifo(fd, size); }while(0)
#define RFIFOP(fd,pos) (session[fd]->rdata + session[fd]->rdata_pos + (pos))
#define WFIFOP(fd,pos) (session[fd]->wdata + session[fd]->wdata_size + (pos))

// Unaligned-safe 16/32-bit field access for packet buffers. Reading/writing a
// member of a __packed__ struct is well-defined for ANY address (the member has
// alignment 1), unlike *(uint16*)ptr which is undefined behaviour on a
// misaligned address. It stays an lvalue and compiles to the same instruction on
// x86, while being correct on strict-alignment CPUs (ARM/MIPS/SPARC) too.
struct s_unaligned_u16 { uint16 v; } __attribute__((packed));
struct s_unaligned_u32 { uint32 v; } __attribute__((packed));

#define RFIFOB(fd,pos) (*(uint8*)RFIFOP(fd,pos))
#define WFIFOB(fd,pos) (*(uint8*)WFIFOP(fd,pos))
#define RFIFOW(fd,pos) (((struct s_unaligned_u16*)RFIFOP(fd,pos))->v)
#define WFIFOW(fd,pos) (((struct s_unaligned_u16*)WFIFOP(fd,pos))->v)
#define RFIFOL(fd,pos) (((struct s_unaligned_u32*)RFIFOP(fd,pos))->v)
#define WFIFOL(fd,pos) (((struct s_unaligned_u32*)WFIFOP(fd,pos))->v)
#define RFIFOSPACE(fd) (session[fd]->max_rdata - session[fd]->rdata_size)
#define WFIFOSPACE(fd) (session[fd]->max_wdata - session[fd]->wdata_size)

#define RFIFOREST(fd)  (session[fd]->eof ? 0 : session[fd]->rdata_size - session[fd]->rdata_pos)
#define RFIFOFLUSH(fd) \
	do { \
		if(session[fd]->rdata_size == session[fd]->rdata_pos){ \
			session[fd]->rdata_size = session[fd]->rdata_pos = 0; \
		} else { \
			session[fd]->rdata_size -= session[fd]->rdata_pos; \
			memmove(session[fd]->rdata, session[fd]->rdata+session[fd]->rdata_pos, session[fd]->rdata_size); \
			session[fd]->rdata_pos = 0; \
		} \
	} while(0)

// buffer I/O macros
#define RBUFP(p,pos) (((uint8*)(p)) + (pos))
#define RBUFB(p,pos) (*(uint8*)RBUFP((p),(pos)))
#define RBUFW(p,pos) (((struct s_unaligned_u16*)RBUFP((p),(pos)))->v)
#define RBUFL(p,pos) (((struct s_unaligned_u32*)RBUFP((p),(pos)))->v)

#define WBUFP(p,pos) (((uint8*)(p)) + (pos))
#define WBUFB(p,pos) (*(uint8*)WBUFP((p),(pos)))
#define WBUFW(p,pos) (((struct s_unaligned_u16*)WBUFP((p),(pos)))->v)
#define WBUFL(p,pos) (((struct s_unaligned_u32*)WBUFP((p),(pos)))->v)

#define TOB(n) ((uint8)((n)&UINT8_MAX))
#define TOW(n) ((uint16)((n)&UINT16_MAX))
#define TOL(n) ((uint32)((n)&UINT32_MAX))


// Struct declaration
typedef int (*RecvFunc)(int fd);
typedef int (*SendFunc)(int fd);
typedef int (*ParseFunc)(int fd);

struct socket_data {
	unsigned char eof;
	unsigned char *rdata, *wdata;
	size_t max_rdata, max_wdata;
	size_t rdata_size, wdata_size;
	size_t rdata_pos;
	time_t rdata_tick; // time of last receive (for detecting timeouts)
	uint32 client_addr; // remote client address (zero for s2s connections)
	void* session_data;
	RecvFunc func_recv;
	SendFunc func_send;
	ParseFunc func_parse;
	unsigned char in_shortlist; // already queued in the send shortlist (dedup)
};


// Data prototype declaration

extern struct socket_data* session[SOCKET_MAX];

extern int fd_max;

extern time_t last_tick;
extern time_t stall_time;

//////////////////////////////////
// some checking on sockets
extern int session_isValid(int fd);
extern int session_isActive(int fd);
//////////////////////////////////

// Function prototype declaration

int make_listen_bind(uint32 ip, uint16 port);
int make_connection(uint32 ip, uint16 port);
int realloc_fifo(int fd, unsigned int rfifo_size, unsigned int wfifo_size);
int realloc_writefifo(int fd, size_t addition);
int WFIFOSET(int fd, int len);
int RFIFOSKIP(int fd, int len);

int do_sendrecv(int next);
int do_parsepacket(void);
void do_close(int fd);
void socket_init(void);
void socket_final(void);

extern void flush_fifo(int fd);
extern void flush_fifos(void);
extern void set_nonblocking(int fd, int yes);

void set_defaultparse(ParseFunc defaultparse);

// hostname/ip conversion functions
uint32 host2ip(const char* hostname);
const char* ip2str(uint32 ip, char ip_str[16]);
uint32 str2ip(const char* ip_str);
#define CONVIP(ip) (ip>>24)&0xFF,(ip>>16)&0xFF,(ip>>8)&0xFF,(ip>>0)&0xFF
uint16 ntows(uint16 netshort);

int socket_getips(uint32* ips, int max);

extern uint32 addr_[16];   // ip addresses of local host (host byte order)
extern int naddr_;   // # of ip addresses

void set_eof(int fd);

/// Use a shortlist of sockets instead of iterating all sessions for sockets
/// that have data to send or need eof handling.
/// Adapted to use a static array instead of a linked list.
///
/// @author Buuyo-tama
#define SEND_SHORTLIST

#ifdef SEND_SHORTLIST
struct send_shortlist_node {
	struct send_shortlist_node *next; // Next node in the linked list
	struct send_shortlist_node *prev; // Previous node in the linked list
	int fd; // FD that needs sending.
};

// Add a fd to the shortlist so that it'll be recognized as a fd that needs
// sending done on it.
void send_shortlist_add_fd(int fd);
// Do pending network sends (and eof handling) from the shortlist.
void send_shortlist_do_sends();
#endif

#endif /* _SOCKET_H_ */
