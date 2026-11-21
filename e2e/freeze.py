#!/usr/bin/env python3
"""Freeze experiment: does a frozen map-server main loop time out clients?

usage: freeze.py <run-dir> <freeze_seconds> <mode>
  mode=keepalive : client keeps sending a keepalive every 5 s during the freeze
  mode=silent    : client stops sending 20 s before the freeze (an idle-but-alive client)
"""
import os
import signal
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenarios  # noqa: E402  (reuses login helpers; RUN comes from argv[1])

RUN, FREEZE, MODE = sys.argv[1], int(sys.argv[2]), sys.argv[3]
log = scenarios.log
pid = int(open(os.path.join(RUN, "map.pid")).read())

v, rv = scenarios.full_login("V")
log("V in map:", rv, "map-server pid", pid)
if MODE == "silent":
    v.map_alive(3)            # one keepalive, then silence
    log("V goes silent; freeze starts in 20 s")
    time.sleep(20)
else:
    time.sleep(2)

def freezer():
    log("SIGSTOP map-server for %d s" % FREEZE)
    os.kill(pid, signal.SIGSTOP)
    time.sleep(FREEZE)
    os.kill(pid, signal.SIGCONT)
    log("SIGCONT map-server")

t = threading.Thread(target=freezer)
t.start()
if MODE == "keepalive":
    alive, kick = v.map_alive(FREEZE + 15)
else:
    t.join()
    # after a host/VM pause the client's packets arrive late (TCP retransmit backoff): stay quiet 5 s more
    time.sleep(5)
    alive, kick = v.map_alive(15)   # only now does V speak again
t.join()
log("RESULT: V still connected=%s" % alive)
mark_txt = scenarios.maplog_since(0)
for line in mark_txt.splitlines()[-30:]:
    if "timed out" in line or "DROP" in line or "loop_stall" in line:
        log("  map.log:", line.strip())
