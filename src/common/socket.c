// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include "../common/cbasetypes.h"
#include "../common/mmo.h"
#include "../common/timer.h"
#include "../common/malloc.h"
#include "../common/showmsg.h"
#include "../common/strlib.h"
#include "socket.h"
#include "send_worker.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/ioctl.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <sys/epoll.h>
#include <sys/resource.h>

#ifndef SIOCGIFCONF
#include <sys/sockio.h> // SIOCGIFCONF on Solaris, maybe others? [Shinomori]
#endif

#define SOCKET_ERROR -1
#define INVALID_SOCKET -1
#define ioctlsocket ioctl
#define closesocket close

#define s_errno errno
#define S_ENOTSOCK EBADF
#define S_EWOULDBLOCK EAGAIN
#define S_ECONNABORTED ECONNABORTED

// epoll: replaces the select() readable-fd set. epoll_fd is the epoll instance;
// epoll_events is filled by epoll_wait with the ready sockets each tick.
static int epoll_fd = -1;
static struct epoll_event* epoll_events = NULL;
int fd_max;
time_t last_tick;
time_t stall_time = 60;

uint32 addr_[16];   // ip addresses of local host (host byte order)
int naddr_ = 0;   // # of ip addresses

#define MODE_NODELAY 1 // disables|enables packet buffering

// values derived from freya
// a player that send more than 2k is probably a hacker without be parsed
// biggest known packet: S 0153 <len>.w <emblem data>.?B -> 24x24 256 color .bmp (0153 + len.w + 1618/1654/1756 bytes)
size_t rfifo_size = (16*1024);
size_t wfifo_size = (16*1024);

// [perf] Send coalescing (map server only). When > 0, the send worker combines
// the chunks already queued for a client into a single send() instead of one
// syscall per chunk — fewer syscalls, fewer TCP segments, less qdisc TX-lock
// contention under crowded maps (WoE). The worker holds an fd's lone sub-segment
// dribble up to this many ms so the small packets that pile up go out as one
// send(); anything that reaches ~1 TCP segment, and every EAGAIN drain, flushes
// immediately, so it cannot hold back a map-entry/spawn burst (an earlier
// game-loop timer version did, and broke "enter game" for remote clients).
// Requires the worker (socket_async_send: 1). map.c forwards this to the worker
// via sendworker_set_coalesce(). <=0 = off; >0 = window in ms (tune by testing).
int socket_send_coalesce_ms = 0;

// [perf] When set (map server only), client send() syscalls are performed on a
// dedicated worker thread (see send_worker.c) instead of inline on the game loop.
// 0 = inline (default, all servers). Set before accepting connections.
int socket_async_send = 0;

// [perf] When >0, set SO_SNDBUF (kernel send buffer) to this many bytes on each socket. A larger
// send buffer lets WoE bursts queue in-kernel instead of hitting EAGAIN (which forces an immediate
// flush + retry and defeats send-coalescing). 0 = leave the kernel default. Set from misc.conf.
int socket_sndbuf_size = 0;

struct socket_data* session[SOCKET_MAX];

#ifdef SEND_SHORTLIST
int send_shortlist_array[SOCKET_MAX];// fd's that have data to send / need eof handling
int send_shortlist_count = 0;// how many fd's are in the shortlist

// [perf] recv parse shortlist: only fds that received data are parsed each tick (vs scanning all
// fd_max sessions). Default ON; map.c may override from misc.conf. Mirrors the send shortlist.
int recv_parse_shortlist = 1;
int parse_shortlist_array[SOCKET_MAX];
int parse_shortlist_count = 0;
static void parse_shortlist_add_fd(int fd)
{
	if( !session_isValid(fd) )
		return;
	if( session[fd]->in_parselist )
		return; // dedup
	session[fd]->in_parselist = 1;
	parse_shortlist_array[parse_shortlist_count++] = fd;
}
// dedup is tracked per-session via session[fd]->in_shortlist (an fd_set would
// have re-imposed the FD_SETSIZE ceiling we are removing).
#endif

/// Registers fd with the epoll instance for read readiness (level-triggered,
/// matching the old select() semantics — the fifo recv reads what it can each
/// tick and gets re-notified while data remains).
static void epoll_add(int fd)
{
	struct epoll_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.events = EPOLLIN;
	ev.data.fd = fd;
	if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, fd, &ev) != 0)
		ShowError("epoll_add: EPOLL_CTL_ADD failed for fd %d (code %d)\n", fd, errno);
}

/// Removes fd from the epoll instance (closing the fd also removes it, so a
/// missing entry here is not an error).
static void epoll_del(int fd)
{
	epoll_ctl(epoll_fd, EPOLL_CTL_DEL, fd, NULL);
}

int create_session(int fd, RecvFunc func_recv, SendFunc func_send, ParseFunc func_parse);

#ifndef MINICORE
	int ip_rules = 1;
	static int connect_check(uint32 ip);
#endif


/*======================================
 *	CORE : Default processing functions
 *--------------------------------------*/
int null_recv(int fd) { return 0; }
int null_send(int fd) { return 0; }
int null_parse(int fd) { return 0; }

ParseFunc default_func_parse = null_parse;

void set_defaultparse(ParseFunc defaultparse)
{
	default_func_parse = defaultparse;
}


/*======================================
 *	CORE : Socket options
 *--------------------------------------*/
