#!/usr/bin/env python3
"""spam_cpu.py <run dir> <what> [seconds]: one logged-in player sends <what> as fast as the socket takes it (and
reads everything back), the test reports the map-server's CPU use (% of one core) and packets sent.
what: chat | emotion | storage | whodrops | charname | walk"""
import os, socket, struct, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, NAME  # noqa: E402

run, what = sys.argv[1], sys.argv[2]; secs = float(sys.argv[3]) if len(sys.argv) > 3 else 10
def pid():
    for p in subprocess.run(["pgrep", "-x", "map-server_sql"], capture_output=True, text=True).stdout.split():
        if os.path.realpath("/proc/%s/cwd" % p) == os.path.realpath(run): return p
def cpu_ticks(p):
    f = open("/proc/%s/stat" % p).read().split(")")[1].split(); return int(f[11]) + int(f[12])
s = rostub.Session(USER, PW, log=lambda *a: None)
s.login(); _, r = s.char_enter(); s.select_char(r[1][0][0]); assert s.map_enter()[0] == "ok"
sock = s.map_sock; sock.sendall(struct.pack("<H", 0x7D)); time.sleep(1)
def chat(t):
    m = ("%s : %s" % (NAME, t)).encode() + b"\0"; return struct.pack("<HH", 0xF3, 4 + len(m)) + m
pk = {"chat": chat("spam spam spam spam spam spam spam spam"), "emotion": struct.pack("<HB", 0xBF, 1),
      "storage": chat("@storage"), "whodrops": chat("@whodrops a"), "charname": struct.pack("<HI", 0x94, s.aid) + b"\0" * 8,
      "walk": None}[what]
stop = threading.Event(); got = [0]
def reader():
    sock.settimeout(0.2)
    while not stop.is_set():
        try:
            d = sock.recv(1 << 20)
            if not d: break
            got[0] += len(d)
        except socket.timeout: pass
        except OSError: break
threading.Thread(target=reader, daemon=True).start()
p = pid(); c0 = cpu_ticks(p); t0 = time.time(); n = 0
while time.time() - t0 < secs:
    try:
        sock.sendall(pk); n += 1
    except OSError:
        print("disconnected after %d" % n); break
el = time.time() - t0; c1 = cpu_ticks(p); stop.set()
hz = os.sysconf("SC_CLK_TCK")
print("%-9s sent %7d packets in %.1f s (%6.0f/s), got back %6.1f MB, map CPU %5.1f%% of a core"
      % (what, n, el, n / el, got[0] / 1e6, (c1 - c0) / hz / el * 100))
try: s.quit_game(wait=1)
except Exception: pass
