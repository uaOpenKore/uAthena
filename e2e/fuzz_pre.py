#!/usr/bin/env python3
"""fuzz_pre.py <host> <port> <server name: login|char> <run dir> [n]: an unauthenticated client sends packets
0x0000-0x0fff plus the server-to-server range 0x2700-0x3100 with boundary/random contents to a login or char port
(no login done). The server must stay alive and keep accepting connections; memory manager quiet."""
import os, random, socket, struct, subprocess, sys, time
host, port, name, run = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
n = int(sys.argv[5]) if len(sys.argv) > 5 else 6
rnd = random.Random(20)
def pid():
    for p in subprocess.run(["pgrep", "-x", "%s-server_sql" % name], capture_output=True, text=True).stdout.split():
        if os.path.realpath("/proc/%s/cwd" % p) == os.path.realpath(run): return p
def memlog():
    t = open(os.path.join(run, "%s.out" % name), errors="replace").read()
    return sum(t.count(k) for k in ("Memory manager: args of", "overflowed pointer", "not valid pointer", "freed pointer"))
p0 = pid(); m0 = memlog(); bad = []
cmds = list(range(0x0000, 0x1000)) + list(range(0x2700, 0x3100))
for i, cmd in enumerate(cmds):
    for k in range(n):
        L = rnd.choice((2, 3, 4, 6, 10, 26, 30, 47, 55, 60, 86, 90, 128, 300, 2000))
        body = bytes(rnd.getrandbits(8) for _ in range(max(0, L - 2)))
        if k % 3 == 1 and L >= 4: body = struct.pack("<H", rnd.choice((0, 1, 3, 4, 0xFFFF, 0x8000, L))) + body[2:]
        try:
            s = socket.create_connection((host, port), timeout=2)
            s.sendall(struct.pack("<H", cmd) + body)
            s.settimeout(0.05)
            try: s.recv(4096)
            except OSError: pass
            s.close()
        except OSError as e:
            bad.append((hex(cmd), "connect/send: %s" % e)); time.sleep(0.5)
    if i % 256 == 255 or cmd in (0x0fff, 0x30ff):
        pp = pid(); m = memlog()
        st = "alive" if pp == p0 else "DIED"
        print("%s up to 0x%04x: %s, memory errors %d" % (name, cmd, st, m - m0), flush=True)
        if pp != p0: bad.append((hex(cmd), "SERVER DIED")); break
print("BAD %d: %s" % (len(bad), bad[:20]))