void set_nonblocking(int fd, int yes)
{
	// TCP_NODELAY BOOL Disables the Nagle algorithm for send coalescing.
	if(MODE_NODELAY)
		setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, (char *)&yes, sizeof yes);

	// FIONBIO Use with a nonzero argp parameter to enable the nonblocking mode of socket s.
	// The argp parameter is zero if nonblocking is to be disabled.
	if (ioctlsocket(fd, FIONBIO, &yes) != 0)
		ShowError("Couldn't set the socket to non-blocking mode (code %d)!\n", s_errno);
}

void setsocketopts(int fd)
{
	int yes = 1;
	setsockopt(fd,SOL_SOCKET,SO_REUSEADDR,(char *)&yes,sizeof(yes));
#ifdef SO_REUSEPORT
	setsockopt(fd,SOL_SOCKET,SO_REUSEPORT,(char *)&yes,sizeof(yes));
#endif
	setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, (char *)&yes, sizeof(yes));
	if( socket_sndbuf_size > 0 ) // [perf] enlarge kernel send buffer (WoE bursts -> fewer EAGAIN); 0 = kernel default
		setsockopt(fd, SOL_SOCKET, SO_SNDBUF, (char *)&socket_sndbuf_size, sizeof(socket_sndbuf_size));
//	setsockopt(fd, SOL_SOCKET, SO_RCVBUF, (char *) &rfifo_size , sizeof(rfifo_size ));

	// force the socket into no-wait, graceful-close mode (should be the default, but better make sure)
	//(http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winsock/winsock/closesocket_2.asp)
	{
	struct linger opt;
	opt.l_onoff = 0; // SO_DONTLINGER
	opt.l_linger = 0; // Do not care
	if (setsockopt(fd, SOL_SOCKET, SO_LINGER, (char*)&opt, sizeof(opt)))
		ShowWarning("setsocketopts: Unable to set SO_LINGER mode for connection %d!\n",fd);
	}
}

/*======================================
 *	CORE : Socket Sub Function
 *--------------------------------------*/
void set_eof(int fd)
{
	if( session_isActive(fd) )
	{
#ifdef SEND_SHORTLIST
		// Add this socket to the shortlist for eof handling.
		send_shortlist_add_fd(fd);
#endif
		session[fd]->eof = 1;
	}
}

int recv_to_fifo(int fd)
{
	int len;

	if( !session_isActive(fd) )
		return -1;

	len = recv(fd, (char *) session[fd]->rdata + session[fd]->rdata_size, RFIFOSPACE(fd), 0);

	if (len == SOCKET_ERROR) {
		if (s_errno == S_ECONNABORTED) {
			ShowWarning("recv_to_fifo: Software caused connection abort on session #%d\n", fd);
			epoll_del(fd); //Stop polling this dead socket until it's closed.
		}
		if (s_errno != S_EWOULDBLOCK) {
			//ShowDebug("recv_to_fifo: error %d, ending connection #%d\n", s_errno, fd);
			set_eof(fd);
		}
		return 0;
	}

	if (len == 0) { //Normal connection end.
		set_eof(fd);
		return 0;
	}

	session[fd]->rdata_size += len;
	session[fd]->rdata_tick = last_tick;
	if( recv_parse_shortlist )
		parse_shortlist_add_fd(fd);	// [perf] mark this fd for parsing this tick
	return 0;
}

int send_from_fifo(int fd)
{
	int len;

	if( !session_isValid(fd) )
		return -1;

	if (session[fd]->wdata_size == 0)
		return 0;

	// [perf] Off-thread send: hand an owned copy to the send worker and return,
	// so the game loop never enters the kernel TCP stack for client traffic.
	// Inter-server (s2s, client_addr==0) always stays on the inline path.
	if( socket_async_send && session[fd]->client_addr != 0 ) {
		sendworker_send(fd, session[fd]->wdata, session[fd]->wdata_size);
		session[fd]->wdata_size = 0;
		return 0;
	}

	len = send(fd, (const char *) session[fd]->wdata, session[fd]->wdata_size, 0);

	if (len == SOCKET_ERROR) {
		if (s_errno == S_ECONNABORTED) {
			ShowWarning("send_from_fifo: Software caused connection abort on session #%d\n", fd);
			epoll_del(fd); //Stop polling this dead socket until it's closed.
		}
		if (s_errno != S_EWOULDBLOCK) {
			//ShowDebug("send_from_fifo: error %d, ending connection #%d\n", s_errno, fd);
			session[fd]->wdata_size = 0; //Clear the send queue as we can't send anymore. [Skotlex]
			set_eof(fd);
		}
		return 0;
	}

	//{ int i; ShowMessage("send %d : ",fd);  for(i=0;i<len;i++){ ShowMessage("%02x ",session[fd]->wdata[i]); } ShowMessage("\n");}
	if(len > 0) {
		if((size_t)len < session[fd]->wdata_size)
			memmove(session[fd]->wdata, session[fd]->wdata + len, session[fd]->wdata_size - len);

		session[fd]->wdata_size -= len;
	}

	return 0;
}

/// Best effort - there's no warranty that the data will be sent.
void flush_fifo(int fd)
{
	if(session[fd] != NULL)
		session[fd]->func_send(fd);
}

void flush_fifos(void)
{
	int i;
	for(i = 1; i < fd_max; i++)
		flush_fifo(i);
}

/*======================================
 *	CORE : Connection functions
 *--------------------------------------*/
