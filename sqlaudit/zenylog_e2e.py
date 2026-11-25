#!/usr/bin/env python3
"""zenylog_e2e.py <run dir>: the zeny log goes to SQL by itself (S. 2026-11-25: "включи", "писать от 5к"), with
sql_logs: 0 and log_zeny: 5000, on the isolated SQL stand (MariaDB 13306, log DB `log`):
 1 map-server creates the missing zenylog table at start, its type enum has 'B' (buying store)
 2 an NPC purchase of 10 000 z is logged (type S, -10000 for the buyer), one of 500 z is not (below 5k)
 3 an old zenylog (logs.sql enum without 'B') gets 'B' added at start, its rows kept
 4 an unreachable log DB does not stop map-server: a character still enters the map, the log is reported off"""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, load_lengths, enter_map  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
def sqldb(db, q): return subprocess.run(["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", db, "-N", "-B", "-e", q],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def sql(q): return sqldb("ragnarok", q)
def lsql(q): return sqldb("log", q)
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
L = load_lengths()
LOGC = os.path.join(run, "conf", "import", "log_conf.txt")
INTER = os.path.join(run, "conf", "import", "inter_conf.txt")
inter0 = open(INTER).read()
logc0 = open(LOGC).read() if os.path.exists(LOGC) else ""
def set_logconf(extra=""):
    open(LOGC, "w").write("sql_logs: 0\nlog_zeny: 5000\n" + extra)
USER, NAME = "zenylog", "ZenyLog"
def map_out_mark(): return os.path.getsize(os.path.join(run, "map.out")) if os.path.exists(os.path.join(run, "map.out")) else 0
def map_out_since(m):
    with open(os.path.join(run, "map.out"), errors="replace") as f:
        f.seek(m); return f.read()
def zeny_now(pkts, z):
    for pid, p in pkts:
        if pid == 0xb1 and struct.unpack_from("<H", p, 2)[0] == 20: z = struct.unpack_from("<i", p, 4)[0]
    return z
def enter():
    for k in range(10):  # 0x81 code 1 while char-server is still connecting to login
        try:
            s = rostub.Session(USER, "zlpw1", log=lambda *a: None); s.login(); break
        except RuntimeError:
            if k == 9: raise
            time.sleep(2)
    s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    return s
try:
    srv("stop")
    set_logconf()
    lsql("DROP TABLE IF EXISTS zenylog")
    srv("start"); time.sleep(5)
    if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % USER) == "0":
        try: rostub.Session(USER + "_M", "zlpw1", log=lambda *a: None).login()
        except Exception: pass
        time.sleep(1)
    if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % USER) == "0":
        s = enter_map(USER, "zlpw1", NAME, log=lambda *a: None); s.quit_game(wait=2); time.sleep(3)
    t1 = lsql("SHOW COLUMNS FROM zenylog LIKE 'type'")
    check("1 map-server created zenylog, its type has 'B'", "'B'" in t1, t1)
    srv("stop")
    sql("UPDATE `char` SET last_map='prt_in', last_x=122, last_y=79, zeny=100000 WHERE name='%s'" % NAME)
    sql("DELETE i FROM inventory i JOIN `char` c USING(char_id) WHERE c.name='%s'" % NAME)  # weight: earlier runs' potions
    srv("start"); time.sleep(5)
    s = enter(); st = Stream(s.map_sock, L); pk = list(st.packets(3))
    ids = set(struct.unpack_from("<I", p, 2)[0] for pid, p in pk if pid in (0x78, 0x7c, 0x22a, 0x22b))
    for i in ids:
        s.map_sock.sendall(struct.pack("<H5sI", 0x8c, bytes(5), i))
    names = {}
    for pid, p in st.packets(2):
        if pid == 0x95: names[struct.unpack_from("<I", p, 2)[0]] = p[6:30].split(b"\0")[0].decode("latin-1")
    tool = [i for i, n in names.items() if n.startswith("Tool Dealer")]
    check("2a the Tool Dealer is next to the character", bool(tool), list(names.values())[:10])
    z = 100000
    def buy(n):
        global z
        s.map_sock.sendall(struct.pack("<HIB", 0x90, tool[0], 1)); z = zeny_now(st.packets(1), z)
        s.map_sock.sendall(struct.pack("<HIB", 0xc5, tool[0], 0)); z = zeny_now(st.packets(1), z)
        s.map_sock.sendall(struct.pack("<HHHH", 0xc8, 8, n, 501)); z = zeny_now(st.packets(2), z)
    cid = sql("SELECT char_id FROM `char` WHERE name='%s'" % NAME)
    z0 = z; buy(200); big = z0 - z
    z1 = z; buy(10); small = z1 - z
    time.sleep(12)  # the async log writer flushes every few seconds
    rows = lsql("SELECT type, amount FROM zenylog WHERE char_id=%s ORDER BY id" % cid)
    check("2b the 10 000 z purchase is logged as S -%d, the %d z one is not" % (big, small),
          rows.split("\n") == ["S\t%d" % -big] and big >= 5000 and 0 < small < 5000, "rows=%r big=%d small=%d" % (rows, big, small))
    try: s.quit_game(wait=2)
    except Exception: pass
    srv("stop")
    lsql("DROP TABLE IF EXISTS zenylog; CREATE TABLE zenylog (id int(11) unsigned NOT NULL auto_increment, time datetime NOT NULL default '2000-01-01 00:00:00',"
         " char_id int(11) NOT NULL default '0', src_id int(11) NOT NULL default '0', type enum('M','T','V','S','N','A') NOT NULL default 'S',"
         " amount int(11) NOT NULL default '0', map varchar(11) NOT NULL default '', PRIMARY KEY (id), INDEX (type)) ENGINE=MyISAM;"
         " INSERT INTO zenylog (time,char_id,src_id,type,amount,map) VALUES (NOW(),1,1,'T',777777,'prontera')")
    srv("start"); time.sleep(5)
    t3 = lsql("SHOW COLUMNS FROM zenylog LIKE 'type'"); kept = lsql("SELECT COUNT(*) FROM zenylog WHERE amount=777777")
    check("3 an old zenylog gets 'B', its rows kept", "'B'" in t3 and kept == "1", "%s kept=%s" % (t3, kept))
    srv("stop")
    open(INTER, "w").write(inter0 + "log_db: zenylog_no_such_db\n")
    m = map_out_mark(); srv("start"); time.sleep(5)
    try:
        s = enter(); entered = True; s.quit_game(wait=2)
    except Exception as e:
        entered = False
    out = map_out_since(m)
    check("4 an unreachable log DB: the character still enters, the zeny log is reported off",
          entered and "the zeny log (log_zeny) is turned off" in out, "entered=%s" % entered)
finally:
    srv("stop")
    open(INTER, "w").write(inter0)
    open(LOGC, "w").write(logc0)
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
