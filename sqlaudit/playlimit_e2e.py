#!/usr/bin/env python3
"""playlimit_e2e.py <run dir> [scenario...]: the daily play-time limit (daily_play_limit 12 h).
Each scenario stops the stand, sets the DB (play_reset row, char rows) and the wall clock (tools/wallwarp.so,
WALL_FILE seconds), starts it and checks. Scenarios:
  play     1 minutes counted (100 -> 102 after ~2 min), 2 a row of another day starts at 0, 3 one minute left:
           the 1-minute warning, the limit message, disconnected ~40 s later, 4 at the limit already: refused
           (message at once, disconnected ~40 s later), 5 a GM (level 2) over the limit stays
  midnight 6 23:59 -> 00:00: the online player's counter goes to 0, play_reset moves to the new date
  timer    7 the clock set back (same date) but 24 h since the reset: reset by the timer
  restart  8 the stand was down over midnight: reset at start
  buy      10 @buyplaytime: the current price (1/60 % of the zeny on the character, at least 1) a minute takes
           minutes off, only what was played is charged,
           not enough zeny is refused, buying at the limit cancels the disconnect; the warnings name the commands
  autopay  11 @autopay on: the minutes are paid (100 x level each) and the played time does not grow; it stays on
           over a relog; when the zeny run out it turns itself off and the minutes count again
  bot      12 OpenKore (ticks 10 a second, the @whobot rule) pays playtime_buy_bot_percent (200) of the price,
           a game client the price (the stand's battle_conf import: playtime_price_hour_bp 100, 200 %)
  nocols   9 without the migration the servers run, log that the limit is off, nobody is kicked
"""
import datetime, os, re, subprocess, sys, time, struct
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths, messages  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
want = sys.argv[2:] or ["play", "buy", "autopay", "bot", "midnight", "timer", "restart", "nocols"]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
WALL = os.path.join(SP, "tools", "wall.txt")
SHIM = os.path.join(SP, "tools", "wallwarp.so")
L = load_lengths()
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def ymd(t): return int(t.strftime("%Y%m%d"))
def charlog(): return open(os.path.join(run, "char.out"), errors="replace").read()
def stop(): subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
def start(offset):
    open(WALL, "w").write("%d\n" % offset)
    env = dict(os.environ, LD_PRELOAD=SHIM, WALL_FILE=WALL)
    subprocess.run([os.path.join(SP, "srv.sh"), "start", run], env=env, stdout=subprocess.DEVNULL)
    end = time.time() + 60
    while time.time() < end and "online after" not in subprocess.run(["tail", "-c", "4000", os.path.join(run, "map.out")],
                                                                    stdout=subprocess.PIPE, text=True).stdout:
        time.sleep(1)
    time.sleep(3)

USERS = [("plima", "PlA"), ("plimb", "PlB"), ("plimc", "PlC"), ("plimd", "PlD"), ("plime", "PlE")]
def setup_accounts():
    for u, n in USERS:
        if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) == "0":
            try: rostub.Session(u + "_M", "plpass1", log=lambda *a: None).login()
            except Exception: pass
            time.sleep(0.5)
        if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % u) == "0":
            s = enter_map(u, "plpass1", n, log=lambda *a: None); s.quit_game(wait=2)
    sql("UPDATE login SET level=0 WHERE userid IN ('plima','plimb','plimc','plimd')")
    sql("UPDATE login SET level=2 WHERE userid='plime'")
def setrow(name, minutes, date): sql("UPDATE `char` SET play_minutes=%d, play_date=%d WHERE name='%s'" % (minutes, date, name))
def row(name): return sql("SELECT play_minutes, play_date FROM `char` WHERE name='%s'" % name).split("\t")
def setreset(date, at): sql("REPLACE INTO play_reset (id, reset_date, reset_at) VALUES (0, %d, FROM_UNIXTIME(%d))" % (date, int(at.timestamp())))
def resetrow(): return sql("SELECT reset_date FROM play_reset WHERE id=0")

class Player:
    def __init__(self, user, name):
        self.name = name
        self.s = enter_map(user, "plpass1", name, log=lambda *a: None)
        self.st = Stream(self.s.map_sock, L); self.msgs = []; self.closed_at = None
    def pump(self, sec):
        if self.closed_at: time.sleep(sec); return
        try:
            for pid, p in self.st.packets(sec):
                for m in messages([(pid, p)]): self.msgs.append((time.time(), m))
        except (ConnectionError, OSError):
            self.closed_at = time.time()
    def said(self, sub): return [t for t, m in self.msgs if sub in m]
    def cmd(self, text): chat(self.s.map_sock, self.name, text)
    def quit(self):
        if not self.closed_at:
            try: self.s.quit_game(wait=2)
            except Exception: pass
