#!/usr/bin/env python3
"""webstorage_e2e.py <e2e run dir>: item requests from the web site (S. 2026-11-23), on the e2e stand (ports 6900..,
the local `ragnarok` DB). The run dir gets guild_storage_lock: 1 (inter_athena.conf) for the run.
Guild G: master MASTER (account M, in game during part of the test), member MEMBER (account A, offline).
 1 move storage -> guild_storage (A offline, storage closed): done, the stack merges into the guild's
 2 A at the character select: a move of A's items waits (status 0); A leaves -> done
 3 DUPE: MASTER has the guild storage open; a move guild_storage -> A's storage waits; MASTER closes -> it runs;
   MASTER opens and closes the guild storage again: the moved potions do not come back (guild + A totals = start)
 4 add into MEMBER's inventory (a site shop): done; remove from the cart without a cart: refused;
   an unknown item: refused; a char of another account: refused; more than there is: refused, nothing taken
 5 an equipped item is not moved
 6 an autotrade shop kept in autotrade_shop: the account's requests wait until it is gone
 7 another character of the account in game: this offline one's inventory is free, the Kafra storage waits"""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/e2e/tools")
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402
run = sys.argv[1]
ICONF = os.path.join(run, "conf", "inter_athena.conf")
MY = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B"]
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def one(q):
    r = sql(q)
    return r.split("\n")[0] if r else ""
def srv(a): subprocess.run(["bash", SCR + "/e2e/tools/srv.sh", a, run], stdout=subprocess.DEVNULL)
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
L = load_lengths("/root/BornRok/src/net/PacketTable.cpp")
AM, AA, AX = 900600001, 900600002, 900600003
CM, CA, CX = 900600001, 900600002, 900600003
G = 900600001
RED = 501
def req(aid, cid, op, src, dst, nameid, amount, **kw):
    cols = "account_id,char_id,op,src,dst,nameid,amount" + "".join("," + k for k in kw)
    vals = "%d,%d,'%s','%s','%s',%d,%d" % (aid, cid, op, src, dst, nameid, amount) + "".join(",%s" % v for v in kw.values())
    sql("INSERT INTO web_storage_request (%s) VALUES (%s)" % (cols, vals))
    return int(one("SELECT MAX(id) FROM web_storage_request"))
def status(rid): return sql("SELECT status, result FROM web_storage_request WHERE id=%d" % rid)
def wait_status(rid, want, secs=20):
    t = time.time() + secs
    while time.time() < t:
        if status(rid).split("\t")[0] == want:
            return True
        time.sleep(1)
    return False
def total(nameid):
    return int(one("SELECT COALESCE(SUM(amount),0) FROM guild_storage WHERE guild_id=%d AND nameid=%d" % (G, nameid)) or 0), \
           int(one("SELECT COALESCE(SUM(amount),0) FROM storage WHERE account_id=%d AND nameid=%d" % (AA, nameid)) or 0)
def cleanup():
    sql("DELETE FROM login WHERE account_id IN (%d,%d,%d)" % (AM, AA, AX))
    sql("DELETE FROM `char` WHERE char_id IN (%d,%d,%d)" % (CM, CA, CX))
    for t in ("inventory", "cart_inventory"):
        sql("DELETE FROM %s WHERE char_id IN (%d,%d,%d)" % (t, CM, CA, CX))
    sql("DELETE FROM storage WHERE account_id IN (%d,%d,%d)" % (AM, AA, AX))
    for t in ("guild", "guild_member", "guild_position", "guild_storage"):
        sql("DELETE FROM %s WHERE guild_id=%d" % (t, G))
    sql("DROP TABLE IF EXISTS web_storage_request")
    sql("DELETE FROM autotrade_shop WHERE account_id IN (%d,%d,%d)" % (AM, AA, AX))
    if os.path.exists(ICONF + ".wsbak"):
        os.replace(ICONF + ".wsbak", ICONF)

