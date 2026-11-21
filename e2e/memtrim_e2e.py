#!/usr/bin/env python3
"""memtrim_e2e.py <map-server pid> [wait s]: memory freed after a peak must go back to the system.
A GM spawns 20 x 999 Red Plants (they never walk: 20k walking porings around the test client
flooded it past the 2 MB send cap and got it dropped before the kill) (a peak of mob memory), kills them all (@killmonster2), the test waits and
reads the map-server's VmRSS: at least 60% of what the peak added must be returned."""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, chat  # noqa: E402

pid, wait = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 75
def rss_mb():
    for l in open("/proc/%s/status" % pid):
        if l.startswith("VmRSS:"):
            return int(l.split()[1]) / 1024.0
def warp(where):
    chat(s.map_sock, "@warp " + where)
    s.map_alive(2)
    s.map_sock.sendall(struct.pack("<H", 0x7D))  # map loaded: the server takes commands again
    s.map_alive(1)

s = rostub.Session(USER, PW, log=lambda *a: None)
s.login(); _, r = s.char_enter(); s.select_char(r[1][0][0]); assert s.map_enter()[0] == "ok"
t0 = time.time()
s.map_alive(1)
warp("new_zone01 55 99")  # the plants go there (whatever map an earlier test left the char on); the GM leaves before killing them
s.map_alive(2)
base = rss_mb()
for i in range(20):
    chat(s.map_sock, "@monster 1078 999")
    s.map_alive(1.5)
peak = rss_mb()
print("peak at %.0f s" % (time.time() - t0), flush=True)
warp("prontera 150 150")  # away: 20k deaths in sight overflow the 2 MB send cap
chat(s.map_sock, "@killmonster2 new_zone01")
s.map_alive(5)
killed = rss_mb()
end = time.time() + wait
while time.time() < end:
    alive, _ = s.map_alive(10)
    if not alive:
        print("FAIL  the test client was disconnected"); sys.exit(1)
    print("  t=%.0f s RSS %.1f MB" % (time.time() - t0, rss_mb()), flush=True)
after = rss_mb()
warp("new_zone01 55 99")
s.quit_game(wait=1)
grown = peak - base
back = (peak - after) / grown * 100 if grown > 0 else 0
print("RSS MB: before %.1f, peak %.1f (+%.1f), right after kill %.1f, after %d s %.1f -> returned %.0f%%"
      % (base, peak, grown, killed, wait, after, back))
if grown < 20:
    print("FAIL  the peak added only %.1f MB, the test did not load the server" % grown); sys.exit(1)
if back < 60:
    print("FAIL  only %.0f%% of the peak went back to the system" % back); sys.exit(1)
print("ok    %.0f%% of the peak returned" % back); print("ALL PASSED")
