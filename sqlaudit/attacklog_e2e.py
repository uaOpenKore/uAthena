#!/usr/bin/env python3
"""attacklog_e2e.py <run dir>: abnormal packets go to log/attack-login.log, log/attack-char.log, log/attack-map1.log.
1 login: an unknown packet; 2 char: an unknown packet; 3 map: junk instead of the map login;
5 map: a logged-in player sends an unknown packet (named with acc/cid); 6 map: a bad length;
7 a flood from one address is cut to 20 lines a minute plus a "... more" line; 8 a map flood names its packets; every line has the date, the
server, the address and the first bytes."""
import os, re, socket, struct, subprocess, sys, time
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import enter_map  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def lines(name):
    try: return open(os.path.join(run, "log", "attack-%s.log" % name), errors="replace").read().splitlines()
    except FileNotFoundError: return []
def send(port, data, wait=0.5):
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    s.sendall(data); time.sleep(wait)
    try: s.recv(4096)
    except Exception: pass
    s.close()
subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
for n in ("login", "char", "map1"):
    try: os.remove(os.path.join(run, "log", "attack-%s.log" % n))
    except FileNotFoundError: pass
subprocess.run([os.path.join(SP, "srv.sh"), "start", run], stdout=subprocess.DEVNULL); time.sleep(10)
day = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d \[ATTACK\] ")
send(16900, struct.pack("<H", 0x9999) + b"\x01\x02\x03\x04")
l = lines("login")
check("1 login: an unknown packet", any("unknown_packet: 0x9999" in x and "127.0.0.1" in x and "head=99 99 01 02" in x and day.match(x) for x in l), l[-2:])
send(16121, struct.pack("<H", 0x8888) + b"\xaa\xbb")
l = lines("char")
check("2 char: an unknown packet", any("unknown_packet: 0x8888" in x for x in l), l[-2:])
send(15121, struct.pack("<HIIIIB", 0x9b, 1, 2, 3, 4, 5) + b"junk" * 8)
l = lines("map1")
check("3 map: junk instead of the map login", any("bad_login_packet" in x for x in l), l[-2:])
try: rostub.Session("atklog_M", "atkpw1", log=lambda *a: None).login()
except Exception: pass
time.sleep(0.5)
s = enter_map("atklog", "atkpw1", "AtkLog", log=lambda *a: None)
s.map_sock.sendall(struct.pack("<H", 0x7777) + b"\x00" * 6); time.sleep(1)
l = lines("map1")
check("5 map: a logged-in player's unknown packet names the account", any("unknown_packet: 0x7777" in x and "acc=" in x and "name='AtkLog'" in x for x in l), l[-2:])
s.map_sock.sendall(struct.pack("<HH", 0x00f3, 2)); time.sleep(1)  # 0xf3 is variable length: 2 < 4
l = lines("map1")
check("6 map: a bad length", any("bad_length: 0x00f3" in x for x in l), l[-2:])
# 9 ticks never make a flood (S. 22.11: OpenKore bursts 150-200 ticks): 230 in a second, still online, at most 10 answered
try: s.quit_game(wait=1)
except Exception: pass
time.sleep(3)
s = enter_map("atklog", "atkpw1", "AtkLog", log=lambda *a: None)
time.sleep(1)
s.map_sock.settimeout(0.2)
try:
    while s.map_sock.recv(65536): pass
except Exception: pass
for i in range(230):
    s.map_sock.sendall(struct.pack("<HI", 0x0089, i) + b"\0\0")
time.sleep(1.5)
data = b""
try:
    while True:
        d = s.map_sock.recv(65536)
        if not d: break
        data += d
except Exception: pass
replies = data.count(b"\x7f\x00")
alive = True
try: s.map_sock.sendall(struct.pack("<HI", 0x0089, 1) + b"\0\0"); time.sleep(0.5); s.map_sock.recv(10)
except Exception: alive = False
check("9 230 ticks in a second: no flood kick, at most 10 answered", alive and 1 <= replies <= 12, "alive=%s replies=%d" % (alive, replies))
# 8 a map flood names the packets of that second (S. 2026-11-21: which packets do the bots flood with)
try: s.quit_game(wait=1)
except Exception: pass
time.sleep(3)
s = enter_map("atklog", "atkpw1", "AtkLog", log=lambda *a: None)
time.sleep(1)
for i in range(230):
    try: s.map_sock.sendall(struct.pack("<H5sI", 0x008c, bytes(5), 150000 + i))  # getcharnamerequest
    except OSError: break
time.sleep(1.5)
l = lines("map1")
check("8 a map flood names the packets of that second", any("packet_flood: over 200 packets in a second (0x008c x" in x for x in l), l[-2:])
try: s.quit_game(wait=1)
except Exception: pass
for i in range(40):
    send(16900, struct.pack("<H", 0x9998), wait=0.02)
time.sleep(61)
send(16900, struct.pack("<H", 0x9997))
l = lines("login")
n9998 = sum("0x9998" in x for x in l)
more = [x for x in l if "more line(s)" in x]
check("7 a flood is cut to 20 lines a minute plus one '... more' line", n9998 + sum("0x9999" in x for x in l) <= 20 and bool(more), "0x9998 lines=%d more=%s" % (n9998, more[-1:]))
subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
sys.exit(0 if ok else 1)
