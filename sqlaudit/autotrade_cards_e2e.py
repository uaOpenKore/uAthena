#!/usr/bin/env python3
"""autotrade_cards_e2e.py <run dir>: autotrade_item keeps the goods' refine, broken flag and cards for the web site
(S. 2026-11-21; upgrade_2026-11-21_autotrade_cards.sql). Vendor ATVend (as in autotrade_e2e) sells Red Potions and
a +7 Knife with a Poring Card.
 1 without the new columns: the shop is kept as before (rows written, no SQL error), the start log says so
 2 with them: the Knife's row has refine 7 and card0 4001, the potion's row 0s
 3 a restart keeps them (the restored shop is written again with the same values)"""
import os, struct, subprocess, sys, time
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
L = load_lengths()
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def maplog(): return open(os.path.join(run, "map.out"), errors="replace").read()
def stop(): subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
def start(): subprocess.run([os.path.join(SP, "srv.sh"), "start", run], stdout=subprocess.DEVNULL); time.sleep(8)
POT, KNIFE, PORING_CARD = 501, 1201, 4001
def cid(name): return sql("SELECT char_id FROM `char` WHERE name='%s'" % name)
COLS = ["refine", "attribute", "card0", "card1", "card2", "card3"]
def cols(on):
    have = sql("SHOW COLUMNS FROM autotrade_item LIKE 'card3'") != ""
    if on and not have:
        sql(open(os.path.join("/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/tick64/sql-files",
                              "upgrade_2026-11-21_autotrade_cards.sql")).read())
    if not on and have:
        sql("ALTER TABLE autotrade_item " + ", ".join("DROP COLUMN `%s`" % c for c in COLS))
def stock():
    v = cid("ATVend")
    sql("UPDATE login SET level=0 WHERE userid='atvend'")
    sql("UPDATE `char` SET class=5, job_level=40, base_level=50, `option`=8, zeny=1000, last_map='prontera', last_x=150, last_y=150, online=0 WHERE char_id=%s" % v)
    sql("REPLACE INTO skill (char_id, id, lv) VALUES (%s, 1, 9), (%s, 36, 10), (%s, 37, 10), (%s, 39, 10), (%s, 41, 10)" % (v, v, v, v, v))
    sql("DELETE FROM cart_inventory WHERE char_id=%s" % v)
    sql("INSERT INTO cart_inventory (char_id, nameid, amount, identify) VALUES (%s, %d, 20, 1)" % (v, POT))
    sql("INSERT INTO cart_inventory (char_id, nameid, amount, identify, refine, card0) VALUES (%s, %d, 1, 1, 7, %d)" % (v, KNIFE, PORING_CARD))
    sql("DELETE FROM autotrade_shop WHERE char_id=%s" % v); sql("DELETE FROM autotrade_item WHERE char_id=%s" % v)
def open_shop():
    s = enter_map("atvend", "atpass1", "ATVend", log=lambda *a: None); st = Stream(s.map_sock, L)
    for _ in st.packets(3): pass
    items = struct.pack("<HHI", 2, 20, 100) + struct.pack("<HHI", 3, 1, 50000)  # cart index 0, 1 (+2 in the protocol)
    s.map_sock.sendall(struct.pack("<HH80sB", 0x1b2, 85 + len(items), b"cards test", 1) + items)
    for _ in st.packets(2): pass
    chat(s.map_sock, "ATVend", "@autotrade")
    for _ in st.packets(3): pass
def rows(v): return sql("SELECT nameid, amount, price%s FROM autotrade_item WHERE char_id=%s ORDER BY nameid" %
                        ("".join(", " + c for c in COLS) if sql("SHOW COLUMNS FROM autotrade_item LIKE 'card3'") else "", v)).splitlines()
try:
    stop()
    if not cid("ATVend"):
        start()
        try: rostub.Session("atvend_M", "atpass1", log=lambda *a: None).login()
        except Exception: pass
        time.sleep(0.5); enter_map("atvend", "atpass1", "ATVend", log=lambda *a: None).quit_game(wait=2); time.sleep(2); stop()
    v = cid("ATVend")
    # 1 without the columns
    cols(False); stock(); n0 = len(maplog()); start(); open_shop(); time.sleep(1)
    r = rows(v); log = maplog()[n0:]
    check("1 without the new columns: the shop is kept as before and the start log says so",
          r == ["%d\t20\t100" % POT, "%d\t1\t50000" % KNIFE] and "no refine/card columns" in log and "DB error" not in log, "rows=%s" % r)
    stop()
    # 2 with them
    cols(True); stock(); n0 = len(maplog()); start(); open_shop(); time.sleep(1)
    r = rows(v); log = maplog()[n0:]
    check("2 with them: the Knife's row has refine 7 and the Poring Card, the potion's row 0s",
          r == ["%d\t20\t100\t0\t0\t0\t0\t0\t0" % POT, "%d\t1\t50000\t7\t0\t%d\t0\t0\t0" % (KNIFE, PORING_CARD)] and "DB error" not in log, "rows=%s" % r)
    # 3 a restart keeps them
    stop(); start(); time.sleep(4)
    r = rows(v)
    check("3 after a restart the rows still carry them", any(x.startswith("%d\t1\t50000\t7\t0\t%d" % (KNIFE, PORING_CARD)) for x in r), "rows=%s" % r)
finally:
    stop()
    v = cid("ATVend")
    if v:
        sql("DELETE FROM autotrade_shop WHERE char_id=%s" % v); sql("DELETE FROM autotrade_item WHERE char_id=%s" % v)
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