int connect_client(int listen_fd)
{
	int fd;
	struct sockaddr_in client_address;
	socklen_t len;

	len = sizeof(client_address);

	fd = accept(listen_fd, (struct sockaddr*)&client_address, &len);
	if ( fd == INVALID_SOCKET ) {
		ShowError("accept failed (code %i)!\n", s_errno);
		return -1;
	}

	if ( fd >= SOCKET_MAX ) { //Not enough capacity for this socket
		ShowError("connect_client: New socket #%d exceeds SOCKET_MAX (%d)!\n", fd, SOCKET_MAX);
		closesocket(fd);
		return -1;
	}

	setsocketopts(fd);
	set_nonblocking(fd, 1);

#ifndef MINICORE
	if( ip_rules && !connect_check(ntohl(client_address.sin_addr.s_addr)) ) {
		do_close(fd);
		return -1;
	}
#endif

	if( fd_max <= fd ) fd_max = fd + 1;
	epoll_add(fd);

	create_session(fd, recv_to_fifo, send_from_fifo, default_func_parse);
	session[fd]->client_addr = ntohl(client_address.sin_addr.s_addr);
	session[fd]->rdata_tick = last_tick;

	return fd;
}

int make_listen_bind(uint32 ip, uint16 port)
{
	struct sockaddr_in server_address;
	int fd;
	int result;

	fd = (int)socket( AF_INET, SOCK_STREAM, 0 );

	if (fd == INVALID_SOCKET) {
		ShowError("socket() creation failed (code %d)!\n", s_errno);
		exit(1);
	}

	if ( fd >= SOCKET_MAX ) { //Not enough capacity for this socket
		ShowError("make_listen_bind: New socket #%d exceeds SOCKET_MAX (%d)!\n", fd, SOCKET_MAX);
		closesocket(fd);
		return -1;
	}

	setsocketopts(fd);
	set_nonblocking(fd, 1);

	server_address.sin_family      = AF_INET;
	server_address.sin_addr.s_addr = htonl(ip);
	server_address.sin_port        = htons(port);

	result = bind(fd, (struct sockaddr*)&server_address, sizeof(server_address));
	if( result == SOCKET_ERROR ) {
		ShowError("bind failed (socket %d, code %d)!\n", fd, s_errno);
		exit(1);
	}
	result = listen( fd, 5 );
	if( result == SOCKET_ERROR ) {
		ShowError("listen failed (socket %d, code %d)!\n", fd, s_errno);
		exit(1);
	}
	if ( fd < 0 || fd > SOCKET_MAX )
	{ //Crazy error that can happen in Windows? (info from Freya)
		ShowFatalError("listen() returned invalid fd %d!\n",fd);
		exit(1);
	}

	if(fd_max <= fd) fd_max = fd + 1;
	epoll_add(fd);

	create_session(fd, connect_client, null_send, null_parse);

	return fd;
}

int make_connection(uint32 ip, uint16 port)
{
	struct sockaddr_in server_address;
	int fd;
	int result;

	fd = (int)socket( AF_INET, SOCK_STREAM, 0 );

	if (fd == INVALID_SOCKET) {
		ShowError("socket() creation failed (code %d)!\n", s_errno);
		return -1;
	}

	if ( fd >= SOCKET_MAX ) { //Not enough capacity for this socket
		ShowError("make_connection: New socket #%d exceeds SOCKET_MAX (%d)!\n", fd, SOCKET_MAX);
		closesocket(fd);
		return -1;
	}

	setsocketopts(fd);

	server_address.sin_family      = AF_INET;
	server_address.sin_addr.s_addr = htonl(ip);
	server_address.sin_port        = htons(port);

	ShowStatus("Connecting to %d.%d.%d.%d:%i\n", CONVIP(ip), port);

	result = connect(fd, (struct sockaddr *)(&server_address), sizeof(struct sockaddr_in));
	if( result == SOCKET_ERROR ) {
		ShowError("connect failed (socket %d, code %d)!\n", fd, s_errno);
		do_close(fd);
		return -1;
	}
	//Now the socket can be made non-blocking. [Skotlex]
	set_nonblocking(fd, 1);

	if (fd_max <= fd) fd_max = fd + 1;
	epoll_add(fd);

	create_session(fd, recv_to_fifo, send_from_fifo, default_func_parse);
	session[fd]->rdata_tick = last_tick;

	return fd;
}

int create_session(int fd, RecvFunc func_recv, SendFunc func_send, ParseFunc func_parse)
{
	CREATE(session[fd], struct socket_data, 1);
	CREATE(session[fd]->rdata, unsigned char, rfifo_size);
	CREATE(session[fd]->wdata, unsigned char, wfifo_size);
	session[fd]->max_rdata  = rfifo_size;
	session[fd]->max_wdata  = wfifo_size;
	session[fd]->func_recv  = func_recv;
	session[fd]->func_send  = func_send;
	session[fd]->func_parse = func_parse;
	// [perf] clear any residual send-worker state if this fd number is being reused
	if( socket_async_send )
		sendworker_reset(fd);
	return 0;
}

int delete_session(int fd)
{
	if (fd <= 0 || fd >= SOCKET_MAX)
		return -1;
	epoll_del(fd);
	if (session[fd]) {
		aFree(session[fd]->rdata);
		aFree(session[fd]->wdata);
		aFree(session[fd]->session_data);
		aFree(session[fd]);
		session[fd] = NULL;
	}
	return 0;
}

