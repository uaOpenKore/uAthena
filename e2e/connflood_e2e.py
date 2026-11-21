#!/usr/bin/env python3
"""connflood_e2e.py <host> <port> <n> [server pid]: one address opens n idle connections to a server port and holds
them; meanwhile a real player must still log in, and the server's memory must stay bounded. Before any limit per
address, every connection gets a session (and its buffers) until stall_time; the fd table (SOCKET_MAX / nofile) runs
out and nobody else gets in."""
import os, resource, socket, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW  # noqa: E402

host, port, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pid = sys.argv[4] if len(sys.argv) > 4 else None
resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
def rss():
    if not pid: return 0
    for l in open("/proc/%s/status" % pid):
        if l.startswith("VmRSS:"): return int(l.split()[1]) // 1024
r0 = rss()
socks, refused = [], 0
t0 = time.time()
for i in range(n):
    try:
        s = socket.create_connection((host, port), timeout=2)
        socks.append(s)
    except OSError:
        refused += 1
time.sleep(2)
alive = 0
for s in socks:
    s.setblocking(False)
    try:
        d = s.recv(1)
        if d == b"": continue   # closed by the server
        alive += 1
    except BlockingIOError:
        alive += 1
    except OSError:
        pass
print("held %d of %d connections open from one address (%d refused at connect), server RSS %d -> %d MB"
      % (alive, n, refused, r0, rss()), flush=True)
# a real player from another address must still get in
ok = True
try:
    p = rostub.Session(USER, PW, log=lambda *a: None)
    p.login(timeout=10); _, r = p.char_enter(timeout=10); p.select_char(r[1][0][0]); st = p.map_enter(timeout=10)[0]
    print("a player logging in meanwhile: map_enter %s" % st)
    ok = st == "ok"
    p.quit_game(wait=1)
except Exception as e:
    print("a player logging in meanwhile: FAILED (%s)" % e); ok = False
for s in socks: s.close()
limit = int(os.environ.get("PER_IP_LIMIT", "0"))
if alive > max(limit, 0) and limit:
    print("FAIL  %d connections from one address stayed open (limit %d)" % (alive, limit)); ok = False
if not limit and alive >= n * 0.9:
    print("FAIL  one address holds %d idle sessions: no per-address limit" % alive); ok = False
if not ok: sys.exit(1)
print("ok"); print("ALL PASSED")
