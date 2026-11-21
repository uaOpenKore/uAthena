#!/usr/bin/env python3
"""idrange_e2e.py <run dir>: accounts may go up to 1,000,000,000; npc/mob ids start above that (1,100,000,000).
1 an account registered with the login counter at 150,000,000 is created (was refused past 100,000,000);
2 it enters the map; 3 a normal account standing next to it sees it (spawn packet with id 150,000,000) and
4 its chat; 5 the npcs/mobs it is sent all carry ids >= 1,100,000,000 (none in the account range);
6 a registration with the counter past 1,000,000,000 is refused. Counters and rows are reset afterwards."""
import os, subprocess, sys, time, struct
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths  # noqa: E402
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
HIGH, END, NPC0 = 150000000, 1000000000, 1100000000
SPAWN = (0x78, 0x79, 0x7b, 0x7c, 0x22a, 0x22b, 0x22c)
def register(user):
    try:
        rostub.Session(user + "_M", "idrpass1", log=lambda *a: None).login(); return "logged in"
    except Exception as e:
        return "refused (%s)" % str(e)[:40]
L = load_lengths()
lo = hi = None
try:
    # the normal account first, while the counter is normal
    sql("DELETE FROM login WHERE userid IN ('idrlo','idrhi','idrend')")
    register("idrlo"); time.sleep(0.5)
    sql("ALTER TABLE `login` AUTO_INCREMENT=%d" % HIGH)
    reg = register("idrhi"); time.sleep(0.5)
    aid = sql("SELECT account_id FROM login WHERE userid='idrhi'")
    check("1 account at 150,000,000 created", aid == str(HIGH), "id=%r, login %s" % (aid, reg))
    sql("ALTER TABLE `login` AUTO_INCREMENT=1")
    lo = enter_map("idrlo", "idrpass1", "IdrLo", log=lambda *a: None)
    los = Stream(lo.map_sock, L); los.collect(2)
    try:
        hi = enter_map("idrhi", "idrpass1", "IdrHi", log=lambda *a: None); entered = True
    except Exception as e:
        entered = False; print("      map enter: %s" % e)
    check("2 the 150,000,000 account enters the map", entered)
    if entered:
        his = Stream(hi.map_sock, L)
        # both new characters start at the same save point: they see each other
        seen_hi = his.collect(3)
        chat(hi.map_sock, "IdrHi", "idrange hello")
        seen_lo = los.collect(3)
        spawn = [struct.unpack_from("<I", p, 2)[0] for pid, p in seen_lo if pid in SPAWN]
        check("3 the normal account sees it", HIGH in spawn, "ids=%s" % spawn[:10])
        said = [p for pid, p in seen_lo if pid == 0x8D and struct.unpack_from("<I", p, 4)[0] == HIGH]
        check("4 and its chat", bool(said))
        units = [struct.unpack_from("<I", p, 2)[0] for pid, p in seen_hi + seen_lo if pid in SPAWN]
        players = {HIGH, int(sql("SELECT account_id FROM login WHERE userid='idrlo'") or -1)}
        npcs = [u for u in units if u not in players]
        bad = [u for u in npcs if END <= u < NPC0 or 100000000 <= u < END]
        check("5 npc/mob ids are >= 1,100,000,000", npcs and not bad and min(npcs) >= NPC0,
              "%d units, min=%s, in the account range: %s" % (len(npcs), min(npcs) if npcs else None, bad[:5]))
    for s in (hi, lo):
        if s:
            try: s.quit_game(wait=2)
            except Exception: pass
    # 6 past END_ACCOUNT_NUM
    sql("ALTER TABLE `login` AUTO_INCREMENT=%d" % (END + 5))
    reg = register("idrend")
    a = sql("SELECT COUNT(*) FROM login WHERE account_id >= %d" % END)
    check("6 account past 1,000,000,000 refused", a == "0", "rows=%s, login %s" % (a, reg))
finally:
    sql("DELETE FROM `char` WHERE name IN ('IdrLo','IdrHi')")
    sql("DELETE FROM login WHERE userid IN ('idrlo','idrhi','idrend') OR account_id >= %d" % HIGH)
    sql("ALTER TABLE `login` AUTO_INCREMENT=1")
sys.exit(0 if ok else 1)
