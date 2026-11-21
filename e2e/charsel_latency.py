#!/usr/bin/env python3
"""Time from char select (0x66) to the 0x71 answer, N times (testacc). Usage: python3 -I charsel_latency.py [N]"""
import os
import struct
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
ms = []
for i in range(n):
    s = rostub.Session("testacc", "testpass")
    s.login()
    _, (kind, chars) = s.char_enter()
    t0 = time.perf_counter()
    s.select_char(chars[0][0])
    ms.append((time.perf_counter() - t0) * 1000)
    time.sleep(21.5 if False else 0.3)
ms.sort()
print("char select -> 0x71: n=%d min %.1f median %.1f p90 %.1f max %.1f ms" % (n, ms[0], ms[len(ms)//2], ms[int(len(ms)*0.9)-1], ms[-1]))
