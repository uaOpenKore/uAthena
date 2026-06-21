// [perf] Off-thread socket send worker. See send_worker.h for the contract.
//
// Producer = game thread (sendworker_send copies bytes into an owned chunk and
// queues it). Consumer = this thread (drains each fd's chunk FIFO via send()).
// All shared state is under g_mtx; the send() syscalls run OUTSIDE the lock so
// the game thread is never blocked behind the kernel TCP stack. Per-fd state is
// a stable fd-indexed array, decoupled from the session lifetime. Chunks use raw
// malloc/free (cross-thread; never the game allocator), exactly like log_async.
//
// Send coalescing (socket_send_coalesce_ms > 0): a lone *sub-segment* dribble for
// an fd is HELD for up to the configured window so the small packets that pile up
// during the window go out as ONE send() (fewer syscalls / TCP segments / qdisc
// trips on crowded maps -- WoE). Anything that reaches ~1 TCP segment, and every
// EAGAIN drain, flushes immediately, so a map-entry/spawn burst is NEVER throttled
// (the bug the old game-loop timer coalescing caused). The window only delays when
// to START draining freshly-queued small data; it never throttles an in-progress
// drain.
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
#define SW_RETRY_MS 5      // delay before re-trying an EAGAIN (backpressured) fd
#define SW_COALESCE_BYTES 1400  // >= ~1 TCP segment: flush now, never wait the window

struct sw_chunk {
	struct sw_chunk *next;
	size_t off;   // bytes already sent from this chunk
	size_t len;
	size_t cap;   // [perf 5a] allocated capacity of data[] (for the recycling pool)
	unsigned char data[];
};

// [perf 5a] Chunk recycling pool. The worker allocates one chunk per hand-off and
// frees it after the send; at high send rates this is a malloc/free on every packet.
// A small stack of recycled SW_SLAB-sized buffers serves the common (small) case
// without touching the allocator. Chunks larger than a slab are never pooled (malloc
// /free directly). The pool has its OWN lock so it never widens g_mtx contention, and
// is touched by both the producer (sendworker_send) and the worker thread. Gated by
// sw_pool_enabled so testers can A/B it (pool off == the original malloc/free path).
#define SW_SLAB         4096    // pooled buffer size; covers a typical accumulated wdata flush
#define SW_FREELIST_MAX 512     // cap idle pooled buffers (~2MB) — live chunks are unbounded
static struct sw_chunk *g_pool = NULL;
static int              g_pool_n = 0;
static int              sw_pool_enabled = 1;   // 1 = recycle (default); 0 = plain malloc/free
static pthread_mutex_t  g_pool_mtx = PTHREAD_MUTEX_INITIALIZER;

void sendworker_set_pool(int on)
{
	pthread_mutex_lock(&g_pool_mtx);
	sw_pool_enabled = on;
	pthread_mutex_unlock(&g_pool_mtx);
}

// Allocate a chunk able to hold len data bytes. Caller sets next/off/len and fills
// data[]. Returns NULL only on OOM. cap >= len always.
static struct sw_chunk *chunk_alloc(size_t len)
{
	struct sw_chunk *c = NULL;
	size_t cap;
	int pool;

	pthread_mutex_lock(&g_pool_mtx);
	pool = sw_pool_enabled;
	if( pool && len <= SW_SLAB && g_pool ) {
		c = g_pool;
		g_pool = c->next;
		g_pool_n--;
	}
	pthread_mutex_unlock(&g_pool_mtx);
	if( c )
		return c;   // recycled (cap == SW_SLAB >= len)

	cap = (pool && len <= SW_SLAB) ? SW_SLAB : len;   // pool off -> exact len (parity with old path)
	c = (struct sw_chunk*)malloc(sizeof(struct sw_chunk) + cap);
	if( c == NULL )
		return NULL;
	c->cap = cap;
	return c;
}

// Return a chunk to the pool (if a slab and there's room) or to the allocator.
static void chunk_free(struct sw_chunk *c)
{
	if( c == NULL )
		return;
	if( c->cap == SW_SLAB ) {	// only recycle true slab buffers; oversized (coalesced) chunks are freed
		pthread_mutex_lock(&g_pool_mtx);
		if( sw_pool_enabled && g_pool_n < SW_FREELIST_MAX ) {
			c->next = g_pool;
			g_pool = c;
			g_pool_n++;
			pthread_mutex_unlock(&g_pool_mtx);
			return;
		}
		pthread_mutex_unlock(&g_pool_mtx);
	}
	free(c);
}

// Free everything parked in the pool (shutdown / A/B-off drain).
static void pool_drain(void)
{
	struct sw_chunk *c;
	pthread_mutex_lock(&g_pool_mtx);
	c = g_pool;
	g_pool = NULL;
	g_pool_n = 0;
	pthread_mutex_unlock(&g_pool_mtx);
	while( c ) { struct sw_chunk *d = c; c = c->next; free(d); }
}

