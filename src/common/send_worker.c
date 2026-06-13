// [perf] Off-thread socket send worker. See send_worker.h for the contract.
//
// Producer = game thread (sendworker_send copies bytes into an owned chunk and
// queues it). Consumer = this thread (drains each fd's chunk FIFO via send()).
// All shared state is under g_mtx; the send() syscalls run OUTSIDE the lock so
// the game thread is never blocked behind the kernel TCP stack. Per-fd state is
// a stable fd-indexed array, decoupled from the session lifetime. Chunks use raw
// malloc/free (cross-thread; never the game allocator), exactly like log_async.
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <sys/socket.h>

#include "send_worker.h"
#include "socket.h"   // SOCKET_MAX

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif

#define SW_MAX SOCKET_MAX
#define SW_RETRY_MS 5   // delay before re-trying an EAGAIN (backpressured) fd

struct sw_chunk {
	struct sw_chunk *next;
	size_t off;   // bytes already sent from this chunk
	size_t len;
	unsigned char data[];
};

struct sw_fd {
	struct sw_chunk *head, *tail;   // pending FIFO
	unsigned char in_ready;         // queued in g_ready (dedup)
	unsigned char in_use;           // worker is mid-send on this fd
	unsigned char closing;          // game thread is closing it; worker must let go
	unsigned char backlogged;       // EAGAIN remainder, pending a timed retry
};

static struct sw_fd sw[SW_MAX];
static int g_ready[SW_MAX];    int g_ready_n = 0;     // fds with work to do now
static int g_backlog[SW_MAX];  int g_backlog_n = 0;   // fds awaiting EAGAIN retry

static pthread_mutex_t g_mtx     = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  g_work_cv = PTHREAD_COND_INITIALIZER;  // worker wakes on new work
static pthread_cond_t  g_close_cv= PTHREAD_COND_INITIALIZER;  // close() waits for in_use to clear
static pthread_t       g_thread;
static int             g_running = 0;

// caller holds g_mtx
static void ready_push(int fd)
{
	if( !sw[fd].in_ready && !sw[fd].backlogged && g_ready_n < SW_MAX ) {
		g_ready[g_ready_n++] = fd;
		sw[fd].in_ready = 1;
	}
}

static void free_chain(struct sw_chunk *c)
{
	while( c ) { struct sw_chunk *d = c; c = c->next; free(d); }
}

static void *sw_main(void *unused)
{
	(void)unused;
	pthread_mutex_lock(&g_mtx);
	while( 1 )
	{
		while( g_running && g_ready_n == 0 )
		{
			if( g_backlog_n > 0 ) {
				// retry backpressured fds after a short delay (no busy-spin)
				struct timespec ts; int k;
				clock_gettime(CLOCK_REALTIME, &ts);
				ts.tv_nsec += SW_RETRY_MS * 1000000L;
				if( ts.tv_nsec >= 1000000000L ) { ts.tv_sec++; ts.tv_nsec -= 1000000000L; }
				pthread_cond_timedwait(&g_work_cv, &g_mtx, &ts);
				for( k = 0; k < g_backlog_n; k++ ) {
					int bfd = g_backlog[k];
					sw[bfd].backlogged = 0;
					if( sw[bfd].head && !sw[bfd].in_ready && g_ready_n < SW_MAX ) {
						g_ready[g_ready_n++] = bfd;
						sw[bfd].in_ready = 1;
					}
				}
				g_backlog_n = 0;
			} else {
				pthread_cond_wait(&g_work_cv, &g_mtx);
			}
		}
		if( !g_running && g_ready_n == 0 )
			break;

		{
			int fd = g_ready[--g_ready_n];
			struct sw_chunk *list, *rem = NULL;
			int eagain = 0, dead = 0;
			sw[fd].in_ready = 0;
			if( sw[fd].closing || sw[fd].head == NULL )
				continue;

			// check out the whole queue and send it outside the lock
			list = sw[fd].head;
			sw[fd].head = sw[fd].tail = NULL;
			sw[fd].in_use = 1;
			pthread_mutex_unlock(&g_mtx);

			while( list ) {
				struct sw_chunk *c = list;
				while( c->off < c->len ) {
					ssize_t n = send(fd, c->data + c->off, c->len - c->off, MSG_NOSIGNAL);
					if( n > 0 )                    c->off += (size_t)n;
					else if( n < 0 && errno == EINTR ) continue;
					else if( n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK) ) { eagain = 1; break; }
					else                           { dead = 1; break; } // EPIPE/ECONNRESET/EBADF
				}
				if( eagain && c->off < c->len ) {   // keep c and everything after it
					rem = list;
					list = NULL;
					break;
				}
				list = c->next;
				free(c);
				if( dead ) { free_chain(list); list = NULL; break; }
			}

			pthread_mutex_lock(&g_mtx);
			sw[fd].in_use = 0;
			if( rem && !sw[fd].closing && !dead ) {
				// prepend the unsent remainder, schedule a delayed retry
				struct sw_chunk *t = rem;
				while( t->next ) t = t->next;
				t->next = sw[fd].head;
				sw[fd].head = rem;
				if( sw[fd].tail == NULL ) sw[fd].tail = t;
				if( !sw[fd].backlogged && g_backlog_n < SW_MAX ) {
					sw[fd].backlogged = 1;
					g_backlog[g_backlog_n++] = fd;
				}
			} else if( rem ) {
				free_chain(rem);
			}
			if( sw[fd].closing )
				pthread_cond_broadcast(&g_close_cv);
		}
	}
	pthread_mutex_unlock(&g_mtx);
	return NULL;
}

