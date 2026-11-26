#!/usr/bin/env python3
"""storagefinal_e2e.py <run dir>: a storage save still failing at shutdown is retried with the item db loaded.
Prod 26.11 03:01: char-server SIGSEGV in do_final. do_final_itemdb() ran before inter_final(), whose last try of the
failed storage saves (SKNOTYB's, failing since 23.11) goes storage_tosql -> memitemdata_to_sql -> itemdb_isequip
-> idb_ensure on the freed item db. On the isolated SQL stand (MariaDB 13306):
 1 the storage save fails while the server runs (a BEFORE UPDATE trigger on `storage` refuses it) and is kept pending
 2 at the stop the char-server runs to "ok! all done..." (no crash) and reports the storage it could not save"""
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
USER, PW, NAME = "storfin", "sfpw1", "StorFin"
TRIG = "DROP TRIGGER IF EXISTS e2e_storage_refuse"
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
    sql(TRIG)
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
    aid = sql("SELECT account_id FROM login WHERE userid='%s'" % USER)
    sql("UPDATE login SET level=99 WHERE account_id=%s" % aid)
    sql("DELETE FROM storage WHERE account_id=%s; INSERT INTO storage (account_id,nameid,amount,identify) VALUES (%s,909,10,1)" % (aid, aid))
    mc = mark("char.out"); srv("start"); time.sleep(5)
    s = enter(); st = Stream(s.map_sock, L); list(st.packets(2))
    chat(s.map_sock, NAME, "@storage"); list(st.packets(3))
    # the char-server holds 10 Jellopy; the DB row now differs, so the save on close is an UPDATE -- refused
    sql("UPDATE storage SET amount=5 WHERE account_id=%s AND nameid=909" % aid)
    sql("CREATE TRIGGER e2e_storage_refuse BEFORE UPDATE ON storage FOR EACH ROW "
        "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='e2e: storage save refused'")
    chat(s.map_sock, NAME, "@item 501 1"); list(st.packets(1))
    chat(s.map_sock, NAME, "@storeall"); list(st.packets(2))  # the storage changed: the close saves it
    s.map_sock.sendall(struct.pack("<H", 0xf7)); list(st.packets(2))  # close the storage: it is saved (and fails)
    try: s.quit_game(wait=3)
    except Exception: pass
    time.sleep(4)
    out = since("char.out", mc)
    check("1 the storage save failed while running", "e2e: storage save refused" in out,
          [l for l in out.splitlines() if "storage" in l.lower()][-5:])
    mc2 = mark("char.out"); srv("stop"); time.sleep(1)
    fin = since("char.out", mc2)
    check("2 char-server stops cleanly with the save pending", "ok! all done" in fin and "could not be saved before shutdown" in fin,
          fin.splitlines()[-6:])
finally:
    sql(TRIG)
    srv("stop")
    try:
        sql("UPDATE login SET level=0 WHERE userid='%s'" % USER)
    except Exception: pass
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