int realloc_fifo(int fd, unsigned int rfifo_size, unsigned int wfifo_size)
{
	if( !session_isValid(fd) )
		return 0;

	if( session[fd]->max_rdata != rfifo_size && session[fd]->rdata_size < rfifo_size) {
		RECREATE(session[fd]->rdata, unsigned char, rfifo_size);
		session[fd]->max_rdata  = rfifo_size;
	}

	if( session[fd]->max_wdata != wfifo_size && session[fd]->wdata_size < wfifo_size) {
		RECREATE(session[fd]->wdata, unsigned char, wfifo_size);
		session[fd]->max_wdata  = wfifo_size;
	}
	return 0;
}

int realloc_writefifo(int fd, size_t addition)
{
	size_t newsize;

	if( !session_isValid(fd) ) // might not happen
		return 0;

	if( session[fd]->wdata_size + addition  > session[fd]->max_wdata )
	{	// grow rule; grow in multiples of wfifo_size
		newsize = wfifo_size;
		while( session[fd]->wdata_size + addition > newsize ) newsize += newsize;
	}
	else if( session[fd]->max_wdata >= FIFOSIZE_SERVERLINK) {
		//Inter-server adjust. [Skotlex]
		if ((session[fd]->wdata_size+addition)*4 < session[fd]->max_wdata)
			newsize = session[fd]->max_wdata / 2;
		else
			return 0; //No change
	} else if( session[fd]->max_wdata > wfifo_size && (session[fd]->wdata_size+addition)*4 < session[fd]->max_wdata )
	{	// shrink rule, shrink by 2 when only a quater of the fifo is used, don't shrink below 4*addition
		newsize = session[fd]->max_wdata / 2;
	}
	else // no change
		return 0;

	RECREATE(session[fd]->wdata, unsigned char, newsize);
	session[fd]->max_wdata  = newsize;

	return 0;
}

int RFIFOSKIP(int fd, int len)
{
    struct socket_data *s;

	if ( !session_isActive(fd) )
		return 0;

	s = session[fd];

	if ( s->rdata_size < s->rdata_pos + len ) {
		//fprintf(stderr,"too many skip\n");
		//exit(1);
		//better than a COMPLETE program abort // TEST! :)
		ShowError("too many skip (%d) now skipped: %u (FD: %d)\n", len, (unsigned int)RFIFOREST(fd), fd);
		len = RFIFOREST(fd);
	}
	s->rdata_pos = s->rdata_pos + len;
	return 0;
}

int WFIFOSET(int fd, int len)
{
	size_t newreserve;
	struct socket_data* s = session[fd];

	if( !session_isValid(fd) || s->wdata == NULL )
		return 0;

	// we have written len bytes to the buffer already before calling WFIFOSET
	if(s->wdata_size+len > s->max_wdata)
	{	// actually there was a buffer overflow already
		uint32 ip = s->client_addr;
		ShowFatalError("socket: Buffer Overflow. Connection %d (%d.%d.%d.%d) has written %d bytes on a %u/%u bytes buffer.\n",
			fd, CONVIP(ip), len, (unsigned int)s->wdata_size, (unsigned int)s->max_wdata);
		ShowDebug("Likely command that caused it: 0x%x\n", (*(unsigned short*)(s->wdata + s->wdata_size)));
		// no other chance, make a better fifo model
		exit(1);
	}

	s->wdata_size += len;
	// always keep a wfifo_size reserve in the buffer
	// For inter-server connections, let the reserve be 1/4th of the link size.
	newreserve = s->wdata_size + (s->max_wdata >= FIFOSIZE_SERVERLINK ? FIFOSIZE_SERVERLINK / 4 : wfifo_size);

	// readfifo does not need to be realloced at all
	// Even the inter-server buffer may need reallocating! [Skotlex]
	realloc_writefifo(fd, newreserve);

#ifdef SEND_SHORTLIST
	send_shortlist_add_fd(fd);
#endif

	return 0;
}

int do_sendrecv(int next)
{
	int ret, n, i;

	last_tick = time(0);

	// PRESEND Timers run before do_sendrecv and can queue packets and/or set
	// sessions to eof. Flush queued data and close eof sessions.
	send_shortlist_do_sends();

	// Wait for readable sockets (replaces select). next is the ms until the
	// next timer; epoll_wait takes its timeout directly in milliseconds.
	// Level-triggered: any ready fd not fully drained this tick is reported
	// again next time, so a fifo recv that doesn't empty the socket is safe.
	ret = epoll_wait(epoll_fd, epoll_events, SOCKET_MAX, next);
	if( ret < 0 )
	{
		if( s_errno != EINTR )
			ShowError("do_sendrecv: epoll_wait failed (code %d)\n", s_errno);
		ret = 0; // nothing to dispatch this round
	}

	for( n = 0; n < ret; ++n )
	{
		i = epoll_events[n].data.fd;
		// A closed fd is auto-removed from epoll, so session[i] is the guard.
		// EPOLLHUP/EPOLLERR also land here; func_recv's recv() detects them.
		if( session[i] )
			session[i]->func_recv(i);
	}

	// POSTSEND Flush queued data and close eof sessions.
	send_shortlist_do_sends();

	return 0;
}

