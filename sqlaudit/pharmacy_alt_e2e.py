#!/usr/bin/env python3
"""pharmacy_alt_e2e.py <e2e run dir>: Red Potion brews with an Empty Bottle when the Empty Potion Bottle is missing
(S. 2026-11-22: "Empty Potion Bottle OR Empty Bottle" for Red/Yellow/White Potion). On the e2e stand (ports
6900.., the local `ragnarok` DB, the worktree's db/). An Alchemist with Prepare Potion 10, the guide, Medicine
Bowls, Red Herbs and Empty Bottles only:
 1 Prepare Potion offers Red Potion (0x18d lists it once)
 2 brewing until one succeeds: Red Potions are made, Empty Bottles are spent, no Empty Potion Bottle needed
 3 Prepare Potion costs 0 SP (S. 22.11: 5 -> 1 -> 0) and no Medicine Bowl (db/skill_require_db.txt)
 4 combat bottles still need a Medicine Bowl: no bowl -> Acid Bottle is not offered (S. 2026-11-22)"""
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
A = C = 900400000
L = load_lengths("/root/BornRok/src/net/PacketTable.cpp")
GUIDE, BOWL, HERB, BOTTLE, POTBOTTLE, REDPOT = 7144, 7134, 507, 713, 1093, 501
def count(nameid): return int(sql("SELECT COALESCE(SUM(amount),0) FROM inventory WHERE char_id=%d AND nameid=%d" % (C, nameid)) or 0)
srv("stop")
sql("DELETE FROM skill WHERE char_id=%d; DELETE FROM inventory WHERE char_id=%d; DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d" % (C, C, C, A))
sql("INSERT INTO login (account_id,userid,user_pass,sex,email,level) VALUES (%d,'pharmalt','phpw1','M','a@a.com',99)" % A)
sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,str,agi,vit,`int`,dex,luk,zeny,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
    "VALUES (%d,%d,0,'PharmAlt',18,90,50,1,1,1,99,99,99,1000,3000,3000,500,500,'prontera',150,150,'prontera',150,150)" % (C, A))
sql("INSERT INTO skill (char_id,id,lv) VALUES (%d,228,10),(%d,227,10)" % (C, C))  # Prepare Potion 10, Learning Potion 10
sql("INSERT INTO inventory (char_id,nameid,amount,identify) VALUES (%d,%d,1,1),(%d,%d,30,1),(%d,%d,30,1),(%d,7129,1,1),(%d,929,5,1)"
    % (C, GUIDE, C, HERB, C, BOTTLE, C, C))  # + Acid Bottle guide and Immortal Hearts  # no Medicine Bowl: not needed any more (S. 22.11)
try:
    srv("start"); time.sleep(3)
    s = rostub.Session("pharmalt", "phpw1", log=lambda *a: None); s.login(); s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, L); sp0 = None
    for pid, p in st.packets(2):
        if pid == 0xb0 and struct.unpack_from("<H", p, 2)[0] == 7: sp0 = struct.unpack_from("<i", p, 4)[0]
    msg = ("PharmAlt : @allskill").encode("latin-1") + b"\0"  # the SQL skill rows alone are dropped at login
    s.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
    for pid, p in st.packets(3):
        if pid == 0xb0 and struct.unpack_from("<H", p, 2)[0] == 7: sp0 = struct.unpack_from("<i", p, 4)[0]
    listed, made, sp_after, tries = [], 0, None, 0
    while tries < 20 and made == 0:
        tries += 1
        s.map_sock.sendall(struct.pack("<H", 0x72) + b"\0" * 4 + struct.pack("<H", 10) + b"\0" * 2 + struct.pack("<H", 228)
                           + b"\0" * 9 + struct.pack("<I", A))
        for pid, p in st.packets(1.5):
            if pid == 0x18d:
                listed = [struct.unpack_from("<H", p, 4 + 8 * k)[0] for k in range((struct.unpack_from("<H", p, 2)[0] - 4) // 8)]
            if pid == 0xb0 and struct.unpack_from("<H", p, 2)[0] == 7: sp_after = struct.unpack_from("<i", p, 4)[0]
        if tries == 1:
            check("1 Prepare Potion offers Red Potion, listed once", listed.count(REDPOT) == 1, "list=%s" % listed)
            sp_first = sp_after
            check("4 Acid Bottle not offered without a Medicine Bowl", 7136 not in listed, "list=%s" % listed)
        s.map_sock.sendall(struct.pack("<HHHHH", 0x18e, REDPOT, 0, 0, 0))
        for pid, p in st.packets(1.5):
            if pid == 0x18f and struct.unpack_from("<H", p, 2)[0] == 0: made += 1  # produce effect: 0 = success
            if pid == 0xa0 and struct.unpack_from("<H", p, 6)[0] == REDPOT: made += 1
    try: s.quit_game(wait=2)
    except Exception: pass
    time.sleep(2)
    red, bottles, herbs = count(REDPOT), count(BOTTLE), count(HERB)
    check("2 Red Potions brewed with Empty Bottles (no Empty Potion Bottle)", red >= 1 and bottles < 30 and herbs < 30 and count(POTBOTTLE) == 0,
          "red=%d bottles=%d herbs=%d tries=%d" % (red, bottles, herbs, tries))
    check("3 Prepare Potion costs 0 SP", sp0 is not None and (sp_first is None or sp_first == sp0), "sp %s -> %s" % (sp0, sp_first))
finally:
    srv("stop")
    sql("DELETE FROM skill WHERE char_id=%d; DELETE FROM inventory WHERE char_id=%d; DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d;"
        " ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1" % (C, C, C, A))
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
