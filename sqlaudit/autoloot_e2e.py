#!/usr/bin/env python3
"""autoloot_e2e.py <run dir>: @autoloot for players, paid in zeny like @autopay (S. 2026-11-26).
A minute costs autoloot_price_hour_bp hundredths of a % of the zeny carried an hour (the @autopay formula: 10 =
0.1 % an hour, at least 1 zeny a minute), paid ahead for the minute that starts. On the isolated SQL stand:
 1 a player (GM level 0) with 600000 zeny: @autoloot on and 10 zeny are taken at once
 2 off and on again within the paid minute: nothing more is taken
 3 within the next two minutes (the minute timer's phase) the next minute is taken: 9 zeny from 599990
 4 it stays on over a relog (no new charge inside the paid minute)
 5 with 5 zeny left (1 a minute) 1 is taken; with 0 zeny at the next minute it turns itself off and says so
 6 a GM level 10 account uses it free; @autoloot alone tells the state, for it too"""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, load_lengths, enter_map, chat, messages  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % (d,)) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
L = load_lengths()
PW = "alpw1"
PLAYER, GM = ("autoloot1", "AutoLoot1"), ("autoloot2", "AutoLoot2")

class Client:
    def __init__(self, user, name):
        self.name = name
        for k in range(10):
            try:
                self.s = rostub.Session(user, PW, log=lambda *a: None); self.s.login(); break
            except RuntimeError:
                if k == 9: raise
                time.sleep(2)
        self.s.char_enter(); self.s.select_char(0)
        assert self.s.map_enter()[0] == "ok"
        self.st = Stream(self.s.map_sock, L); self.zeny = None; self.msgs = []
        self.pump(3)
    def pump(self, secs):
        pk = list(self.st.packets(secs))
        for pid, p in pk:
            if pid == 0xb1 and struct.unpack_from("<H", p, 2)[0] == 20:
                self.zeny = struct.unpack_from("<I", p, 4)[0]
        m = messages(pk); self.msgs += m
        return m
    def cmd(self, text, secs=2):
        chat(self.s.map_sock, self.name, text); return self.pump(secs)
    def quit(self):
        try: self.s.quit_game(wait=2)
        except Exception: pass
        time.sleep(3)

def zeny_of(name): return int(sql("SELECT zeny FROM `char` WHERE name='%s'" % name) or -1)
try:
    srv("stop"); srv("start"); time.sleep(5)
    for u, n in (PLAYER, GM):
        if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) == "0":
            for k in range(10):
                try: rostub.Session(u + "_M", PW, log=lambda *a: None).login()
                except Exception: pass
                time.sleep(2)
                if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) != "0": break
        if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % u) == "0":
            for k in range(10):
                try:
                    s = enter_map(u, PW, n, log=lambda *a: None); break
                except RuntimeError:
                    if k == 9: raise
                    time.sleep(2)
            s.quit_game(wait=2); time.sleep(3)
    srv("stop")
    sql("UPDATE login SET level=0 WHERE userid='%s'; UPDATE login SET level=10 WHERE userid='%s'" % (PLAYER[0], GM[0]))
    sql("UPDATE `char` SET zeny=600000 WHERE name IN ('%s','%s')" % (PLAYER[1], GM[1]))
    sql("DELETE r FROM global_reg_value r JOIN `char` c USING(char_id) WHERE c.name IN ('%s','%s') AND r.str LIKE 'AUTOLOOT%%'" % (PLAYER[1], GM[1]))
    srv("start"); time.sleep(5)

    c = Client(*PLAYER)
    m = c.cmd("@autoloot on")
    check("1 on, 10 zeny taken at once", c.zeny == 600000 - 10 and any("10 zeny a minute" in x for x in m), (c.zeny, m))
    c.cmd("@autoloot off"); m = c.cmd("@autoloot on")
    check("2 off + on inside the paid minute: nothing more", c.zeny == 600000 - 10 and any("Autolooting" in x for x in m), (c.zeny, m))
    paid = c.zeny
    for k in range(13):  # the minute timer runs every 60 s with its own phase: the next charge is within 2 min
        c.pump(10)
        if c.zeny != paid: break
    check("3 the next minute is taken (9 zeny from 599990)", c.zeny == paid - 9, c.zeny)
    c.pump(3)
    c.quit()
    c = Client(*PLAYER)
    m = c.cmd("@autoloot")
    check("4b the state names the price", any("zeny a minute" in x for x in m), m)
    check("4 still on after a relog, no new charge", zeny_of(PLAYER[1]) in (599981, 599981 - 9) and any("is on" in x for x in m), (zeny_of(PLAYER[1]), m))
    c.quit()
    srv("stop")
    sql("UPDATE `char` SET zeny=1 WHERE name='%s'" % PLAYER[1])
    sql("UPDATE global_reg_value r JOIN `char` c USING(char_id) SET r.value='0' WHERE c.name='%s' AND r.str='AUTOLOOT_UNTIL'" % PLAYER[1])
    srv("start"); time.sleep(5)
    c = Client(*PLAYER)  # the paid minute is over: the login takes 1 zeny, the next minute finds 0
    for k in range(13):
        c.pump(10)
        if any("Autoloot is off" in x for x in c.msgs): break
    off = [x for x in c.msgs if "Autoloot is off" in x]
    c.quit()
    check("5 out of zeny: it turns itself off and says so", off and zeny_of(PLAYER[1]) == 0
          and sql("SELECT r.value FROM global_reg_value r JOIN `char` c USING(char_id) WHERE c.name='%s' AND r.str='AUTOLOOT'" % PLAYER[1]) in ("", "0"),
          (zeny_of(PLAYER[1]), c.msgs[-4:]))
    g = Client(*GM)
    m = g.cmd("@autoloot on"); g.pump(2)
    check("6 GM level 10: free", g.zeny in (None, 600000) and zeny_of(GM[1]) == 600000 and any("Autolooting" in x for x in m), (g.zeny, m))
    m2 = g.cmd("@autoloot")
    check("6b @autoloot alone: the state, nothing switched", any("Autoloot is on" in x and "free" in x for x in m2), m2)
    g.cmd("@autoloot off"); g.quit()
finally:
    srv("stop")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