struct sw_fd {
	struct sw_chunk *head, *tail;   // pending FIFO
	struct timespec due;            // when a deferred fd becomes ready (abs, CLOCK_REALTIME)
	unsigned char in_ready;         // queued in g_ready (drain now); dedup
	unsigned char in_use;           // worker is mid-send on this fd
	unsigned char closing;          // game thread is closing it; worker must let go
	unsigned char deferred;         // queued in g_defer awaiting .due; dedup
	unsigned char defer_backlog;    // deferral reason: 1 = EAGAIN retry, 0 = coalesce window
};

static struct sw_fd sw[SW_MAX];
static int g_ready[SW_MAX];   int g_ready_n = 0;   // fds with work to do now
static int g_defer[SW_MAX];   int g_defer_n = 0;   // fds awaiting a deadline (coalesce / EAGAIN)

static pthread_mutex_t g_mtx     = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  g_work_cv = PTHREAD_COND_INITIALIZER;  // worker wakes on new work
static pthread_cond_t  g_close_cv= PTHREAD_COND_INITIALIZER;  // close() waits for in_use to clear
static pthread_t       g_thread;
static int             g_running = 0;
static int             sw_coalesce_ms = 0;  // [perf] 0/neg = off; >0 = flush window in ms (under g_mtx)

void sendworker_set_coalesce(int ms)
{
	pthread_mutex_lock(&g_mtx);
	sw_coalesce_ms = ms;
	pthread_mutex_unlock(&g_mtx);
}

// --- small time helpers (CLOCK_REALTIME, to match pthread_cond_timedwait) -----
static struct timespec now_plus_ms(int ms)
{
	struct timespec ts;
	clock_gettime(CLOCK_REALTIME, &ts);
	ts.tv_nsec += (long)ms * 1000000L;
	ts.tv_sec  += ts.tv_nsec / 1000000000L;
	ts.tv_nsec %= 1000000000L;
	return ts;
}
static int ts_ge(struct timespec a, struct timespec b)  // a >= b ?
{
	return a.tv_sec != b.tv_sec ? a.tv_sec > b.tv_sec : a.tv_nsec >= b.tv_nsec;
}
static int ts_lt(struct timespec a, struct timespec b)  // a < b ?
{
	return a.tv_sec != b.tv_sec ? a.tv_sec < b.tv_sec : a.tv_nsec < b.tv_nsec;
}

// caller holds g_mtx
static void ready_push(int fd)
{
	if( !sw[fd].in_ready && !sw[fd].deferred && g_ready_n < SW_MAX ) {
		g_ready[g_ready_n++] = fd;
		sw[fd].in_ready = 1;
	}
}

// caller holds g_mtx; caller has already set sw[fd].due and sw[fd].defer_backlog
static void defer_add(int fd)
{
	if( !sw[fd].deferred && g_defer_n < SW_MAX ) {
		sw[fd].deferred = 1;
		g_defer[g_defer_n++] = fd;
	}
}

// caller holds g_mtx
static void defer_remove(int fd)
{
	int i;
	if( !sw[fd].deferred )
		return;
	sw[fd].deferred = 0;
	for( i = 0; i < g_defer_n; i++ )
		if( g_defer[i] == fd ) { g_defer[i] = g_defer[--g_defer_n]; return; }
}

// caller holds g_mtx; total unsent bytes queued for fd
static size_t qbytes_of(int fd)
{
	size_t b = 0; struct sw_chunk *c;
	for( c = sw[fd].head; c; c = c->next ) b += c->len - c->off;
	return b;
}

// caller holds g_mtx; fd has head data and is idle (not in_use/in_ready/deferred):
// drain it now if coalescing is off or it already fills a segment, else arm the
// coalesce window so more small packets can pile in before one send().
static void sched_fd(int fd)
{
	if( sw_coalesce_ms <= 0 || qbytes_of(fd) >= SW_COALESCE_BYTES ) {
		ready_push(fd);
	} else {
		sw[fd].defer_backlog = 0;
		sw[fd].due = now_plus_ms(sw_coalesce_ms);
		defer_add(fd);
	}
	pthread_cond_signal(&g_work_cv);
}

static void free_chain(struct sw_chunk *c)
{
	while( c ) { struct sw_chunk *d = c; c = c->next; chunk_free(d); }
}