int do_parsepacket(void)
{
	int i;

	if( !recv_parse_shortlist )
	{	// [perf] fallback / A/B: original brute-scan of every session each tick
		for(i = 1; i < fd_max; i++)
		{
			if(!session[i])
				continue;

			// Skip the idle stall timeout for inter-server (s2s) links (client_addr==0): they can sit
			// idle far longer than stall_time between logins, and killing an ALIVE char<->map link makes
			// the char-server's auth (0x2b06) get lost in the reconnect gap -> the player who logs in then
			// "not authed within 30 seconds" -> intermittent disconnect on map entry (S., server-side).
			// A genuinely dead s2s link is still caught: periodic s2s writes (send_users_tochar etc.)
			// fail -> set_eof, and the reconnect timer re-links.
			if (session[i]->client_addr &&
				session[i]->rdata_tick && DIFF_TICK(last_tick, session[i]->rdata_tick) > stall_time) {
				ShowInfo ("Session #%d timed out\n", i);
				set_eof(i);
			}

			session[i]->func_parse(i);

			if(!session[i])
				continue;

			/* after parse, check client's RFIFO size to know if there is an invalid packet (too big and not parsed) */
			if (session[i]->rdata_size == rfifo_size && session[i]->max_rdata == rfifo_size) {
				set_eof(i);
				continue;
			}
			RFIFOFLUSH(i);
		}
		return 0;
	}

	// [perf] Shortlist path: parse ONLY fds that received data (queued by recv_to_fifo via epoll),
	// instead of indirect-calling func_parse + RFIFOFLUSH on every one of fd_max sessions each tick.
	{
		int n = 0;
		while( n < parse_shortlist_count )
		{
			i = parse_shortlist_array[n];
			if( !session[i] )
			{	// session gone -> drop the slot (swap with last)
				parse_shortlist_array[n] = parse_shortlist_array[--parse_shortlist_count];
				continue;
			}

			session[i]->func_parse(i);

			if( session[i] )
			{
				// invalid (oversized, unparseable) packet -> close
				if( session[i]->rdata_size == rfifo_size && session[i]->max_rdata == rfifo_size )
					set_eof(i);
				else
					RFIFOFLUSH(i);
			}

			// Keep the fd ONLY if it's still alive, not eof, and still holds unparsed data
			// (a partial/incomplete packet awaiting more bytes). recv_to_fifo re-adds it when
			// more data arrives, so removing a fully-drained fd never loses anything.
			if( session[i] && !session[i]->eof && RFIFOREST(i) > 0 )
			{
				++n;
			}
			else
			{
				if( session[i] )
					session[i]->in_parselist = 0;
				parse_shortlist_array[n] = parse_shortlist_array[--parse_shortlist_count];
			}
		}
	}

	// [perf 3b] Stall/idle timeout: shortlisted fds are only the active ones, so the per-fd timeout
	// can't live in the parse loop. Sweep ALL sessions on a ~1s throttle instead of every tick.
	{
		static unsigned int last_stall_sweep = 0;
		unsigned int now = gettick();
		if( DIFF_TICK(now, last_stall_sweep) >= 1000 )
		{
			last_stall_sweep = now;
			for(i = 1; i < fd_max; i++)
			{
				// Skip idle-stall for inter-server (s2s) links (client_addr==0) -- see the note in the
				// brute-scan path above: killing an alive char<->map link on idle loses the map-entry
				// auth and disconnects the player ("not authed within 30 seconds"). (S., server-side)
				if( session[i] && session[i]->client_addr && session[i]->rdata_tick
					&& DIFF_TICK(last_tick, session[i]->rdata_tick) > stall_time )
				{
					ShowInfo("Session #%d timed out\n", i);
					set_eof(i);
				}
			}
		}
	}
	return 0;
}

//////////////////////////////
#ifndef MINICORE
//////////////////////////////
// IP rules and DDoS protection

typedef struct _connect_history {
	struct _connect_history* next;
	uint32 ip;
	uint32 tick;
	int count;
	unsigned ddos : 1;
} ConnectHistory;

typedef struct _access_control {
	uint32 ip;
	uint32 mask;
} AccessControl;

enum _aco {
	ACO_DENY_ALLOW,
	ACO_ALLOW_DENY,
	ACO_MUTUAL_FAILURE
};

static AccessControl* access_allow = NULL;
static AccessControl* access_deny = NULL;
static int access_order    = ACO_DENY_ALLOW;
static int access_allownum = 0;
static int access_denynum  = 0;
static int access_debug    = 0;
static int ddos_count      = 10;
static int ddos_interval   = 3*1000;
static int ddos_autoreset  = 10*60*1000;
/// Connection history, an array of linked lists.
/// The array's index for any ip is ip&0xFFFF
static ConnectHistory* connect_history[0x10000];

static int connect_check_(uint32 ip);

/// Verifies if the IP can connect. (with debug info)
/// @see connect_check_()
static int connect_check(uint32 ip)
{
	int result = connect_check_(ip);
	if( access_debug ) {
		ShowMessage("connect_check: Connection from %d.%d.%d.%d %s\n", CONVIP(ip),result ? "allowed." : "denied!");
	}
	return result;
}

