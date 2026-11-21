#!/usr/bin/env python3
"""autotrade_e2e.py <run dir>: autotrade shops survive a server restart (S. 2026-11-21).
Vendor ATVend (Merchant, Vending 10, a cart with 50 Red Potions and 30 Apples) opens a shop (0x1b2) and goes
@autotrade; buyer ATBuy (zeny) stands next to it.
 1 @autotrade: autotrade_shop/autotrade_item rows, the vendor is not online (char.online 0, not in @who)
 2 a restart: the shop stands again (0x131 board with its title) with the same items and prices (0x133)
 3 buying 5 potions after the restart: the buyer gets them, the vendor's zeny and the row's amount follow
 4 another restart: the amounts are still right
 5 a cart item gone while the server was down: that item is skipped, the rest is sold
 6 the owner logs in: the shop goes, the rows go, the cart and zeny are intact
 7 sold out: the rows go
 8 the shutdown rewrites the tables: a row edited by hand while running is back to what the shop holds"""
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
    v, va = cid("ATVend"), int(aid("ATVend"))
    vend = Client("atvend", "ATVend"); vend.pump(3)
    # the cart slots: in the order the rows went in (the char-server loads cart_inventory by id)
    slots = {POT: 0, APPLE: 1}
    title = b"Potions and apples"
    items = struct.pack("<HHI", slots[POT] + 2, 50, 100) + struct.pack("<HHI", slots[APPLE] + 2, 30, 50)
    vend.send(struct.pack("<HH80sB", 0x1b2, 85 + len(items), title, 1) + items); vend.pump(2)
    check("0 the shop opens (0x136 to the vendor)", any(pid == 0x136 for pid, _ in vend.pk))
    chat(vend.s.map_sock, "ATVend", "@autotrade"); vend.pump(3)
    time.sleep(2)
    rows = sql("SELECT map, x, y, title FROM autotrade_shop WHERE char_id=%s" % v)
    check("1a @autotrade writes the shop row", rows.startswith("prontera\t150\t150\tPotions and apples"), "row=%r" % rows)
    check("1b and its items", shop_rows(v) == "%d\t50\t100\n%d\t30\t50" % (POT, APPLE), "items=%r" % shop_rows(v))
    check("1c the vendor is not online", sql("SELECT online FROM `char` WHERE char_id=%s" % v) == "0")
    stop(); start()
    buy = Client("atbuy", "ATBuy"); buy.pump(5)
    check("2a after a restart the shop board is back", board(buy, va) == ["Potions and apples"], "boards=%s" % board(buy, va))
    buy.send(struct.pack("<HI", 0x130, va)); buy.pump(2)
    vl = vlist(buy, va)
    check("2b with the same items and prices", vl.get(POT, (0, 0))[:2] == (100, 50) and vl.get(APPLE, (0, 0))[:2] == (50, 30), "list=%s" % vl)
    z0 = int(sql("SELECT zeny FROM `char` WHERE char_id=%s" % v))
    if POT in vl:
        buy.send(struct.pack("<HHIHH", 0x134, 12, va, 5, vl[POT][2])); buy.pump(3)
    buy.quit(); time.sleep(4)
    got = sql("SELECT SUM(amount) FROM inventory WHERE char_id=%s AND nameid=%d" % (cid("ATBuy"), POT))
    check("3a the buyer got 5 potions", got == "5", "got=%r" % got)
    check("3b the row's amount follows", shop_rows(v).startswith("%d\t45\t100" % POT), "items=%r" % shop_rows(v))
    stop()
    z1 = int(sql("SELECT zeny FROM `char` WHERE char_id=%s" % v))
    check("3c the vendor got the zeny (saved)", z1 >= z0 + 450, "zeny %d -> %d" % (z0, z1))
    # 5: an item gone from the cart while down
    sql("DELETE FROM cart_inventory WHERE char_id=%s AND nameid=%d" % (v, APPLE))
    start()
    buy = Client("atbuy", "ATBuy"); buy.pump(5); buy.send(struct.pack("<HI", 0x130, va)); buy.pump(2)
    vl = vlist(buy, va)
    check("4 another restart: the amounts are still right", vl.get(POT, (0, 0))[:2] == (100, 45), "list=%s" % vl)
    check("5 the item gone from the cart is skipped", APPLE not in vl, "list=%s" % vl)
    # 8: hand-edit while running, then a shutdown rewrites
    sql("UPDATE autotrade_item SET amount=7 WHERE char_id=%s AND nameid=%d" % (v, POT))
    buy.quit(); stop()
    check("8 the shutdown rewrites the tables from the shops", shop_rows(v) == "%d\t45\t100" % POT, "items=%r" % shop_rows(v))
    check("8b and logs it", re.search(r"\[AUTOTRADE\] saved \d+ shops?, \d+ items?", maplog()) is not None)
    start()
    # 6: the owner logs in
    buy = Client("atbuy", "ATBuy"); buy.pump(4)
    vend = Client("atvend", "ATVend"); vend.pump(3); buy.pump(3)
    check("6a the owner logs in: the rows go", sql("SELECT COUNT(*) FROM autotrade_shop WHERE char_id=%s" % v) == "0" and shop_rows(v) == "")
    cart = sql("SELECT amount FROM cart_inventory WHERE char_id=%s AND nameid=%d" % (v, POT))
    check("6b the cart is intact", cart == "45", "cart=%r" % cart)
    gone = [p for pid, p in buy.pk if pid == 0x132 and struct.unpack_from("<I", p, 2)[0] == va]
    check("6c the buyer saw the shop close", bool(gone))
    # 7: sold out
    title = b"Last potions"
    items = struct.pack("<HHI", slots[POT] + 2, 2, 10)
    vend.send(struct.pack("<HH80sB", 0x1b2, 85 + len(items), title, 1) + items); vend.pump(2)
    chat(vend.s.map_sock, "ATVend", "@autotrade"); vend.pump(3); time.sleep(2)
    buy.send(struct.pack("<HI", 0x130, va)); buy.pump(2); vl = vlist(buy, va)
    if POT in vl:
        buy.send(struct.pack("<HHIHH", 0x134, 12, va, 2, vl[POT][2])); buy.pump(3)
    time.sleep(2)
    check("7 sold out: the rows go", sql("SELECT COUNT(*) FROM autotrade_shop WHERE char_id=%s" % v) == "0" and shop_rows(v) == "",
          "shop=%s items=%r list=%s" % (sql("SELECT COUNT(*) FROM autotrade_shop WHERE char_id=%s" % v), shop_rows(v), vl))
    buy.quit()
finally:
    stop()
sys.exit(0 if ok else 1)
