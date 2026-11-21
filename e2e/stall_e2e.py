#!/usr/bin/env python3
"""Stall guard + abandoned held login, against a local login+char+map stack.

usage: stall_e2e.py <run-dir> <idle_seconds>
  1. A enters the map, its client is killed (prevent_logout keeps the char ~10 s), A logs in again and its
     char-select connection is held (charsel_wait); the client gives up after 3 s and closes it.
  2. The stack idles for <idle_seconds>: count [DCMETRIC] loop_stall per server (an idle loop is no stall).
  3. Real freezes: SIGSTOP login 10 s, map 6 s -> each must be reported as a loop_stall.
"""
import os
import re
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenarios  # noqa: E402  (RUN comes from argv[1])

RUN, IDLE = sys.argv[1], int(sys.argv[2])
log = scenarios.log


def size(name):
    try:
        return os.path.getsize(os.path.join(RUN, name))
    except OSError:
        return 0


def since(name, mark):
    with open(os.path.join(RUN, name), "rb") as f:
        f.seek(mark)
        txt = f.read().decode("latin-1")
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", txt)


def pid(name):
    return int(open(os.path.join(RUN, name + ".pid")).read())


def stalls(name, mark):
    return [l.strip() for l in since(name, mark).splitlines() if "loop_stall" in l]


# 1. abandoned held login
cmark = size("char.out")
a, ra = scenarios.full_login("A")
if ra[0] != "ok":
    log("A could not enter:", ra)
    sys.exit(1)
time.sleep(2)
log("killing A's client -> the char stays on the map ~10 s (prevent_logout)")
a.kill_map()
a2 = scenarios.account("A")
t = time.time()
try:
    took, res = a2.char_enter(timeout=3)
    log("UNEXPECTED: char-select answered at once:", res)
except TimeoutError:
    log("relogin held by the char-server; the client gives up after %.1f s and closes" % (time.time() - t))
    a2.char_sock.close()
    a2.char_sock = None
time.sleep(13)
a3, r3 = scenarios.full_login("A")
log("RESULT: A logs in normally afterwards ->", r3)
if r3[0] == "ok":
    time.sleep(11)
    a3.quit_game(2)
for line in since("char.out", cmark).splitlines():
    if "DCMETRIC" in line:
        log("  char.log:", line.strip())

# 2. idle
marks = {s: size(s + ".out") for s in ("login", "char", "map")}
log("idle for %d s ..." % IDLE)
time.sleep(IDLE)
for s in ("login", "char", "map"):
    found = stalls(s + ".out", marks[s])
    log("RESULT: idle %d s -> %s loop_stall lines: %d" % (IDLE, s, len(found)))
    for line in found[:5]:
        log("   ", line)

# 3. real freezes
for s, secs in (("login", 10), ("map", 6)):
    m = size(s + ".out")
    p = pid(s)
    log("SIGSTOP %s (pid %d) for %d s" % (s, p, secs))
    os.kill(p, signal.SIGSTOP)
    time.sleep(secs)
    os.kill(p, signal.SIGCONT)
    time.sleep(4)
    found = stalls(s + ".out", m)
    log("RESULT: %d s freeze of %s -> loop_stall lines: %d %s" % (secs, s, len(found), found[:2]))