/// Verifies if the IP can connect.
///  0      : Connection Rejected
///  1 or 2 : Connection Accepted
static int connect_check_(uint32 ip)
{
	ConnectHistory* hist = connect_history[ip&0xFFFF];
	int i;
	int is_allowip = 0;
	int is_denyip = 0;
	int connect_ok = 0;

	// Search the allow list
	for( i=0; i < access_allownum; ++i ){
		if( (ip & access_allow[i].mask) == (access_allow[i].ip & access_allow[i].mask) ){
			if( access_debug ){
				ShowMessage("connect_check: Found match from allow list:%d.%d.%d.%d IP:%d.%d.%d.%d Mask:%d.%d.%d.%d\n",
					CONVIP(ip),
					CONVIP(access_allow[i].ip),
					CONVIP(access_allow[i].mask));
			}
			is_allowip = 1;
			break;
		}
	}
	// Search the deny list
	for( i=0; i < access_denynum; ++i ){
		if( (ip & access_deny[i].mask) == (access_deny[i].ip & access_deny[i].mask) ){
			if( access_debug ){
				ShowMessage("connect_check: Found match from deny list:%d.%d.%d.%d IP:%d.%d.%d.%d Mask:%d.%d.%d.%d\n",
					CONVIP(ip),
					CONVIP(access_deny[i].ip),
					CONVIP(access_deny[i].mask));
			}
			is_denyip = 1;
			break;
		}
	}
	// Decide connection status
	//  0 : Reject
	//  1 : Accept
	//  2 : Unconditional Accept (accepts even if flagged as DDoS)
	switch(access_order) {
	case ACO_DENY_ALLOW:
	default:
		if( is_denyip )
			connect_ok = 0; // Reject
		else if( is_allowip )
			connect_ok = 2; // Unconditional Accept
		else
			connect_ok = 1; // Accept
		break;
	case ACO_ALLOW_DENY:
		if( is_allowip )
			connect_ok = 2; // Unconditional Accept
		else if( is_denyip )
			connect_ok = 0; // Reject
		else
			connect_ok = 1; // Accept
		break;
	case ACO_MUTUAL_FAILURE:
		if( is_allowip && !is_denyip )
			connect_ok = 2; // Unconditional Accept
		else
			connect_ok = 0; // Reject
		break;
	}

	// Inspect connection history
	while( hist ) {
		if( ip == hist->ip )
		{// IP found
			if( hist->ddos )
			{// flagged as DDoS
				return (connect_ok == 2 ? 1 : 0);
			} else if( DIFF_TICK(gettick(),hist->tick) < ddos_interval )
			{// connection within ddos_interval
				hist->tick = gettick();
				if( hist->count++ >= ddos_count )
				{// DDoS attack detected
					hist->ddos = 1;
					ShowWarning("connect_check: DDoS Attack detected from %d.%d.%d.%d!\n", CONVIP(ip));
					return (connect_ok == 2 ? 1 : 0);
				}
				return connect_ok;
			} else
			{// not within ddos_interval, clear data
				hist->tick  = gettick();
				hist->count = 0;
				return connect_ok;
			}
		}
		hist = hist->next;
	}
	// IP not found, add to history
	CREATE(hist, ConnectHistory, 1);
	memset(hist, 0, sizeof(ConnectHistory));
	hist->ip   = ip;
	hist->tick = gettick();
	hist->next = connect_history[ip&0xFFFF];
	connect_history[ip&0xFFFF] = hist;
	return connect_ok;
}

/// Timer function.
/// Deletes old connection history records.
static int connect_check_clear(int tid, unsigned int tick, intptr_t id, intptr_t data)
{
	int i;
	int clear = 0;
	int list  = 0;
	ConnectHistory root;
	ConnectHistory* prev_hist;
	ConnectHistory* hist;

	for( i=0; i < 0x10000 ; ++i ){
		prev_hist = &root;
		root.next = hist = connect_history[i];
		while( hist ){
			if( (!hist->ddos && DIFF_TICK(tick,hist->tick) > ddos_interval*3) ||
					(hist->ddos && DIFF_TICK(tick,hist->tick) > ddos_autoreset) )
			{// Remove connection history
				prev_hist->next = hist->next;
				aFree(hist);
				hist = prev_hist->next;
				clear++;
			} else {
				prev_hist = hist;
				hist = hist->next;
			}
			list++;
		}
		connect_history[i] = root.next;
	}
	if( access_debug ){
		ShowMessage("connect_check_clear: Cleared %d of %d from IP list.\n", clear, list);
	}
	return list;
}

/// Parses the ip address and mask and puts it into acc.
/// Returns 1 is successful, 0 otherwise.
int access_ipmask(const char* str, AccessControl* acc)
{
	uint32 ip;
	uint32 mask;
	unsigned int a[4];
	unsigned int m[4];
	int n;

	if( strcmp(str,"all") == 0 ) {
		ip   = 0;
		mask = 0;
	} else {
		if( ((n=sscanf(str,"%u.%u.%u.%u/%u.%u.%u.%u",a,a+1,a+2,a+3,m,m+1,m+2,m+3)) != 8 && // not an ip + standard mask
				(n=sscanf(str,"%u.%u.%u.%u/%u",a,a+1,a+2,a+3,m)) != 5 && // not an ip + bit mask
				(n=sscanf(str,"%u.%u.%u.%u",a,a+1,a+2,a+3)) != 4 ) || // not an ip
				a[0] > 255 || a[1] > 255 || a[2] > 255 || a[3] > 255 || // invalid ip
				(n == 8 && (m[0] > 255 || m[1] > 255 || m[2] > 255 || m[3] > 255)) || // invalid standard mask
				(n == 5 && m[0] > 32) ){ // invalid bit mask
			return 0;
		}
		ip = (uint32)(a[0] | (a[1] << 8) | (a[2] << 16) | (a[3] << 24));
		if( n == 8 )
		{// standard mask
			mask = (uint32)(a[0] | (a[1] << 8) | (a[2] << 16) | (a[3] << 24));
		} else if( n == 5 )
		{// bit mask
			mask = 0;
			while( m[0] ){
				mask = (mask >> 1) | 0x80000000;
				--m[0];
			}
			mask = ntohl(mask);
		} else
		{// just this ip
			mask = 0xFFFFFFFF;
		}
	}
	if( access_debug ){
		ShowMessage("access_ipmask: Loaded IP:%d.%d.%d.%d mask:%d.%d.%d.%d\n", CONVIP(ip), CONVIP(mask));
	}
	acc->ip   = ip;
	acc->mask = mask;
	return 1;
}
//////////////////////////////
#endif
//////////////////////////////