static void *sw_main(void *unused)
{
	(void)unused;
	pthread_mutex_lock(&g_mtx);
	while( 1 )
	{
		while( g_running && g_ready_n == 0 )
		{
			if( g_defer_n > 0 ) {
				// sleep until the earliest deferred deadline (no busy-spin), then
				// promote every fd whose coalesce window / EAGAIN retry has elapsed.
				struct timespec ts = sw[g_defer[0]].due, now;
				int k, r, w = 0;
				for( k = 1; k < g_defer_n; k++ )
					if( ts_lt(sw[g_defer[k]].due, ts) ) ts = sw[g_defer[k]].due;
				pthread_cond_timedwait(&g_work_cv, &g_mtx, &ts);
				clock_gettime(CLOCK_REALTIME, &now);
				for( r = 0; r < g_defer_n; r++ ) {
					int dfd = g_defer[r];
					if( ts_ge(now, sw[dfd].due) ) {
						sw[dfd].deferred = 0;
						if( sw[dfd].head && !sw[dfd].in_ready && !sw[dfd].in_use && !sw[dfd].closing )
							ready_push(dfd);
					} else {
						g_defer[w++] = dfd;   // not due yet: keep
					}
				}
				g_defer_n = w;
			} else {
				pthread_cond_wait(&g_work_cv, &g_mtx);
			}
		}
		if( !g_running && g_ready_n == 0 )
			break;

		{
			int fd = g_ready[--g_ready_n];
			struct sw_chunk *list, *rem = NULL;
			int eagain = 0, dead = 0, coalesce;
			sw[fd].in_ready = 0;
			if( sw[fd].closing || sw[fd].head == NULL )
				continue;

			// check out the whole queue and send it outside the lock
			list = sw[fd].head;
			sw[fd].head = sw[fd].tail = NULL;
			sw[fd].in_use = 1;
			coalesce = (sw_coalesce_ms > 0);   // read under lock
			pthread_mutex_unlock(&g_mtx);

			// [perf] Coalesce: merge the chunks queued for this fd into one buffer
			// so they go out in a single send(). When the window is on these are the
			// small packets that accumulated during it; merging cuts syscalls /
			// segments / qdisc-lock trips. On OOM, fall back to chunk-by-chunk.
			if( coalesce && list && list->next ) {
				size_t total = 0;
				struct sw_chunk *c, *big;
				for( c = list; c; c = c->next ) total += c->len - c->off;
				big = chunk_alloc(total);
				if( big ) {
					size_t o = 0;
					for( c = list; c; c = c->next ) {
						memcpy(big->data + o, c->data + c->off, c->len - c->off);
						o += c->len - c->off;
					}
					big->next = NULL; big->off = 0; big->len = total;
					free_chain(list);
					list = big;
				}
			}

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
				chunk_free(c);
				if( dead ) { free_chain(list); list = NULL; break; }
			}

			pthread_mutex_lock(&g_mtx);
			sw[fd].in_use = 0;
			if( rem && !sw[fd].closing && !dead ) {
				// prepend the unsent remainder, schedule a delayed EAGAIN retry. The
				// coalesce window NEVER throttles this drain -- only the 5ms retry.
				struct sw_chunk *t = rem;
				while( t->next ) t = t->next;
				t->next = sw[fd].head;
				sw[fd].head = rem;
				if( sw[fd].tail == NULL ) sw[fd].tail = t;
				sw[fd].defer_backlog = 1;
				sw[fd].due = now_plus_ms(SW_RETRY_MS);
				defer_add(fd);
			} else {
				if( rem )
					free_chain(rem);
				// chunks may have been queued during the unlocked send: (re)schedule
				if( sw[fd].head && !sw[fd].in_ready && !sw[fd].deferred && !sw[fd].closing )
					sched_fd(fd);
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
	c = chunk_alloc(len);
	if( c == NULL )
		return; // OOM: drop (parity with a failed send on a full buffer)
	c->next = NULL;
	c->off  = 0;
	c->len  = len;
	memcpy(c->data, buf, len);

	pthread_mutex_lock(&g_mtx);
	if( sw[fd].closing ) {            // being torn down: drop
		pthread_mutex_unlock(&g_mtx);
		chunk_free(c);
		return;
	}
	if( sw[fd].tail ) sw[fd].tail->next = c;
	else              sw[fd].head = c;
	sw[fd].tail = c;

	if( sw[fd].in_use || sw[fd].in_ready ) {
		// worker is draining or has already scheduled this fd; it will pick up the
		// new chunk when it (re)checks head. nothing to do.
	} else if( sw[fd].deferred ) {
		// waiting on a deadline. If it's a coalesce window and we've now reached the
		// flush threshold, promote to immediate; otherwise let the window fire.
		if( !sw[fd].defer_backlog && qbytes_of(fd) >= SW_COALESCE_BYTES ) {
			defer_remove(fd);
			ready_push(fd);
			pthread_cond_signal(&g_work_cv);
		}
	} else {
		sched_fd(fd);
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
	defer_remove(fd);                // drop any armed coalesce/retry deadline
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
		chunk_free(d);
	}
}

void sendworker_reset(int fd)
{
	struct sw_chunk *c;
	if( fd <= 0 || fd >= SW_MAX )
		return;
	pthread_mutex_lock(&g_mtx);
	defer_remove(fd);                // drop any armed deadline before fd reuse
	c = sw[fd].head;
	sw[fd].head = sw[fd].tail = NULL;
	sw[fd].closing = 0;
	sw[fd].in_use  = 0;
	sw[fd].defer_backlog = 0;
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
		sw[i].in_ready = sw[i].in_use = sw[i].closing = sw[i].deferred = 0;
	}
	g_ready_n = 0;
	g_defer_n = 0;
	pool_drain();   // [perf 5a] worker is joined; release recycled buffers
}
