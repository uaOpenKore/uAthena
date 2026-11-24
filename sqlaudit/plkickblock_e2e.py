#!/usr/bin/env python3
"""plkickblock_e2e.py <run dir>: an account kicked again and again for the daily play limit is refused at the
login-server for a while, in memory (S. 2026-11-24: OpenKore relogs every ~40 s after the kick -- 93 accounts made
27 500 kicks in 12 h; "after 10 kicks a delay of an hour, not the ban list, forgotten by a restart").
The stand runs with playtime_kick_block_after 2 / playtime_kick_block_minutes 1 (set for this test, restored after).
 1 a character past its limit is kicked (as before)
 2 the 2nd kick: the map-server logs the block, the login-server logs the refusal window
 3 the next login is refused with 0x6a code 6 (prohibited until ...)
 4 nothing is written to the ban list / login.ban_until
 5 after the minute it can log in again"""
import datetime, os, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import enter_map  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def log(name): return open(os.path.join(run, name + ".out"), errors="replace").read()
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
CONF = os.path.join(run, "conf/import/battle_conf.txt")
orig = open(CONF).read()
U, N = "plkb", "PlKb"
try:
    srv("stop")
    open(CONF, "w").write(orig + "playtime_kick_block_after: 2\nplaytime_kick_block_minutes: 1\n")
    srv("start"); time.sleep(5)
    if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % U) == "0":
        try: rostub.Session(U + "_M", "plkbpw1", log=lambda *a: None).login()
        except Exception: pass
        time.sleep(1)
    if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % U) == "0":
        s = enter_map(U, "plkbpw1", N, log=lambda *a: None); s.quit_game(wait=2); time.sleep(3)
    srv("stop")
    today = int(datetime.date.today().strftime("%Y%m%d"))
    sql("UPDATE login SET level=0, ban_until=0 WHERE userid='%s'" % U)
    sql("UPDATE `char` SET play_minutes=900, play_date=%d WHERE name='%s'" % (today, N))
    sql("REPLACE INTO play_reset (id, reset_date, reset_at) VALUES (0, %d, NOW())" % today)
    m0, l0 = 0, 0
    srv("start"); time.sleep(5)
    m0, l0 = len(log("map")), len(log("login"))
    kicks = 0
    for i in range(2):
        s = enter_map(U, "plkbpw1", N, log=lambda *a: None)
        s.map_sock.settimeout(70)
        t0 = time.time()
        try:
            while s.map_sock.recv(4096): pass
        except OSError: pass
        if time.time() - t0 < 65: kicks += 1
        time.sleep(3)
    ml, ll = log("map")[m0:], log("login")[l0:]
    check("1 the character past its limit is kicked (twice)", kicks == 2 and ml.count("[PLAYLIMIT] kick") >= 2, "kicks=%d" % kicks)
    check("2 the 2nd kick blocks the account (map + login logs)", "[PLAYLIMIT] block" in ml and "logins refused for 1 min" in ll,
          [l for l in (ml + ll).splitlines() if "PLAYLIMIT" in l][-4:])
    try:
        rostub.Session(U, "plkbpw1", log=lambda *a: None).login(); refused = ""
    except RuntimeError as e:
        refused = str(e)
    check("3 the next login is refused with code 6", "0x6a code=6" in refused, refused)
    check("4 not in the ban list (login.ban_until stays 0)", sql("SELECT ban_until FROM login WHERE userid='%s'" % U) == "0")
    time.sleep(62)
    try:
        rostub.Session(U, "plkbpw1", log=lambda *a: None).login(); again = True
    except RuntimeError: again = False
    check("5 after the minute it logs in again", again)
finally:
    srv("stop")
    open(CONF, "w").write(orig)
    sql("UPDATE `char` SET play_minutes=0 WHERE name='%s'" % N)
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