int socket_config_read(const char* cfgName)
{
	char line[1024],w1[1024],w2[1024];
	FILE *fp;

	fp = fopen(cfgName, "r");
	if(fp == NULL) {
		ShowError("File not found: %s\n", cfgName);
		return 1;
	}

	while(fgets(line, sizeof(line), fp))
	{
		if(line[0] == '/' && line[1] == '/')
			continue;
		if(sscanf(line, "%[^:]: %[^\r\n]", w1, w2) != 2)
			continue;

		if (!strcmpi(w1, "stall_time"))
			stall_time = atoi(w2);
#ifndef MINICORE
		else if (!strcmpi(w1, "enable_ip_rules")) {
			ip_rules = config_switch(w2);
		} else if (!strcmpi(w1, "order")) {
			if (!strcmpi(w2, "deny,allow"))
				access_order = ACO_DENY_ALLOW;
			else if (!strcmpi(w2, "allow,deny"))
				access_order = ACO_ALLOW_DENY;
			else if (!strcmpi(w2, "mutual-failure"))
				access_order = ACO_MUTUAL_FAILURE;
		} else if (!strcmpi(w1, "allow")) {
			RECREATE(access_allow, AccessControl, access_allownum+1);
			if (access_ipmask(w2, &access_allow[access_allownum]))
				++access_allownum;
			else
				ShowError("socket_config_read: Invalid ip or ip range '%s'!\n", line);
		} else if (!strcmpi(w1, "deny")) {
			RECREATE(access_deny, AccessControl, access_denynum+1);
			if (access_ipmask(w2, &access_deny[access_denynum]))
				++access_denynum;
			else
				ShowError("socket_config_read: Invalid ip or ip range '%s'!\n", line);
		}
		else if (!strcmpi(w1,"ddos_interval"))
			ddos_interval = atoi(w2);
		else if (!strcmpi(w1,"ddos_count"))
			ddos_count = atoi(w2);
		else if (!strcmpi(w1,"ddos_autoreset"))
			ddos_autoreset = atoi(w2);
		else if (!strcmpi(w1,"debug"))
			access_debug = config_switch(w2);
#endif
		else if (!strcmpi(w1, "import"))
			socket_config_read(w2);
	}

	fclose(fp);
	return 0;
}


void socket_final(void)
{
	int i;
	sendworker_final(); // stop the send thread (no-op if never started) before tearing down sessions
#ifndef MINICORE
	ConnectHistory* hist;
	ConnectHistory* next_hist;

	for( i=0; i < 0x10000; ++i ){
		hist = connect_history[i];
		while( hist ){
			next_hist = hist->next;
			aFree(hist);
			hist = next_hist;
		}
	}
	if( access_allow )
		aFree(access_allow);
	if( access_deny )
		aFree(access_deny);
#endif

	for (i = 1; i < fd_max; i++) {
		if(session[i])
			delete_session(i);
	}

	// session[0] _~[f[^
	aFree(session[0]->rdata);
	aFree(session[0]->wdata);
	aFree(session[0]);

	if( epoll_events )
		aFree(epoll_events);
	if( epoll_fd != -1 )
		close(epoll_fd);
}

/// Closes a socket.
void do_close(int fd)
{
	flush_fifo(fd); // Try to send what's left (hands off to the worker when async)
	// [perf] async send: make the worker let go of this fd (drop+best-effort flush
	// its queue, wait out any in-flight send) BEFORE we close/reuse it, so a send
	// can never land on a closed or recycled fd.
	if( socket_async_send )
		sendworker_release(fd);
	shutdown(fd, SHUT_RDWR); // Disallow further reads/writes
	closesocket(fd); // We don't really care if these closing functions return an error, we are just shutting down and not reusing this socket.
	if (session[fd]) delete_session(fd);
}

/// Retrieve local ips in host byte order.
/// Uses loopback is no address is found.
int socket_getips(uint32* ips, int max)
{
	int num = 0;

	if( ips == NULL || max <= 0 )
		return 0;

	{
		int pos;
		int fd;
		char buf[2*16*sizeof(struct ifreq)];
		struct ifconf ic;
		struct ifreq* ir;
		struct sockaddr_in* a;
		u_long ad;

		fd = socket(AF_INET, SOCK_STREAM, 0);

		// The ioctl call will fail with Invalid Argument if there are more
		// interfaces than will fit in the buffer
		ic.ifc_len = sizeof(buf);
		ic.ifc_buf = buf;
		if( ioctl(fd, SIOCGIFCONF, &ic) == -1 )
		{
			ShowError("socket_getips: SIOCGIFCONF failed!\n");
			return 0;
		}
		else
		{
			for( pos=0; pos < ic.ifc_len && num < max; )
			{
				ir = (struct ifreq*)(buf+pos);
				a = (struct sockaddr_in*) &(ir->ifr_addr);
				if( a->sin_family == AF_INET ){
					ad = ntohl(a->sin_addr.s_addr);
					if( ad != INADDR_LOOPBACK && ad != INADDR_ANY )
						ips[num++] = (uint32)ad;
				}
				pos += sizeof(struct ifreq);
			}
		}
		closesocket(fd);
	}

	// Use loopback if no ips are found
	if( num == 0 )
		ips[num++] = (uint32)INADDR_LOOPBACK;

	return num;
}

