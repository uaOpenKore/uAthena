#!/usr/bin/env python3
"""vendtax_e2e.py <run dir>: the vending tax is kept back (S. 2026-11-27: vending_tax 200 = 2 % in items.conf, but
vending_tax/10000 is integer division, 0, so the vendor got the full price).
Vendor ATVend opens a shop with Red Potions at 1000 z; buyer ATBuy buys 5 (5000 z).
 1 the buyer pays 5000
 2 the vendor gets 4900 (2 % kept back)"""
import os, re, struct, subprocess, sys, time
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths, messages  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
L = load_lengths()
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def maplog(): return open(os.path.join(run, "map.out"), errors="replace").read()
def stop(): subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
def start():
    subprocess.run([os.path.join(SP, "srv.sh"), "start", run], stdout=subprocess.DEVNULL)
    time.sleep(8)

POT, APPLE = 501, 512
def cid(name): return sql("SELECT char_id FROM `char` WHERE name='%s'" % name)
def aid(name): return sql("SELECT account_id FROM `char` WHERE name='%s'" % name)
def setup():
    for u, n in (("atvend", "ATVend"), ("atbuy", "ATBuy")):
        if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) == "0":
            try: rostub.Session(u + "_M", "atpass1", log=lambda *a: None).login()
            except Exception: pass
            time.sleep(0.5)
        if not cid(n):
            s = enter_map(u, "atpass1", n, log=lambda *a: None); s.quit_game(wait=2)
    time.sleep(3)
def stock():
    """(while stopped) the vendor: Merchant at prontera 150,150 with Vending, a cart; the buyer next to it."""
    v, b = cid("ATVend"), cid("ATBuy")
    sql("UPDATE login SET level=0 WHERE userid IN ('atvend','atbuy')")
    sql("UPDATE `char` SET class=5, job_level=40, base_level=50, `option`=8, zeny=1000, last_map='prontera', last_x=150, last_y=150, online=0 WHERE char_id=%s" % v)
    sql("UPDATE `char` SET zeny=1000000, last_map='prontera', last_x=151, last_y=150, online=0 WHERE char_id=%s" % b)
    sql("REPLACE INTO skill (char_id, id, lv) VALUES (%s, 1, 9), (%s, 36, 10), (%s, 37, 10), (%s, 39, 10), (%s, 41, 10)" % (v, v, v, v, v))
    sql("DELETE FROM cart_inventory WHERE char_id=%s" % v); sql("DELETE FROM inventory WHERE char_id=%s AND nameid IN (%d,%d)" % (b, POT, APPLE))
    sql("INSERT INTO cart_inventory (char_id, nameid, amount, identify) VALUES (%s, %d, 50, 1), (%s, %d, 30, 1)" % (v, POT, v, APPLE))
    sql("DELETE FROM autotrade_shop WHERE char_id=%s" % v); sql("DELETE FROM autotrade_item WHERE char_id=%s" % v)

class Client:
    def __init__(self, user, name):
        self.name = name
        self.s = enter_map(user, "atpass1", name, log=lambda *a: None)
        self.st = Stream(self.s.map_sock, L); self.pk = []; self.closed = False
    def pump(self, sec):
        try:
            for pid, p in self.st.packets(sec): self.pk.append((pid, p))
        except (ConnectionError, OSError):
            self.closed = True
    def send(self, b): self.s.map_sock.sendall(b)
    def quit(self):
        try: self.s.quit_game(wait=2)
        except Exception: pass
def board(c, vid):
    return [p[6:86].split(b"\0")[0].decode("latin-1") for pid, p in c.pk if pid == 0x131 and struct.unpack_from("<I", p, 2)[0] == vid]
def vlist(c, vid):
    """{nameid: (price, amount, index)} from the last 0x133 for vid."""
    last = None
    for pid, p in c.pk:
        if pid == 0x133 and struct.unpack_from("<I", p, 4)[0] == vid: last = p
    out = {}
    if last:
        for off in range(8, len(last), 22):
            price, amount, idx, typ, nameid = struct.unpack_from("<IHHBH", last, off)
            out[nameid] = (price, amount, idx)
    return out
def shop_rows(v): return sql("SELECT nameid, amount, price FROM autotrade_item WHERE char_id=%s ORDER BY nameid" % v)

try:
    stop(); start(); setup(); stop(); stock(); start()
    v, b, va = cid("ATVend"), cid("ATBuy"), int(aid("ATVend"))
    vend = Client("atvend", "ATVend"); vend.pump(3)
    items = struct.pack("<HHI", 0 + 2, 50, 1000)
    vend.send(struct.pack("<HH80sB", 0x1b2, 85 + len(items), b"Tax test", 1) + items); vend.pump(2)
    check("0 the shop opens (0x136 to the vendor)", any(pid == 0x136 for pid, _ in vend.pk))
    buy = Client("atbuy", "ATBuy"); buy.pump(3)
    buy.send(struct.pack("<HI", 0x130, va)); buy.pump(2)
    vl = vlist(buy, va)
    if POT in vl:
        buy.send(struct.pack("<HHIHH", 0x134, 12, va, 5, vl[POT][2])); buy.pump(3)
    vend.pump(1)
    buy.quit(); vend.quit(); time.sleep(4)
    zb, zv = int(sql("SELECT zeny FROM `char` WHERE char_id=%s" % b)), int(sql("SELECT zeny FROM `char` WHERE char_id=%s" % v))
    check("1 the buyer pays 5000", zb == 1000000 - 5000, "buyer zeny %d, list %s" % (zb, vl))
    check("2 the vendor gets 4900 (2 %% kept back)", zv == 1000 + 4900, "vendor zeny %d" % zv)
finally:
    stop()
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
