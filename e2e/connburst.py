#!/usr/bin/env python3
"""N clients connect to the login-server at the same instant and send a login for a non-existent account;
time until each gets the server's answer. Usage: python3 -I connburst.py [N] [port]"""
import socket
import struct
import sys
import threading
import time
n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
port = int(sys.argv[2]) if len(sys.argv) > 2 else 6900
bar = threading.Barrier(n)
res = [None] * n


def one(i):
    bar.wait()
    t0 = time.perf_counter()
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=10)
        user = ("nobody%03d" % i).encode() + b"\0" * (24 - 9)
        s.sendall(struct.pack("<HI", 0x64, 20) + user + b"x" * 1 + b"\0" * 23 + b"\0")
        s.settimeout(10)
        d = s.recv(64)
        res[i] = (time.perf_counter() - t0) * 1000 if d else None
        s.close()
    except Exception:  # noqa: BLE001
        res[i] = None


th = [threading.Thread(target=one, args=(i,)) for i in range(n)]
for t in th:
    t.start()
for t in th:
    t.join()
ok = sorted(x for x in res if x is not None)
print("n=%d answered=%d  median %.0f ms  p90 %.0f ms  max %.0f ms  >=900 ms: %d" % (
    n, len(ok), ok[len(ok) // 2], ok[int(len(ok) * 0.9) - 1], ok[-1], sum(1 for x in ok if x >= 900)))
