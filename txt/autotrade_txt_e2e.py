#!/usr/bin/env python3
"""autotrade_txt_e2e.py <run dir>: autotrade shops survive a restart on the TXT stand (save/autotrade.txt).
The stand's first account is GM 99: its character becomes a Merchant with a cart (@job/@allskill/@option),
puts 20 Red Potions in the cart, opens a shop and goes @autotrade; a second account buys after a restart.
 1 @autotrade writes save/autotrade.txt; 2 a restart: the shop board and the list are back; 3 buying 5 after
 the restart: the buyer gets them, the file follows; 4 the owner logs in: the shop goes, the file empties."""
import os, struct, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2elib import Stream, chat, enter_map, ensure_account, load_lengths  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
L = load_lengths()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run(["bash", os.path.join(HERE, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
def atfile():
    try: return open(os.path.join(run, "save", "autotrade.txt")).read()
    except FileNotFoundError: return ""
class C:
    def __init__(self, u, n):
        self.n = n; self.s = enter_map(u, "atpw1", n, log=lambda *a: None); self.st = Stream(self.s.map_sock, L); self.pk = []
    def pump(self, t):
        try:
            for x in self.st.packets(t): self.pk.append(x)
        except (ConnectionError, OSError): pass
    def cmd(self, t): chat(self.s.map_sock, self.n, t); self.pump(1.5)
    def send(self, b): self.s.map_sock.sendall(b)
    def quit(self):
        try: self.s.quit_game(wait=2)
        except Exception: pass
def vlist(c, vid):
    last = None
    for pid, p in c.pk:
        if pid == 0x133 and struct.unpack_from("<I", p, 4)[0] == vid: last = p
    out = {}
    if last:
        for off in range(8, len(last), 22):
            price, amount, idx, typ, nameid = struct.unpack_from("<IHHBH", last, off); out[nameid] = (price, amount, idx)
    return out

ensure_account("atvt", "atpw1"); time.sleep(11); ensure_account("atbt", "atpw1")
srv("stop"); srv("start")  # the GM list (conf/GM_account.txt: the first account is GM 99) reaches the map-server at a start
v = C("atvt", "ATVt"); v.pump(2)
for t in ("@joblevel 10", "@job 5", "@allskill", "@option 0 0 8", "@item 501 20", "@zeny 1000"):
    v.cmd(t)
idx = None
for pid, p in v.pk:
    if pid == 0xa0 and struct.unpack_from("<H", p, 6)[0] == 501: idx = struct.unpack_from("<H", p, 2)[0]
v.send(struct.pack("<HHI", 0x126, idx or 0, 20)); v.pump(2)
items = struct.pack("<HHI", 2, 20, 100)
v.send(struct.pack("<HH80sB", 0x1b2, 85 + len(items), b"TXT potions", 1) + items); v.pump(2)
check("0 the shop opens", any(pid == 0x136 for pid, _ in v.pk), "inv idx=%s" % idx)
b = C("atbt", "ATBt"); b.pump(1)
b.quit()
v.cmd("@autotrade"); time.sleep(2)
f = atfile()
check("1 @autotrade writes save/autotrade.txt", "TXT potions" in f and "\t501\t20\t100" in f, repr(f))
aid = int(f.split("\t")[2]) if f.startswith("S\t") else 0
srv("stop")
# the buyer needs zeny: 10000 in its athena.txt line (<base exp>,<job exp>,<zeny> is the 5th field)
path = os.path.join(run, "save", "athena.txt"); lines = open(path).read().split("\n")
for i, line in enumerate(lines):
    f2 = line.split("\t")
    if len(f2) > 5 and f2[2] == "ATBt":
        e = f2[4].split(","); e[2] = "10000"; f2[4] = ",".join(e); lines[i] = "\t".join(f2)
open(path, "w").write("\n".join(lines))
srv("start")
# both new characters start on the same spot (the start point): the buyer stands by the shop
b = C("atbt", "ATBt")
b.pump(3)
b.send(struct.pack("<HI", 0x130, aid)); b.pump(2)
vl = vlist(b, aid)
check("2 after a restart the shop is back with its item and price", vl.get(501, (0, 0))[:2] == (100, 20), "list=%s aid=%s" % (vl, aid))
if 501 in vl:
    b.send(struct.pack("<HHIHH", 0x134, 12, aid, 5, vl[501][2])); b.pump(3)
time.sleep(1)
check("3 a purchase after the restart: the file follows", "\t501\t15\t100" in atfile(), repr(atfile()))
b.quit()
# the TXT char-server answers the owner's first try with code 8 (the shop is being removed): a client retries
for attempt in range(5):
    try:
        v = C("atvt", "ATVt"); break
    except RuntimeError:
        time.sleep(3)
v.pump(3); time.sleep(1)
check("4 the owner logs in: the shop goes", "TXT potions" not in atfile(), repr(atfile()))
v.quit()
sys.exit(0 if ok else 1)
