#!/usr/bin/env python3
"""shops_rathena_e2e.py <e2e run dir>: the backported rAthena shops with a discount flag (SPRITE,no,id:price) load
(S. 2026-11-22: "callshop: Shop [Runes_Seller] not found" in the prod log). On the e2e stand (ports 6900..,
the local `ragnarok` DB, the worktree's npc/).
 1 Rune Merchant#prt (prontera 168,228): clicking opens Runes_Seller with General Rough Runestone (12737) at 1000
 2 Point Merchant#Prontera (prt_in 131,66): Shard_Seller with Scarlet Point (6360) at 200
 3 the map-server start has no 'callshop' / 'bad shop line' errors and no Gemstone Bagger NPC is loaded"""
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
A = C = 900300000
L = load_lengths("/root/BornRok/src/net/PacketTable.cpp")
def place(m, x, y):
    sql("UPDATE `char` SET last_map='%s', last_x=%d, last_y=%d, online=0 WHERE char_id=%d" % (m, x, y, C))
def shop_of(npc_prefix):
    s = rostub.Session("shoprath", "srpw1", log=lambda *a: None); s.login(); s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, L); pk = list(st.packets(3))
    ids = set(struct.unpack_from("<I", p, 2)[0] for pid, p in pk if pid in (0x78, 0x7c))
    for i in ids:
        s.map_sock.sendall(struct.pack("<H5sI", 0x8c, bytes(5), i))
    names = {}
    for pid, p in st.packets(2):
        if pid == 0x95: names[struct.unpack_from("<I", p, 2)[0]] = p[6:30].split(b"\0")[0].decode("latin-1")
    npc = [i for i, n in names.items() if n.startswith(npc_prefix)]
    items = {}
    if npc:
        s.map_sock.sendall(struct.pack("<HIB", 0x90, npc[0], 1))
        for pid, p in st.packets(3):
            if pid == 0xc6:
                for k in range((len(p) - 4) // 11):
                    price, _dc, _t, nameid = struct.unpack_from("<iiBH", p, 4 + 11 * k)
                    items[nameid] = price
    try: s.quit_game(wait=2)
    except Exception: pass
    return npc, items, list(names.values())
srv("stop")
sql("DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d" % (C, A))
sql("INSERT INTO login (account_id,userid,user_pass,sex,email) VALUES (%d,'shoprath','srpw1','M','a@a.com')" % A)
sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,zeny,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
    "VALUES (%d,%d,0,'ShopRath',0,10,9,1000,100,100,10,10,'prontera',167,226,'prontera',150,150)" % (C, A))
n0 = len(open(os.path.join(run, "map.out"), errors="replace").read()) if os.path.exists(os.path.join(run, "map.out")) else 0
try:
    srv("start"); time.sleep(3)
    npc, items, names = shop_of("Rune Merchant")
    check("1 Rune Merchant opens Runes_Seller: General Rough Runestone at 1000", items.get(12737) == 1000, "npc=%s items=%s names=%s" % (npc, items, names[:8]))
    time.sleep(2); place("prt_in", 131, 64)
    npc, items, names = shop_of("Point Merchant")
    check("2 Point Merchant opens Shard_Seller: Scarlet Point at 200", items.get(6360) == 200, "npc=%s items=%s names=%s" % (npc, items, names[:8]))
    log = open(os.path.join(run, "map.out"), errors="replace").read()[n0:]
    check("3 no callshop / bad shop line errors, no Gemstone Bagger", "buildin_callshop" not in log and "bad shop line" not in log
          and "Gemstone_Bagger.txt" not in log, [l for l in log.splitlines() if "callshop" in l or "bad shop" in l][:3])
finally:
    srv("stop")
    sql("DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d; ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1" % (C, A))
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
