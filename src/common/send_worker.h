// [perf] Off-thread socket send worker.
//
// Moves the send() syscalls (and the kernel TCP/IP/qdisc work they drive) off
// the single game-loop thread onto a dedicated thread, so a burst of outbound
// traffic no longer steals CPU from the tick. OFF by default; the game loop's
// inline send path is unchanged unless this is enabled.
//
// Threading contract (mirrors log_async/async_db): the worker NEVER touches live
// game state. The game thread hands it OWNED COPIES of already-built packet bytes
// via sendworker_send(); the worker only owns those copies and the raw fd number.
// Per-fd send state lives in a stable fd-indexed array (never freed with the
// session), so freeing a session can't dangle the worker. The game thread keeps
// ownership of close(): sendworker_release() makes the worker drop/finish any
// work for an fd and blocks until nothing is in-flight, so close()+fd-reuse can
// never race a send to the wrong client.
#ifndef _SEND_WORKER_H_
#define _SEND_WORKER_H_

#include <stddef.h>

#ifdef MINICORE
// MINICORE tools (e.g. ladmin) never send off-thread — stub everything inline so
// they don't have to link the worker.
static inline void sendworker_init(void) {}
static inline void sendworker_final(void) {}
static inline void sendworker_send(int fd, const unsigned char *buf, size_t len) { (void)fd; (void)buf; (void)len; }
static inline void sendworker_release(int fd) { (void)fd; }
static inline void sendworker_reset(int fd) { (void)fd; }
static inline void sendworker_set_coalesce(int ms) { (void)ms; }
static inline void sendworker_set_pool(int on) { (void)on; }
#else

// Start/stop the worker thread. Idempotent. Call before accepting clients.
void sendworker_init(void);
void sendworker_final(void);

// Hand off len bytes to be sent on fd (a private copy is made). FIFO per fd.
void sendworker_send(int fd, const unsigned char *buf, size_t len);

// Before closing fd: drop queued data, wait until the worker is not mid-send on
// it. After this returns the caller may safely close()/reuse the fd.
void sendworker_release(int fd);

// Before reusing fd for a new connection: clear any residual state.
void sendworker_reset(int fd);

// Send-coalescing window in milliseconds: 0 or negative = off; >0 = hold an fd's
// lone sub-segment dribble up to this long so the small packets that pile up go
// out as one send(). Bulk (>= ~1 segment) and EAGAIN drains always flush at once.
void sendworker_set_coalesce(int ms);

// [perf 5a] Chunk recycling pool: 1 = recycle freed send buffers (default), 0 =
// plain malloc/free per send. Behaviour-identical; for A/B and as a kill-switch.
void sendworker_set_pool(int on);

#endif /* MINICORE */
#endif /* _SEND_WORKER_H_ */
