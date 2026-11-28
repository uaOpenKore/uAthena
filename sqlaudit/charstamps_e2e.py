#!/usr/bin/env python3
"""charstamps_e2e.py <run dir>: two dates in the char table (S. 2026-11-28): `created` = when the character was made,
`maxed` = when it first reached base 99 and job 70. On the isolated SQL stand, after
sql-files/upgrade_2026-11-28_char_dates.sql:
 1 a character made now has `created` = now
 2 98/70 -> @blevel 1 -> after the save `maxed` = now
 3 a stored `maxed` is kept: down to 98 and back to 99 does not change it
 4 a character already at 99/70 before the columns came keeps `maxed` NULL after a session (its date is unknown)
 5 without the columns the char-server still lets the character in and says the dates are off"""
import os, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, load_lengths, enter_map, chat  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
UPGRADE = sys.argv[2]  # sql-files/upgrade_2026-11-28_char_dates.sql of the tree under test
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B"]
def sql(q): return subprocess.run(MYSQL + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % (d,)) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
L = load_lengths()
PW = "cdpw1"
A, B = ("chardate1", "CharDate1"), ("chardate2", "CharDate2")

def ensure_account(u):
    if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) != "0": return
    for k in range(10):
        try: rostub.Session(u + "_M", PW, log=lambda *a: None).login()
        except Exception: pass
        time.sleep(2)
        if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) != "0": return
    raise RuntimeError("no account " + u)

def session(u, n, cmds=()):
    for k in range(10):
        try:
            s = enter_map(u, PW, n, log=lambda *a: None); break
        except RuntimeError:
            if k == 9: raise
            time.sleep(2)
    st = Stream(s.map_sock, L); list(st.packets(2))
    for c in cmds:
        chat(s.map_sock, n, c); list(st.packets(2))
    try: s.quit_game(wait=2)
    except Exception: pass
    time.sleep(3)

def secs_ago(col, n):
    v = sql("SELECT IFNULL(TIMESTAMPDIFF(SECOND, `%s`, NOW()), 'NULL') FROM `char` WHERE name='%s'" % (col, n))
    return None if v in ("NULL", "") else int(v) if v.lstrip("-").isdigit() else v

def drop_cols():
    for c in ("created", "maxed"):
        if sql("SHOW COLUMNS FROM `char` LIKE '%s'" % c): sql("ALTER TABLE `char` DROP COLUMN `%s`" % c)

try:
    srv("stop"); srv("start"); time.sleep(5)
    for u, n in (A, B):
        ensure_account(u)
    srv("stop")
    drop_cols()
    sql("DELETE c FROM `char` c JOIN login l USING(account_id) WHERE l.userid IN ('%s','%s')" % (A[0], B[0]))
    sql("UPDATE login SET level=99 WHERE userid IN ('%s','%s')" % (A[0], B[0]))
    # B exists before the columns and is already 99/70
    srv("start"); time.sleep(5)
    session(*B)
    srv("stop")
    sql("UPDATE `char` SET base_level=99, job_level=70, class=4008 WHERE name='%s'" % B[1])
    r = subprocess.run(MYSQL, stdin=open(UPGRADE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    check("0 the upgrade applies", r.returncode == 0 and sql("SHOW COLUMNS FROM `char` LIKE 'maxed'") != "", r.stdout)
    srv("start"); time.sleep(5)
    session(*A)
    a = secs_ago("created", A[1])
    check("1 a new character has created = now", isinstance(a, int) and 0 <= a < 120, a)
    srv("stop")
    sql("UPDATE `char` SET base_level=98, job_level=70, class=4008, base_exp=0 WHERE name='%s'" % A[1])
    srv("start"); time.sleep(5)
    session(A[0], A[1], ["@blevel 1"])
    srv("stop")  # the char-server writes the logout save to SQL later (its cache), at the latest on stop
    lv = sql("SELECT CONCAT(base_level,'/',job_level) FROM `char` WHERE name='%s'" % A[1])
    m = secs_ago("maxed", A[1])
    check("2 98/70 -> @blevel 1: maxed = now", lv == "99/70" and isinstance(m, int) and 0 <= m < 120, (lv, m))
    sql("UPDATE `char` SET maxed='2020-01-02 03:04:05' WHERE name='%s'" % A[1])
    srv("start"); time.sleep(5)
    session(A[0], A[1], ["@blevel -1"])
    session(A[0], A[1], ["@blevel 1"])
    session(*B)
    srv("stop")
    v = sql("SELECT CONCAT(base_level,' ',maxed) FROM `char` WHERE name='%s'" % A[1])
    check("3 a stored maxed is kept over 99 -> 98 -> 99", v == "99 2020-01-02 03:04:05", v)
    check("4 a char that was 99/70 before the columns keeps maxed NULL", secs_ago("maxed", B[1]) is None, secs_ago("maxed", B[1]))
    drop_cols()
    mark = os.path.getsize(os.path.join(run, "char.out"))
    srv("start"); time.sleep(5)
    try:
        session(*A); entered = True
    except Exception as e:
        entered = repr(e)
    out = open(os.path.join(run, "char.out"), errors="replace").read()[mark:]
    check("5 no columns: the character still enters, the char-server says the dates are off",
          entered is True and "[CHARDATES]" in out, (entered, out[-300:]))
finally:
    srv("stop")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