srv("stop")
subprocess.run(MY[:-2], stdin=open(SCR + "/tick64/sql-files/upgrade_2026-11-21_autotrade.sql"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # the stand DB may not have the tables
cleanup()
s = open(ICONF).read()
open(ICONF + ".wsbak", "w").write(s)
import re
open(ICONF, "w").write(re.sub(r"(?m)^guild_storage_lock: .*$", "guild_storage_lock: 1", s))
sql("INSERT INTO login (account_id,userid,user_pass,sex,email,level) VALUES (%d,'wsmaster','wspw1','M','a@a.com',99),(%d,'wsmember','wspw2','M','a@a.com',0),(%d,'wsother','wspw3','M','a@a.com',0)" % (AM, AA, AX))
CH = "INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,guild_id,option,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) VALUES "
sql(CH + "(%d,%d,0,'WsMaster',10,50,%d,0,500,500,50,50,'prontera',150,150,'prontera',150,150),(%d,%d,0,'WsMember',5,50,%d,0,500,500,50,50,'prontera',150,150,'prontera',150,150),"
         "(%d,%d,0,'WsOther',5,50,0,0,500,500,50,50,'prontera',150,150,'prontera',150,150)" % (CM, AM, G, CA, AA, G, CX, AX))
sql("INSERT INTO guild (guild_id,name,char_id,master,guild_lv,max_member) VALUES (%d,'WsGuild',%d,'WsMaster',1,16)" % (G, CM))
sql("INSERT INTO guild_member (guild_id,account_id,char_id,name,position) VALUES (%d,%d,%d,'WsMaster',0),(%d,%d,%d,'WsMember',1)" % (G, AM, CM, G, AA, CA))
sql("INSERT INTO guild_position (guild_id,position,name,mode) VALUES (%d,0,'Master',17),(%d,1,'Member',0)" % (G, G))
sql("INSERT INTO storage (account_id,nameid,amount,identify) VALUES (%d,%d,30,1)" % (AA, RED))
sql("INSERT INTO guild_storage (guild_id,nameid,amount,identify) VALUES (%d,%d,100,1)" % (G, RED))
sql("INSERT INTO inventory (char_id,nameid,amount,identify,equip) VALUES (%d,1201,1,1,2)" % CA)  # an equipped knife
try:
    srv("start"); time.sleep(4)
    if not sql("SHOW TABLES LIKE 'web_storage_request'"):
        time.sleep(3)
    r1 = req(AA, CA, "move", "storage", "guild_storage", RED, 10)
    done1 = wait_status(r1, "1")
    g, a = total(RED)
    check("1 storage -> guild_storage done, merged", done1 and g == 110 and a == 20 and one("SELECT COUNT(*) FROM guild_storage WHERE guild_id=%d AND nameid=%d" % (G, RED)) == "1",
          "%s g=%d a=%d" % (status(r1), g, a))
    mem = rostub.Session("wsmember", "wspw2", log=lambda *x: None); mem.login(); mem.char_enter()
    r2 = req(AA, CA, "move", "storage", "guild_storage", RED, 5)
    time.sleep(8)
    waiting = status(r2)
    try: mem.char_sock.close()
    except Exception: pass
    done2 = wait_status(r2, "1", 260)
    g, a = total(RED)
    check("2 account at the character select: waits; after it leaves: done", waiting.startswith("0") and done2 and g == 115 and a == 15, "waiting=%r %s g=%d a=%d" % (waiting, status(r2), g, a))
    # 3 the dupe: MASTER opens the guild storage in game
    ms = rostub.Session("wsmaster", "wspw1", log=lambda *x: None); ms.login(); ms.char_enter(); ms.select_char(0)
    assert ms.map_enter()[0] == "ok"
    st = Stream(ms.map_sock, L)
    for _ in st.packets(2): pass
    def say(text):
        m = ("WsMaster : " + text).encode("latin-1") + b"\0"
        ms.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(m)) + m)
    say("@gstorage")
    got = [pid for pid, p in st.packets(3)]
    r3 = req(AA, CA, "move", "guild_storage", "storage", RED, 40)
    time.sleep(8)
    waiting3 = status(r3)
    ms.map_sock.sendall(struct.pack("<H", 0x193))  # close the storage
    for _ in st.packets(2): pass
    done3 = wait_status(r3, "1", 90)
    g3, a3 = total(RED)
    say("@gstorage")   # open again: a stale copy would bring the 40 back on the next close
    for _ in st.packets(3): pass
    ms.map_sock.sendall(struct.pack("<H", 0x193))
    for _ in st.packets(2): pass
    try: ms.quit_game(wait=2)
    except Exception: pass
    time.sleep(3)
    g4, a4 = total(RED)
    check("3 dupe: waits while open, runs after the close; reopen + close brings nothing back",
          waiting3.startswith("0") and "open" in waiting3 and done3 and (g3, a3) == (75, 55) and (g4, a4) == (75, 55) and g4 + a4 == 130,
          "opened=%s waiting=%r %s after=%s again=%s" % ([hex(x) for x in got if x in (0x1f0, 0x2d1, 0xa5, 0x1f2)], waiting3, status(r3), (g3, a3), (g4, a4)))
    r4 = req(AA, CA, "add", "", "inventory", 502, 3)
    r5 = req(AA, CA, "remove", "cart", "", RED, 1)
    r6 = req(AA, CA, "add", "", "storage", 59999, 1)
    r7 = req(AX, CA, "move", "storage", "inventory", RED, 1)
    r8 = req(AA, CA, "move", "storage", "inventory", RED, 9999)
    for r in (r4, r5, r6, r7, r8):
        wait_status(r, "1", 15) or wait_status(r, "2", 1)
    res = {r: status(r) for r in (r4, r5, r6, r7, r8)}
    check("4 add into the inventory; no cart / unknown item / other account / too many: refused, nothing taken",
          res[r4].startswith("1") and one("SELECT SUM(amount) FROM inventory WHERE char_id=%d AND nameid=502" % CA) == "3"
          and res[r5].startswith("2") and "cart" in res[r5] and res[r6].startswith("2") and "no such item" in res[r6]
          and res[r7].startswith("2") and "account" in res[r7] and res[r8].startswith("2") and total(RED)[1] == 55, str(res))
    # 6 an autotrade shop kept in the table (even while not on the server): the account's requests wait
    sql("INSERT INTO autotrade_shop (char_id,account_id,sex,map,x,y,dir,title,opened) VALUES (%d,%d,1,'prontera',150,150,0,'ws',NOW())" % (CA, AA))
    r10 = req(AA, CA, "move", "storage", "inventory", RED, 1)
    time.sleep(8)
    w10 = status(r10)
    sql("DELETE FROM autotrade_shop WHERE char_id=%d" % CA)
    d10 = wait_status(r10, "1", 20)
    check("6 an autotrade shop in the table: waits; shop gone: done", w10.startswith("0") and "autotrade" in w10 and d10, "%r %s" % (w10, status(r10)))
    r9 = req(AA, CA, "move", "inventory", "storage", 1201, 1)
    wait_status(r9, "2", 15)
    check("5 an equipped item is not moved", status(r9).startswith("2") and one("SELECT equip FROM inventory WHERE char_id=%d AND nameid=1201" % CA) == "2", status(r9))
    # 7 the account plays another character: this offline one's inventory is free, the Kafra storage is not
    sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
        "VALUES (900600004,%d,1,'WsMember2',1,10,100,100,10,10,'prontera',150,150,'prontera',150,150)" % AA)
    p2 = rostub.Session("wsmember", "wspw2", log=lambda *x: None); p2.login(); p2.char_enter(); p2.select_char(1)
    assert p2.map_enter()[0] == "ok"
    time.sleep(2)
    r11 = req(AA, CA, "add", "", "inventory", 503, 2)
    r12 = req(AA, CA, "move", "storage", "inventory", RED, 1)
    d11 = wait_status(r11, "1", 20)
    time.sleep(4)
    w12 = status(r12)
    try: p2.quit_game(wait=2)
    except Exception: pass
    check("7 another char of the account in game: the offline char's inventory done, the Kafra storage waits",
          d11 and one("SELECT SUM(amount) FROM inventory WHERE char_id=%d AND nameid=503" % CA) == "2" and w12.startswith("0") and "Kafra" in w12,
          "%s / %r" % (status(r11), w12))
    sql("DELETE FROM web_storage_request WHERE id=%d" % r12)
    sql("DELETE FROM `char` WHERE char_id=900600004")
finally:
    srv("stop")
    print(subprocess.run("sed 's/\\x1b\\[[0-9;]*m//g' %s/char.out | grep -a 'WEBSTORAGE' | tail -12" % run, shell=True, stdout=subprocess.PIPE, text=True).stdout)
    cleanup()
    sql("ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