void sendworker_send(int fd, const unsigned char *buf, size_t len)
{
	struct sw_chunk *c;
	if( fd <= 0 || fd >= SW_MAX || len == 0 )
		return;
	c = (struct sw_chunk*)malloc(sizeof(struct sw_chunk) + len);
	if( c == NULL )
		return; // OOM: drop (parity with a failed send on a full buffer)
	c->next = NULL;
	c->off  = 0;
	c->len  = len;
	memcpy(c->data, buf, len);

	pthread_mutex_lock(&g_mtx);
	if( sw[fd].closing ) {            // being torn down: drop
		pthread_mutex_unlock(&g_mtx);
		free(c);
		return;
	}
	if( sw[fd].tail ) sw[fd].tail->next = c;
	else              sw[fd].head = c;
	sw[fd].tail = c;
	if( !sw[fd].in_ready && !sw[fd].backlogged ) {  // already queued? backlog retry will catch it
		ready_push(fd);
		pthread_cond_signal(&g_work_cv);
	}
	pthread_mutex_unlock(&g_mtx);
}

void sendworker_release(int fd)
{
	struct sw_chunk *c;
	if( fd <= 0 || fd >= SW_MAX )
		return;
	pthread_mutex_lock(&g_mtx);
	sw[fd].closing = 1;
	c = sw[fd].head;                 // detach everything not in-flight
	sw[fd].head = sw[fd].tail = NULL;
	while( sw[fd].in_use )           // wait out an in-flight send on this fd
		pthread_cond_wait(&g_close_cv, &g_mtx);
	pthread_mutex_unlock(&g_mtx);
	// best-effort final flush of what the worker hadn't sent yet (socket is being
	// closed anyway; non-blocking send won't stall), then discard.
	while( c ) {
		struct sw_chunk *d = c; c = c->next;
		while( d->off < d->len ) {
			ssize_t n = send(fd, d->data + d->off, d->len - d->off, MSG_NOSIGNAL);
			if( n > 0 ) d->off += (size_t)n; else break;
		}
		free(d);
	}
}

void sendworker_reset(int fd)
{
	struct sw_chunk *c;
	if( fd <= 0 || fd >= SW_MAX )
		return;
	pthread_mutex_lock(&g_mtx);
	c = sw[fd].head;
	sw[fd].head = sw[fd].tail = NULL;
	sw[fd].closing = 0;
	sw[fd].in_use  = 0;
	pthread_mutex_unlock(&g_mtx);
	free_chain(c);
}

void sendworker_init(void)
{
	pthread_mutex_lock(&g_mtx);
	if( g_running ) { pthread_mutex_unlock(&g_mtx); return; }
	g_running = 1;
	pthread_mutex_unlock(&g_mtx);
	if( pthread_create(&g_thread, NULL, sw_main, NULL) != 0 ) {
		pthread_mutex_lock(&g_mtx);
		g_running = 0;
		pthread_mutex_unlock(&g_mtx);
	}
}

void sendworker_final(void)
{
	int i;
	pthread_mutex_lock(&g_mtx);
	if( !g_running ) { pthread_mutex_unlock(&g_mtx); return; }
	g_running = 0;
	pthread_cond_broadcast(&g_work_cv);
	pthread_mutex_unlock(&g_mtx);
	pthread_join(g_thread, NULL);
	for( i = 0; i < SW_MAX; i++ ) {
		free_chain(sw[i].head);
		sw[i].head = sw[i].tail = NULL;
	}
}
