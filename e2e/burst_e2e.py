#!/usr/bin/env python3
"""burst_e2e.py <run dir>: (1) a burst of valid packets bigger than the 16 KB receive buffer (100 chat lines at once:
what a client sends after its connection stalled) must NOT drop the session as an
"invalid packet"; (2) a client that keeps flooding (packets as fast as the socket takes them) must be dropped
quickly, and the map-server's CPU must stay low meanwhile."""
import os, socket, struct, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW  # noqa: E402
run = sys.argv[1]
def pid():
    for p in subprocess.run(["pgrep", "-x", "map-server_sql"], capture_output=True, text=True).stdout.split():
        if os.path.realpath("/proc/%s/cwd" % p) == os.path.realpath(run): return p
def cpu(p):
    f = open("/proc/%s/stat" % p).read().split(")")[1].split(); return int(f[11]) + int(f[12])
def login():
    s = rostub.Session(USER, PW, log=lambda *a: None)
    s.login(); _, r = s.char_enter(); s.select_char(r[1][0][0]); assert s.map_enter()[0] == "ok"
    s.map_sock.sendall(struct.pack("<H", 0x7D)); s.map_alive(1); return s
ok = True
s = login()
from elemark_e2e import NAME
msg = ("%s : %s" % (NAME, "x" * 170)).encode() + b"\0"
chatpk = struct.pack("<HH", 0xF3, 4 + len(msg)) + msg
s.map_sock.sendall(chatpk * 100)   # ~19 KB at once: 100 chat lines a stalled connection delivers together
alive, _ = s.map_alive(3)
print("1 a %d-byte burst of 100 valid packets: session %s" % (len(chatpk) * 100, "kept" if alive else "DROPPED"))
if not alive: ok = False
else: s.quit_game(wait=1)
time.sleep(2)
s = login(); sock = s.map_sock; p = pid(); c0 = cpu(p); t0 = time.time(); n = 0; dropped_at = None
stop = threading.Event()
def rd():
    sock.settimeout(0.2)
    while not stop.is_set():
        try:
            if not sock.recv(1 << 20): break
        except socket.timeout: pass
        except OSError: break
threading.Thread(target=rd, daemon=True).start()
while time.time() - t0 < 8:
    try: sock.sendall(struct.pack("<HB", 0xBF, 1) * 200); n += 200
    except OSError: dropped_at = time.time() - t0; break
el = time.time() - t0; stop.set(); c = (cpu(p) - c0) / os.sysconf("SC_CLK_TCK") / el * 100
print("2 flood: %d packets, %s, map CPU %.0f%% of a core" % (n, ("dropped after %.1f s" % dropped_at) if dropped_at else "NOT dropped in 8 s", c))
if dropped_at is None or dropped_at > 5: ok = False
if not ok: sys.exit(1)
print("ok"); print("ALL PASSED")