def pump_all(ps, sec):
    end = time.time() + sec
    while time.time() < end:
        for p in ps: p.pump(0.3)

now = datetime.datetime.now()
today, yesterday = ymd(now), ymd(now - datetime.timedelta(days=1))
try:
    if "play" in want:
        stop(); start(0); setup_accounts(); stop()
        setreset(today, now - datetime.timedelta(hours=1))
        setrow("PlA", 100, today); setrow("PlB", 700, yesterday); setrow("PlC", 719, today)
        setrow("PlD", 720, today); setrow("PlE", 800, today)
        start(0)
        a, b = Player("plima", "PlA"), Player("plimb", "PlB")
        c = Player("plimc", "PlC"); t_c = time.time()
        d = Player("plimd", "PlD"); t_d = time.time()
        e = Player("plime", "PlE")
        b.cmd("@playtime")
        pump_all([a, b, c, d, e], 128)
        a.cmd("@playtime"); pump_all([a, b, c, d, e], 2)
        # the limit message may come late in that window: give its 40 s disconnect time to happen
        lim = c.said("limit (12 h) reached")
        if lim and not c.closed_at:
            pump_all([c, e], max(0, lim[0] + 55 - time.time()))
        a.quit(); b.quit(); time.sleep(4)
        r = row("PlA")
        check("1 minutes counted (100 + ~2)", r == ["102", str(today)], "row=%s, @playtime=%s" % (r, [m for _, m in a.msgs if "Played" in m]))
        check("2 a row of another day starts at 0", bool(b.said("Played today: 0 h 00 min")), "msgs=%s" % [m for _, m in b.msgs][-3:])
        warn = c.said("1 minute(s) left today"); lim = c.said("limit (12 h) reached")
        check("3a one minute left: the 1-minute warning", bool(warn), "msgs=%s" % [m for _, m in c.msgs][-4:])
        check("3b then the limit message within ~2 min", bool(lim) and lim[0] - t_c < 130, "lim=%s" % [x - t_c for x in lim])
        check("3c disconnected ~40 s after it", bool(lim) and c.closed_at and 35 <= c.closed_at - lim[0] <= 50,
              "closed after %s s" % ((c.closed_at - lim[0]) if lim and c.closed_at else None))
        lim = d.said("limit (12 h) reached")
        check("4a at the limit already: the message at once", bool(lim) and lim[0] - t_d < 5, "lim=%s" % [x - t_d for x in lim])
        check("4b disconnected ~40 s later", bool(lim) and d.closed_at and 35 <= d.closed_at - lim[0] <= 50,
              "closed after %s s" % ((d.closed_at - lim[0]) if lim and d.closed_at else None))
        check("5 a GM over the limit stays, no limit message", e.closed_at is None and not e.said("reached"), "closed=%s" % e.closed_at)
        e.quit(); c.quit(); d.quit()
        check("  kicks logged", charlog().count("") >= 0 and open(os.path.join(run, "map.out"), errors="replace").read().count("[PLAYLIMIT] kick") >= 2)
    if "buy" in want:
        stop()
        lv = 10
        sql("UPDATE `char` SET base_level=%d, zeny=200000 WHERE name IN ('PlA','PlC')" % lv)
        sql("UPDATE `char` SET zeny=10 WHERE name='PlB'")
        setreset(today, now - datetime.timedelta(hours=1))
        setrow("PlA", 100, today); setrow("PlB", 100, today); setrow("PlC", 719, today)
        start(0)
        a = Player("plima", "PlA"); a.cmd("@buyplaytime 60"); pump_all([a], 2); a.cmd("@playtime"); pump_all([a], 2)
        zeny = sql("SELECT zeny FROM `char` WHERE name='PlA'")
        pt = [m for _, m in a.msgs if "Played today" in m]
        bought = [m for _, m in a.msgs if "Bought" in m]
        check("10a 60 minutes bought for 60 x the price (200000 zeny: 33 a minute)", bool(bought) and "%d zeny" % (60 * 33) in bought[-1], "msgs=%s" % [m for _, m in a.msgs][-3:])
        check("10b the played minutes went down by 60", bool(pt) and re.search(r"Played today: 0 h 4[0-1] min", pt[-1]), "pt=%s" % pt[-1:])
        a.cmd("@buyplaytime 500"); pump_all([a], 2)
        bought = [m for _, m in a.msgs if "Bought" in m]
        check("10c buying more than played: only the played minutes are charged", bool(bought) and re.search(r"Bought 4[0-1] minute", bought[-1]), "msgs=%s" % [m for _, m in a.msgs][-2:])
        a.quit()
        b = Player("plimb", "PlB"); b.cmd("@buyplaytime 30"); pump_all([b], 2)
        check("10d not enough zeny: refused", bool([m for _, m in b.msgs if "Not enough zeny" in m]), "msgs=%s" % [m for _, m in b.msgs][-2:])
        b.quit()
        c = Player("plimc", "PlC")
        pump_all([c], 125)
        warn = [m for _, m in c.msgs if "left today" in m]
        check("10e the warning names @playtime and @buyplaytime", bool(warn) and "@playtime" in warn[-1] and "@buyplaytime" in warn[-1], "warn=%s" % warn[-1:])
        lim = c.said("limit (12 h) reached")
        if lim and not c.closed_at:
            c.cmd("@buyplaytime 30"); pump_all([c], 50)
        check("10f buying at the limit cancels the disconnect", bool(lim) and c.closed_at is None, "lim=%s closed=%s" % (bool(lim), c.closed_at))
        c.quit()
    if "autopay" in want:
        stop()
        lv = 10
        sql("UPDATE `char` SET base_level=%d, zeny=100000 WHERE name='PlA'" % lv)
        sql("UPDATE `char` SET base_level=%d, zeny=0 WHERE name='PlB'" % lv)  # not even the 1-zeny minimum: off at the first
        sql("DELETE FROM global_reg_value WHERE str='PLAY_AUTOPAY'")
        setreset(today, now - datetime.timedelta(hours=1))
        setrow("PlA", 100, today); setrow("PlB", 100, today)
        start(0)
        a = Player("plima", "PlA"); a.cmd("@autopay on"); pump_all([a], 2)
        b = Player("plimb", "PlB"); b.cmd("@autopay on"); pump_all([a, b], 2)
        on = [m for _, m in a.msgs if "@autopay is on" in m]
        check("11a @autopay on (100000 zeny: 16 a minute)", bool(on) and "16 zeny" in on[-1], "msgs=%s" % [m for _, m in a.msgs][-2:])
        pump_all([a, b], 130)
        a.cmd("@playtime"); pump_all([a, b], 2)
        pt = [m for _, m in a.msgs if "Played today" in m]
        check("11b the played time does not grow (1 h 40 min = 100)", bool(pt) and "Played today: 1 h 40 min" in pt[-1], "pt=%s" % pt[-1:])
        off = [m for _, m in b.msgs if "@autopay is off: not enough zeny" in m]
        check("11c out of zeny: @autopay turns itself off", bool(off), "msgs=%s" % [m for _, m in b.msgs][-3:])
        a.quit(); b.quit(); time.sleep(4)
        zeny = int(sql("SELECT zeny FROM `char` WHERE name='PlA'"))
        check("11d the minutes were paid, each at the price of its own minute (16 while over 96000)", 2 * 16 <= 100000 - zeny <= 10 * 16 and (100000 - zeny) % 16 == 0, "zeny=%d" % zeny)
        a = Player("plima", "PlA"); a.cmd("@autopay"); pump_all([a], 2)
        st = [m for _, m in a.msgs if m.startswith("@autopay is")]
        check("11e @autopay stays on over a relog", bool(st) and st[-1].startswith("@autopay is on"), "st=%s" % st[-1:])
        a.cmd("@autopay off"); pump_all([a], 2); a.quit()
    if "bot" in want:
        stop()
        sql("UPDATE `char` SET base_level=10, zeny=100000 WHERE name IN ('PlA','PlB')")
        sql("DELETE FROM global_reg_value WHERE str='PLAY_AUTOPAY'")
        setreset(today, now - datetime.timedelta(hours=1))
        setrow("PlA", 100, today); setrow("PlB", 100, today)
        start(0)
        a = Player("plima", "PlA"); b = Player("plimb", "PlB")
        t0 = time.time()
        while time.time() - t0 < 65:  # PlB ticks like OpenKore's default config
            try: b.s.map_sock.sendall(struct.pack("<HI", 0x0089, int(time.time() * 1000) & 0xffffffff) + b"\0\0")
            except OSError: break
            pump_all([a, b], 0.1)
        a.cmd("@autopay"); b.cmd("@autopay"); pump_all([a, b], 2)
        pa = [m for _, m in a.msgs if m.startswith("@autopay is")]
        pb = [m for _, m in b.msgs if m.startswith("@autopay is")]
        check("12a a game client pays the price (100000 zeny: 16 a minute)", bool(pa) and "(16 zeny a minute)" in pa[-1], "msgs=%s" % pa[-1:])
        check("12b OpenKore pays 200 % of it (32 a minute)", bool(pb) and "(32 zeny a minute)" in pb[-1], "msgs=%s" % pb[-1:])
        a.quit(); b.quit()
    if "midnight" in want:
        stop()
        target = datetime.datetime.combine(now.date(), datetime.time(23, 59, 15))
        off = int(target.timestamp() - time.time()) - 30   # the stand needs ~30 s to come up
        setreset(ymd(target), target - datetime.timedelta(hours=2)); setrow("PlA", 300, ymd(target))
        start(off)
        a = Player("plima", "PlA")
        # wait until 00:01:15 server time
        pump_all([a], max(0, (target + datetime.timedelta(seconds=120)).timestamp() - (time.time() + off)))
        a.cmd("@playtime"); pump_all([a], 2)
        pt = [m for _, m in a.msgs if "Played today" in m]
        check("6a the online player's counter went to 0 at midnight", bool(pt) and re.search(r"Played today: 0 h 0[0-2] min", pt[-1] or ""), "pt=%s" % pt[-1:])
        nxt = ymd(target + datetime.timedelta(days=1))
        check("6b play_reset moved to the new date", resetrow() == str(nxt), "reset_date=%s want %d" % (resetrow(), nxt))
        check("6c logged as a midnight reset", "[PLAYLIMIT] reset (midnight)" in charlog())
        a.quit(); time.sleep(4)
        # the row may still carry yesterday's minutes (rows are not rewritten at a reset): they count as 0
        a = Player("plima", "PlA"); a.cmd("@playtime"); pump_all([a], 3); a.quit()
        pt = [m for _, m in a.msgs if "Played today" in m]
        check("6d after a relog the new day still counts from 0", bool(pt) and re.search(r"Played today: 0 h 0[0-3] min", pt[-1]),
              "pt=%s row=%s" % (pt[-1:], row("PlA")))
    if "timer" in want:
        stop()
        setreset(today, datetime.datetime.now() - datetime.timedelta(hours=24) + datetime.timedelta(seconds=40))
        n0 = charlog().count("[PLAYLIMIT] reset (24h")
        start(0)
        time.sleep(80)
        check("7 24 h after the reset, same date: reset by the timer", charlog().count("[PLAYLIMIT] reset (24h") > n0 and resetrow() == str(today),
              "reset_date=%s" % resetrow())
    if "restart" in want:
        stop()
        setreset(yesterday, datetime.datetime.now() - datetime.timedelta(hours=20))
        n0 = charlog().count("[PLAYLIMIT] reset (midnight")
        start(0)
        check("8 down over midnight: reset at start", charlog().count("[PLAYLIMIT] reset (midnight") > n0 and resetrow() == str(today),
              "reset_date=%s" % resetrow())
    if "nocols" in want:
        stop()
        sql("ALTER TABLE `char` DROP COLUMN play_minutes, DROP COLUMN play_date"); sql("DROP TABLE play_reset")
        n0 = charlog().count("daily play-time limit is OFF")
        try:
            start(0)
            d = Player("plimd", "PlD"); pump_all([d], 15)
            check("9 without the migration: runs, logs the limit is off, nobody kicked",
                  charlog().count("daily play-time limit is OFF") > n0 and d.closed_at is None and not d.said("reached"))
            d.quit()
        finally:
            stop()
            subprocess.run("mysql --no-defaults -h127.0.0.1 -P13306 -uroot ragnarok < %s" %
                           "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/tick64/sql-files/upgrade_2026-11-21_playlimit.sql", shell=True)
finally:
    stop(); open(WALL, "w").write("0\n")
    setreset(ymd(datetime.datetime.now()), datetime.datetime.now())
sys.exit(0 if ok else 1)
