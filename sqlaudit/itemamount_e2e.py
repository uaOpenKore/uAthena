#!/usr/bin/env python3
"""itemamount_e2e.py <run dir>: a stack above MAX_AMOUNT (32766) in the DB is split on load, and the saves work again.
Prod 23-25.11: a storage row with 34148 loaded as -31388 (short), every save of that storage failed with "Out of range
value for column 'amount'" and was rolled back (2237 times on 25.11). On the isolated SQL stand (MariaDB 13306):
 1 an inventory row of 40000 Red Potions: after login + logout the DB holds 32766 + 7234 and the save had no SQL error
 2 a storage row of 34148 Jellopy (opened with @storage): after closing, 32766 + 1382 in the DB, no "Out of range"
 3 char.out reports both splits ([ITEMAMOUNT])"""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, load_lengths, enter_map, chat  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
L = load_lengths()
USER, PW, NAME = "itemamt", "iapw1", "ItemAmt"
def mark(n): p = os.path.join(run, n); return os.path.getsize(p) if os.path.exists(p) else 0
def since(n, m):
    with open(os.path.join(run, n), errors="replace") as f:
        f.seek(m); return f.read()
def enter():
    for k in range(10):
        try:
            s = rostub.Session(USER, PW, log=lambda *a: None); s.login(); break
        except RuntimeError:
            if k == 9: raise
            time.sleep(2)
    s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    return s
try:
    srv("stop"); srv("start"); time.sleep(5)
    if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % USER) == "0":
        for k in range(10):
            try: rostub.Session(USER + "_M", PW, log=lambda *a: None).login()
            except Exception: pass
            time.sleep(2)
            if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % USER) != "0": break
    if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % USER) == "0":
        for k in range(10):
            try:
                s = enter_map(USER, PW, NAME, log=lambda *a: None); break
            except RuntimeError:
                if k == 9: raise
                time.sleep(2)
        s.quit_game(wait=2); time.sleep(3)
    srv("stop")
    aid = sql("SELECT account_id FROM login WHERE userid='%s'" % USER); cid = sql("SELECT char_id FROM `char` WHERE name='%s'" % NAME)
    sql("UPDATE login SET level=99 WHERE account_id=%s" % aid)
    sql("DELETE FROM inventory WHERE char_id=%s AND nameid=501; INSERT INTO inventory (char_id,nameid,amount,identify) VALUES (%s,501,40000,1)" % (cid, cid))
    sql("DELETE FROM storage WHERE account_id=%s; INSERT INTO storage (account_id,nameid,amount,identify) VALUES (%s,909,34148,1)" % (aid, aid))
    mc = mark("char.out"); srv("start"); time.sleep(5)
    s = enter(); st = Stream(s.map_sock, L); list(st.packets(2))
    chat(s.map_sock, NAME, "@storage"); list(st.packets(3))
    s.map_sock.sendall(struct.pack("<H", 0xf7)); list(st.packets(2))  # close the storage: it is saved
    try: s.quit_game(wait=3)
    except Exception: pass
    time.sleep(8)
    inv = sql("SELECT amount FROM inventory WHERE char_id=%s AND nameid=501 ORDER BY amount DESC" % cid).split("\n")
    stor = sql("SELECT amount FROM storage WHERE account_id=%s AND nameid=909 ORDER BY amount DESC" % aid).split("\n")
    out = since("char.out", mc)
    check("1 inventory 40000 -> 32766 + 7234", inv == ["32766", "7234"], "inv=%s" % inv)
    check("2 storage 34148 -> 32766 + 1382, no 'Out of range'", stor == ["32766", "1382"] and "Out of range" not in out, "stor=%s" % stor)
    check("3 char.out reports both splits", out.count("[ITEMAMOUNT]") >= 2 and "item 909 had 34148" in out and "item 501 had 40000" in out,
          [l for l in out.splitlines() if "ITEMAMOUNT" in l])
finally:
    srv("stop")
    try:
        sql("UPDATE login SET level=0 WHERE userid='%s'" % USER)
    except Exception: pass
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
