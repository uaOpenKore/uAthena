#!/usr/bin/env python3
"""friendadd_e2e.py <run dir>: "friend added" (0x209) carries the friend's full account and character ids
(S. 2026-11-27: WFIFOW wrote 2 bytes of the 4-byte fields, so ids above 65535 reached the client cut, the upper
bytes whatever was in the buffer). ATVend asks ATBuy (0x202), ATBuy accepts (0x208).
 1 ATVend gets 0x209 type 0 with ATBuy's account id and char id in full
 2 ATBuy gets 0x209 type 0 with ATVend's ids in full"""
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

def acks(c):
    return [struct.unpack_from("<HII", p, 2) for pid, p in c.pk if pid == 0x209]
try:
    stop(); start(); setup(); stop(); stock(); start()
    v, b, va, ba = int(cid("ATVend")), int(cid("ATBuy")), int(aid("ATVend")), int(aid("ATBuy"))
    sql("DELETE FROM friends WHERE char_id IN (%d,%d) OR friend_id IN (%d,%d)" % (v, b, v, b))
    a = Client("atvend", "ATVend"); a.pump(2)
    c = Client("atbuy", "ATBuy"); c.pump(2)
    a.send(struct.pack("<H24s", 0x202, b"ATBuy")); c.pump(2)
    req = [p for pid, p in c.pk if pid == 0x207]
    if req:
        c.send(struct.pack("<HIIB", 0x208, va, v, 1) + b"\0" * 3)
    c.pump(2); a.pump(2)
    check("1 ATVend: 0x209 type 0 with ATBuy's ids", (0, ba, b) in acks(a), "0x207 %d, got %s, want %s" % (len(req), acks(a), (0, ba, b)))
    check("2 ATBuy: 0x209 type 0 with ATVend's ids", (0, va, v) in acks(c), "got %s, want %s" % (acks(c), (0, va, v)))
    a.quit(); c.quit()
finally:
    sql("DELETE FROM friends WHERE char_id IN (SELECT char_id FROM `char` WHERE name IN ('ATVend','ATBuy'))")
    stop()
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
