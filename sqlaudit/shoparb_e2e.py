#!/usr/bin/env python3
"""shoparb_e2e.py <e2e run dir>: buying from an NPC shop and selling back to an NPC must never pay (S. 2026-11-21).
On the e2e stand (ports 6900.., the local `ragnarok` DB, the npc/ of the worktree), with a test shop
"ShopArb Test" (npc_test/shoparb_shop.txt) selling Oridecon Arrows at 3 like Arrow Quivers did: 100 bought and
sold back; before the fix an NPC paid 15 each (+1200), now at most what the shop asks with the best discount (2
each). And Arrow Quivers itself sells them at the item_db price now (30), no shop sells below it."""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/e2e/tools")
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402
run = sys.argv[1]
MY = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B"]
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def srv(a): subprocess.run(["bash", SCR + "/e2e/tools/srv.sh", a, run], stdout=subprocess.DEVNULL)
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
A = C = 900100000
L = load_lengths("/root/BornRok/src/net/PacketTable.cpp")
srv("stop")
TESTNPC = os.path.join(run, "e2e_npc", "shoparb_shop.txt")
subprocess.run(["cp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "npc_test", "shoparb_shop.txt"), TESTNPC])
MC = os.path.join(run, "conf", "import", "map_conf.txt")
if "shoparb_shop.txt" not in open(MC).read():
    open(MC, "a").write("npc: e2e_npc/shoparb_shop.txt\n")
sql("DELETE FROM inventory WHERE char_id=%d; DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d" % (C, C, A))
sql("INSERT INTO login (account_id,userid,user_pass,sex,email) VALUES (%d,'shoparb','sapw1','M','a@a.com')" % A)
sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,zeny,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
    "VALUES (%d,%d,0,'ShopArb',0,10,9,1000,100,100,10,10,'geffen',123,109,'geffen',123,109)" % (C, A))
srv("start"); time.sleep(3)
try:
    s = rostub.Session("shoparb", "sapw1", log=lambda *a: None); s.login(); s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, L); pk = list(st.packets(3))
    ids = set(struct.unpack_from("<I", p, 2)[0] for pid, p in pk if pid in (0x78, 0x7c, 0x22a, 0x22b))
    names = {}
    for i in ids:
        s.map_sock.sendall(struct.pack("<H5sI", 0x8c, bytes(5), i))  # v22 getcharnamerequest: the id at 7
    for pid, p in st.packets(2):
        if pid == 0x95: names[struct.unpack_from("<I", p, 2)[0]] = p[6:30].split(b"\0")[0].decode("latin-1")
    shop = [i for i, n in names.items() if n.startswith("ShopArb Test")]
    aq = [i for i, n in names.items() if n.startswith("Arrow Quivers")]
    check("0 the test shop and Arrow Quivers are next to the character", bool(shop) and bool(aq), "names=%s" % list(names.values())[:10])
    s.map_sock.sendall(struct.pack("<HIB", 0x90, aq[0], 1)); list(st.packets(1))
    s.map_sock.sendall(struct.pack("<HIB", 0xc5, aq[0], 0)); pk = list(st.packets(1))
    aqprice = [struct.unpack_from("<i", p, 4 + 11 * k)[0] for pid, p in pk if pid == 0xc6 for k in range((len(p) - 4) // 11)
               if struct.unpack_from("<H", p, 4 + 11 * k + 9)[0] == 1765]
    check("0b Arrow Quivers sells Oridecon Arrows at the item_db price (30), not 3", aqprice[:1] == [30], "price=%s" % aqprice)
    def zeny_now(pkts, z):
        for pid, p in pkts:
            if pid == 0xb1 and struct.unpack_from("<H", p, 2)[0] == 20: z = struct.unpack_from("<i", p, 4)[0]
        return z
    z = 1000
    # buy 100 Oridecon Arrows
    s.map_sock.sendall(struct.pack("<HIB", 0x90, shop[0], 1)); z = zeny_now(st.packets(1), z)
    s.map_sock.sendall(struct.pack("<HIB", 0xc5, shop[0], 0)); z = zeny_now(st.packets(1), z)
    s.map_sock.sendall(struct.pack("<HHHH", 0xc8, 8, 100, 1765)); pk = list(st.packets(2)); z = zeny_now(pk, z)
    idx = None
    for pid, p in pk:
        if pid == 0xa0 and struct.unpack_from("<H", p, 6)[0] == 1765: idx = struct.unpack_from("<H", p, 2)[0]
    z_after_buy = z
    check("1 bought 100 Oridecon Arrows for 300", z_after_buy == 700 and idx is not None, "zeny=%s idx=%s" % (z, idx))
    # sell them back
    s.map_sock.sendall(struct.pack("<HIB", 0x90, shop[0], 1)); z = zeny_now(st.packets(1), z)
    s.map_sock.sendall(struct.pack("<HIB", 0xc5, shop[0], 1)); pk = list(st.packets(1)); z = zeny_now(pk, z)
    shown = [struct.unpack_from("<i", p, 10 + 10 * k)[0] for pid, p in pk if pid == 0xc7 for k in range((len(p) - 4) // 10)
             if struct.unpack_from("<H", p, 4 + 10 * k)[0] == (idx or -1)]
    s.map_sock.sendall(struct.pack("<HHHH", 0xc9, 8, idx or 0, 100)); z = zeny_now(st.packets(2), z)
    check("2 selling them back to an NPC does not pay (zeny never above the 1000 it started with)", z <= 1000,
          "zeny after selling: %s (price shown in the sell window: %s)" % (z, shown))
    check("3 the sell window shows what is really paid (2 a piece)", shown == [2], "shown=%s" % shown)
    try: s.quit_game(wait=2)
    except Exception: pass
    log = open(os.path.join(run, "map.out"), errors="replace").read()
    check("4 the capped items are listed at start", "[shoparb] Oridecon Arrow (1765)" in log or "[shoparb]" in log)
finally:
    srv("stop")
    sql("DELETE FROM inventory WHERE char_id=%d; DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d;"
        " ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1" % (C, C, A))
sys.exit(0 if ok else 1)
