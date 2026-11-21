#!/usr/bin/env python3
"""Baseline: does a completely silent client get reaped by stall_time at all? usage: idle.py <run-dir> <seconds>"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenarios  # noqa: E402

secs = int(sys.argv[2])
v, rv = scenarios.full_login("V")
scenarios.log("V in map", rv, "- now completely silent (no keepalive, not reading) for %d s" % secs)
time.sleep(secs)
alive, kick = v.map_alive(3)
scenarios.log("RESULT after %d s silence: connected=%s" % (secs, alive))
for line in scenarios.maplog_since(0).splitlines()[-15:]:
    if "timed out" in line or "DROP" in line or "loop_stall" in line:
        scenarios.log("  map.log:", line.strip())
