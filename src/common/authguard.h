// Account lock against password guessing (S. 2026-11-21): the pure rules, shared by the SQL and TXT
// login-servers and unit tested by test_authguard.c.
//
// The IP ban (dynamic_pass_failure_ban) stops one address; guessing one account's password from many addresses
// goes past it. So each account counts its wrong passwords from all addresses together: `limit` (10) of them within
// `window` seconds lock the account for `base` seconds, every further lock within a day twice as long, up to
// `max`. While locked, even the right password is refused (or the guessing would go on and the answer would
// tell the password), except from an address the account logged in from successfully within `trusted` seconds:
// that is how the owner still gets in while someone else guesses. A successful login clears the count.
#ifndef _AUTHGUARD_H_
#define _AUTHGUARD_H_

#include <string.h>
#include <time.h>

#define AG_FAILS 16  // wrong passwords kept per account (the limit is at most this)
#define AG_TRUSTED 5 // addresses kept per account that logged in successfully

struct ag_config {
	int limit;          // wrong passwords ...
	int window;         // ... within this many seconds lock the account
	int base, max;      // the first lock (s); each further one within a day doubles, up to max (s)
	int trusted;        // a successful address stays trusted this long (s)
};

struct ag_state {
	time_t fail_at[AG_FAILS];
	unsigned int fail_ip[AG_FAILS];
	int fails;              // entries used in fail_at/fail_ip (oldest first)
	time_t lock_until;      // 0 = not locked
	time_t last_lock;       // when the last lock began (doubling within a day)
	int locks;              // locks within a day of each other
	int lock_fails, lock_ips; // the wrong passwords and their addresses that started the last lock
	unsigned int ok_ip[AG_TRUSTED];
	time_t ok_at[AG_TRUSTED];
};

// Drops the wrong passwords older than the window.
static inline void ag_expire(struct ag_state* s, const struct ag_config* c, time_t now)
{
	int i, k = 0;
	for (i = 0; i < s->fails; i++) {
		if (now - s->fail_at[i] < c->window) {
			s->fail_at[k] = s->fail_at[i];
			s->fail_ip[k] = s->fail_ip[i];
			k++;
		}
	}
	s->fails = k;
}

static inline bool ag_locked(const struct ag_state* s, time_t now)
{
	return s->lock_until > now;
}

// Did the account log in successfully from `ip` within the trusted time?
static inline bool ag_trusted(const struct ag_state* s, const struct ag_config* c, unsigned int ip, time_t now)
{
	int i;
	for (i = 0; i < AG_TRUSTED; i++)
		if (s->ok_at[i] && s->ok_ip[i] == ip && now - s->ok_at[i] < c->trusted)
			return true;
	return false;
}

// The different addresses among the wrong passwords in the window.
static inline int ag_fail_ips(const struct ag_state* s)
{
	int i, j, n = 0;
	for (i = 0; i < s->fails; i++) {
		for (j = 0; j < i; j++)
			if (s->fail_ip[j] == s->fail_ip[i])
				break;
		if (j == i)
			n++;
	}
	return n;
}

// A wrong password from `ip`. Returns the seconds of the lock it starts, 0 if none.
static inline int ag_fail(struct ag_state* s, const struct ag_config* c, unsigned int ip, time_t now)
{
	int secs, i, limit = c->limit < 1 ? 1 : c->limit > AG_FAILS ? AG_FAILS : c->limit;
	ag_expire(s, c, now);
	if (s->fails == AG_FAILS) { // full: the oldest goes
		memmove(s->fail_at, s->fail_at + 1, sizeof(s->fail_at[0]) * (AG_FAILS - 1));
		memmove(s->fail_ip, s->fail_ip + 1, sizeof(s->fail_ip[0]) * (AG_FAILS - 1));
		s->fails--;
	}
	s->fail_at[s->fails] = now;
	s->fail_ip[s->fails] = ip;
	s->fails++;
	if (ag_locked(s, now) || s->fails < limit)
		return 0;
	if (s->last_lock == 0 || now - s->last_lock >= 86400)
		s->locks = 0;
	secs = c->base;
	for (i = 0; i < s->locks && secs < c->max; i++)
		secs *= 2;
	if (secs > c->max)
		secs = c->max;
	s->locks++;
	s->last_lock = now;
	s->lock_until = now + secs;
	s->lock_fails = s->fails;
	s->lock_ips = ag_fail_ips(s);
	s->fails = 0; // after the lock the guesser has `limit` tries again, then a longer lock
	return secs;
}

// A successful login from `ip`: the count and the lock go, the address is trusted (the oldest one makes room).
static inline void ag_success(struct ag_state* s, unsigned int ip, time_t now)
{
	int i, slot = 0;
	s->fails = 0;
	s->lock_until = 0;
	s->locks = 0;
	s->last_lock = 0;
	for (i = 0; i < AG_TRUSTED; i++) {
		if (s->ok_ip[i] == ip && s->ok_at[i]) {
			slot = i;
			break;
		}
		if (s->ok_at[i] < s->ok_at[slot])
			slot = i;
	}
	s->ok_ip[slot] = ip;
	s->ok_at[slot] = now;
}

// Can the state be forgotten (no count, no lock, no trusted address left)?
static inline bool ag_idle(const struct ag_state* s, const struct ag_config* c, time_t now)
{
	int i;
	if (ag_locked(s, now) || (s->fails && now - s->fail_at[s->fails - 1] < c->window))
		return false;
	if (s->last_lock && now - s->last_lock < 86400)
		return false;
	for (i = 0; i < AG_TRUSTED; i++)
		if (s->ok_at[i] && now - s->ok_at[i] < c->trusted)
			return false;
	return true;
}

#endif /* _AUTHGUARD_H_ */