void socket_init(void)
{
	char *SOCKET_CONF_FILENAME = "conf/packet_athena.conf";

	// Get initial local ips
	naddr_ = socket_getips(addr_,16);

	// Raise the open-file limit so SOCKET_MAX sockets are actually usable
	// (the OS default is often 1024 — the old select() ceiling).
#ifdef HAVE_SETRLIMIT
	{
		struct rlimit rl;
		if( getrlimit(RLIMIT_NOFILE, &rl) == 0 && rl.rlim_cur < (rlim_t)SOCKET_MAX )
		{
			rl.rlim_cur = (rlim_t)SOCKET_MAX;
			if( rl.rlim_max < (rlim_t)SOCKET_MAX )
				rl.rlim_max = (rlim_t)SOCKET_MAX;
			if( setrlimit(RLIMIT_NOFILE, &rl) != 0 )
				ShowWarning("socket_init: could not raise the open-file limit to %d; connections stay capped by the OS limit.\n", SOCKET_MAX);
		}
	}
#endif

	// Create the epoll instance and its event buffer (replaces the select fd_set).
	epoll_fd = epoll_create1(0);
	if( epoll_fd == -1 )
	{
		ShowFatalError("socket_init: epoll_create1 failed (code %d)!\n", errno);
		exit(1);
	}
	CREATE(epoll_events, struct epoll_event, SOCKET_MAX);

	socket_config_read(SOCKET_CONF_FILENAME);

	// initialise last send-receive tick
	last_tick = time(0);

	// session[0] is now currently used for disconnected sessions of the map server, and as such,
	// should hold enough buffer (it is a vacuum so to speak) as it is never flushed. [Skotlex]
	create_session(0, null_recv, null_send, null_parse);

#ifndef MINICORE
	// Delete old connection history every 5 minutes
	memset(connect_history, 0, sizeof(connect_history));
	add_timer_func_list(connect_check_clear, "connect_check_clear");
	add_timer_interval(gettick()+1000, connect_check_clear, 0, 0, 5*60*1000);
#endif
}


int session_isValid(int fd)
{
	return ( (fd > 0) && (fd < SOCKET_MAX) && (session[fd] != NULL) );
}

int session_isActive(int fd)
{
	return ( session_isValid(fd) && !session[fd]->eof );
}

// Resolves hostname into a numeric ip.
uint32 host2ip(const char* hostname)
{
	struct hostent* h = gethostbyname(hostname);
	return (h != NULL) ? ntohl(*(uint32*)h->h_addr) : 0;
}

// Converts a numeric ip into a dot-formatted string.
// Result is placed either into a user-provided buffer or a static system buffer.
const char* ip2str(uint32 ip, char ip_str[16])
{
	struct in_addr addr;
	addr.s_addr = htonl(ip);
	return (ip_str == NULL) ? inet_ntoa(addr) : strncpy(ip_str, inet_ntoa(addr), 16);
}

// Converts a dot-formatted ip string into a numeric ip.
uint32 str2ip(const char* ip_str)
{
	return ntohl(inet_addr(ip_str));
}

// Reorders bytes from network to little endian (Windows).
// Neccessary for sending port numbers to the RO client until Gravity notices that they forgot ntohs() calls.
uint16 ntows(uint16 netshort)
{
	return ((netshort & 0xFF) << 8) | ((netshort & 0xFF00) >> 8);
}

#ifdef SEND_SHORTLIST
// Add a fd to the shortlist so that it'll be recognized as a fd that needs
// sending or eof handling.
void send_shortlist_add_fd(int fd)
{
	if( !session_isValid(fd) )
		return;
	if( session[fd]->in_shortlist )
		return;// Refuse to add duplicate FDs to the shortlist

	session[fd]->in_shortlist = 1;
	// Add to the end of the shortlist array.
	send_shortlist_array[send_shortlist_count++] = fd;
}

// Do pending network sends and eof handling from the shortlist.
void send_shortlist_do_sends()
{
	int i = 0;

	while( i < send_shortlist_count )
	{
		int fd = send_shortlist_array[i];

		// If this session still exists, perform send operations on it and
		// check for the eof state.
		if( session[fd] )
		{
			// Send data. (Coalescing is NOT done here — it was timer-based and
			// throttled the drain of a window-limited remote client, breaking
			// map entry. It now lives in the send worker, which combines queued
			// chunks into one send() with no added delay. See send_worker.c.)
			if( session[fd]->wdata_size )
				session[fd]->func_send(fd);

			// If it's been marked as eof, call the parse func on it so that
			// the socket will be immediately closed.
			if( session[fd] && session[fd]->eof )
				session[fd]->func_parse(fd);

			// If the session still exists, is not eof and has things left to
			// be sent from it we'll keep it in the shortlist (flag stays set).
			if( session[fd] && !session[fd]->eof && session[fd]->wdata_size )
			{
				++i;
				continue;
			}
		}

		// Remove fd from the shortlist: clear its flag (if the session lives)
		// and move the last entry into this slot.
		if( session[fd] )
			session[fd]->in_shortlist = 0;
		send_shortlist_array[i] = send_shortlist_array[--send_shortlist_count];
	}
}
#endif
