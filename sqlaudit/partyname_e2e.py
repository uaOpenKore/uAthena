#!/usr/bin/env python3
"""partyname_e2e.py <run dir>: a party invite by name (0x2c4) and its answer (0x2c7) -- S. 2026-11-27, for BornRok
and uaRO-HD; the old client keeps 0xfc/0xff. The invitee still gets 0xfe, so any client can answer it.
ATVend makes a party; ATBuy is asked by name.
 1 0x2c4 "ATBuy": ATBuy gets 0xfe from ATVend's account
 2 0x2c7 <party id> 0 (rAthena's form): ATVend gets 0xfd "ATBuy" 1 (rejected)
 3 asked again, 0x2c7 <inviter's account id> 1 (the 0xfe form): ATBuy is in ATVend's party
 4 0x2c4 with a name nobody plays: ATVend is told "Character 'Nobody' is not online." """
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
    stop(); start(); setup(); stop(); stock()
    v, b, va = int(cid("ATVend")), int(cid("ATBuy")), int(aid("ATVend"))
    sql("REPLACE INTO skill (char_id, id, lv) VALUES (%d, 1, 9)" % b)
    sql("UPDATE `char` SET party_id=0 WHERE char_id IN (%d,%d)" % (v, b)); sql("DELETE FROM party WHERE name='PNameTest'")
    start()
    a = Client("atvend", "ATVend"); a.pump(2)
    a.send(struct.pack("<H24s", 0xf9, b"PNameTest")); a.pump(3)
    pid_ = int(sql("SELECT party_id FROM `char` WHERE char_id=%d" % v) or 0)
    c = Client("atbuy", "ATBuy"); c.pump(2)
    a.send(struct.pack("<H24s", 0x2c4, b"ATBuy")); c.pump(2)
    inv = [struct.unpack_from("<I", p, 2)[0] for pid, p in c.pk if pid == 0xfe]
    check("1 ATBuy is invited (0xfe from ATVend's account)", va in inv and pid_ > 0, "party %d, 0xfe %s" % (pid_, inv))
    c.send(struct.pack("<HIB", 0x2c7, pid_, 0)); a.pump(2)
    acks = [(p[2:26].split(b"\0")[0], p[26]) for pid, p in a.pk if pid == 0xfd]
    check("2 rejected by party id: ATVend gets 0xfd ATBuy 1", (b"ATBuy", 1) in acks, acks)
    a.send(struct.pack("<H24s", 0x2c4, b"ATBuy")); c.pump(2)
    c.send(struct.pack("<HIB", 0x2c7, va, 1)); c.pump(3); a.pump(1)
    pb = int(sql("SELECT party_id FROM `char` WHERE char_id=%d" % b) or 0)
    inparty = pb == pid_ or any(pid == 0xfb and b"ATBuy" in p for pid, p in a.pk)
    check("3 accepted by account id: ATBuy is in the party", inparty and pid_ > 0, "ATBuy party %d" % pb)
    a.pk.clear(); a.send(struct.pack("<H24s", 0x2c4, b"Nobody")); a.pump(2)
    m = messages(a.pk)
    check("4 an unknown name: 'not online'", any("Nobody" in x and "not online" in x for x in m), m)
    a.quit(); c.quit()
finally:
    stop()
    sql("UPDATE `char` SET party_id=0 WHERE name IN ('ATVend','ATBuy')"); sql("DELETE FROM party WHERE name='PNameTest'")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
