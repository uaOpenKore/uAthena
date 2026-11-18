// Copyright (c) uAthena / bornrok.com
// [stall-guard] How long the server itself was gone during one main-loop round. Pure arithmetic only, so
// test_stallguard.c needs nothing else; do_sendrecv (socket.c) measures and acts on it.
#ifndef _STALLGUARD_H_
#define _STALLGUARD_H_

/// Milliseconds of one main-loop round in which the server did not run.
///   since_prev: ms from the previous round's start to this round's start (an unsigned tick difference,
///               so it stays right across the tick wrap)
///   waited:     ms the previous round's socket wait actually took
///   asked:      ms that wait was allowed to take (the time to the next timer)
/// Sleeping in the wait up to `asked` is the loop doing its job, not a stall: an idle login-server sleeps
/// 4-5 s until its next timer. Everything else is: timers and packet parsing that took long (a frozen
/// loop), and any time the wait ran past `asked` (a VM/host pause while it slept).
static inline unsigned int stallguard_gone_ms(unsigned int since_prev, unsigned int waited, unsigned int asked)
{
	unsigned int slept = waited < asked ? waited : asked;
	return since_prev > slept ? since_prev - slept : 0;
}

/// The longest socket wait, in ms. A freeze while the loop sleeps only shows as the wait running past its
/// timeout, and do_timer has no upper bound (an idle login-server would sleep up to 60 s until ip_ban_flush),
/// so the loop wakes at least once a second and every freeze is seen to within 1 s (rAthena does the same).
#define STALLGUARD_MAX_WAIT_MS 1000

/// The socket wait for `next` ms to the next timer, cut to STALLGUARD_MAX_WAIT_MS.
static inline int stallguard_wait_ms(int next)
{
	return next > STALLGUARD_MAX_WAIT_MS ? STALLGUARD_MAX_WAIT_MS : next;
}

#endif /* _STALLGUARD_H_ */
