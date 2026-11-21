#!/usr/bin/env python3
"""connflood_hold.py <host> <port> <n> <hold s>: open n idle connections from this address, hold them, then print
how many the server kept open."""
import resource, socket, sys, time
host, port, n, hold = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
socks, refused = [], 0
for i in range(n):
    try: socks.append(socket.create_connection((host, port), timeout=2))
    except OSError: refused += 1
print("opened %d (%d refused)" % (len(socks), refused), flush=True)
time.sleep(hold)
alive = 0
for s in socks:
    s.setblocking(False)
    try:
        if s.recv(1) != b"": alive += 1
    except BlockingIOError: alive += 1
    except OSError: pass
print("HELD %d" % alive, flush=True)
