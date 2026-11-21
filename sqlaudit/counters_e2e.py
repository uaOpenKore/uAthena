#!/usr/bin/env python3
"""counters_e2e.py <run dir>: new ids past the server's range must be refused, not stored wrong.
AUTO_INCREMENT set past 2^31-1 (char, guild, party) / past END_ACCOUNT_NUM 1000000000 (login), then: a character is
created, a guild and a party are founded (@guild / @party by GM Char5), an account is registered (_M). Each must be
refused (no row with an id over the limit, no negative id handed out) and logged; afterwards the counters are reset."""
import os, subprocess, sys, time, socket, struct
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths  # noqa: E402
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def log(name): return open(os.path.join(run, name), errors="replace").read()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
BIG = 2147483648
# a fresh account + character, made while the counters are normal
for t in ("login",): pass
try:
    rostub.Session("ctra_M", "ctrpass1", log=lambda *a: None).login()
except Exception:
    pass
time.sleep(1)
sql("UPDATE login SET level=99 WHERE userid='ctra'")
s = rostub.Session("ctra", "ctrpass1", log=lambda *a: None); s.login(); _, r = s.char_enter()
if not r[1]:
    s.make_char("CtrA", slot=0)
for a in ("char_sock", "login_sock", "sock"):
    if getattr(s, a, None):
        try: getattr(s, a).close()
        except Exception: pass
time.sleep(8)
sql("ALTER TABLE `char` AUTO_INCREMENT=%d" % BIG); sql("ALTER TABLE `guild` AUTO_INCREMENT=%d" % BIG)
sql("ALTER TABLE `party` AUTO_INCREMENT=%d" % BIG); sql("ALTER TABLE `login` AUTO_INCREMENT=1000000005")
try:
    # 1 a second character with the char counter past 2^31
    s = rostub.Session("ctra", "ctrpass1", log=lambda *a: None); s.login(); _, r = s.char_enter()
    try: cid = s.make_char("CtrB", slot=1)
    except Exception as e: cid = "refused (%s)" % e.__class__.__name__
    big = sql("SELECT COUNT(*) FROM `char` WHERE char_id >= %d OR char_id < 0" % BIG)
    check("1 character past 2^31 refused (no row, no negative id)", big == "0", "rows=%s cid=%s" % (big, cid))
    for a in ("char_sock", "login_sock", "sock"):
        if getattr(s, a, None):
            try: getattr(s, a).close()
            except Exception: pass
    time.sleep(8)  # the char-server lets the account go
    # 2/3 guild and party founded by CtrA (GM, in neither)
    cida = sql("SELECT char_id FROM `char` WHERE name='CtrA'")
    sql("INSERT INTO inventory (char_id, nameid, amount, identify) VALUES (%s, 714, 1, 1)" % cida)  # an Emperium
    sql("REPLACE INTO skill (char_id, id, lv) VALUES (%s, 1, 9)" % cida)  # Basic Skill 9: may found a party
    s = enter_map("ctra", "ctrpass1", "CtrA", log=lambda *a: None)
    time.sleep(1)
    s.map_sock.sendall(struct.pack("<H24s", 0xF9, b"CtrParty")); time.sleep(2)                 # create party
    s.map_sock.sendall(struct.pack("<HI24s", 0x165, int(cida), b"CtrGuild")); time.sleep(2)   # create guild
    s.quit_game(wait=2)
    g = sql("SELECT COUNT(*) FROM guild WHERE guild_id >= %d OR guild_id < 0" % BIG)
    p = sql("SELECT COUNT(*) FROM party WHERE party_id >= %d OR party_id < 0" % BIG)
    check("2 guild past 2^31 refused", g == "0", "rows=%s" % g)
    check("3 party past 2^31 refused", p == "0", "rows=%s" % p)
    # 4 registration past END_ACCOUNT_NUM
    try:
        rostub.Session("ctrnew_M", "ctrpass1", log=lambda *a: None).login()
        reg = "logged in"
    except Exception as e:
        reg = "refused (%s)" % str(e)[:40]
    a = sql("SELECT COUNT(*) FROM login WHERE account_id >= 1000000000")
    check("4 account past END_ACCOUNT_NUM refused", a == "0", "rows=%s, login %s" % (a, reg))
    lg = log("char.out").count("is out of range") + log("login.out").count("is out of range")
    check("5 each refusal logged", lg >= 4, "lines=%d" % lg)
finally:
    for t, k in (("char", "char_id"), ("guild", "guild_id"), ("party", "party_id"), ("login", "account_id")):
        sql("DELETE FROM `%s` WHERE %s >= %d" % (t, k, 1000000000 if t == "login" else BIG))
        sql("DELETE FROM `%s` WHERE %s < 0" % (t, k))
        sql("ALTER TABLE `%s` AUTO_INCREMENT=1" % t)   # back to max(id)+1
    sql("DELETE FROM `char` WHERE name IN ('CtrA','CtrB')"); sql("DELETE FROM login WHERE userid IN ('ctrnew','ctra')")
    sql("DELETE FROM guild WHERE name='CtrGuild'"); sql("DELETE FROM party WHERE name='CtrParty'")
sys.exit(0 if ok else 1)
