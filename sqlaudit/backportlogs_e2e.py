#!/usr/bin/env python3
"""backportlogs_e2e.py <run dir>: two log floods of the 26.11 deploy, from npc/backport.
Prod 26.11: 2056 x "npc_touch_areanpc : some bug" -- the cell is an NPC cell, but the NPC is hidden from the old
client ([rnpc], 2efea4b9), so the search found nothing and reported it as a bug. On the isolated SQL stand:
 1 the old client's char walks onto ein_fild01 28,261 (npc/backport warp cave_in1): map.out has no "some bug"
 2 it is not warped by the hidden NPC (still on its cell after the login)
Prod 26.11: backport shops (Extended_Ammunition, pet_groomer) listed items with ids above 32767, which the item db
now leaves out: "Item UNKNOWN_ITEM [1000291] buying price (0) ...", a dummy entry in the shop.
 3 at the start no shop holds an UNKNOWN_ITEM; the left-out items are reported instead"""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, load_lengths, enter_map  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
def mark(n): p = os.path.join(run, n); return os.path.getsize(p) if os.path.exists(p) else 0
def since(n, m):
    with open(os.path.join(run, n), errors="replace") as f:
        f.seek(m); return f.read()
L = load_lengths()
USER, PW, NAME = "rnpcold", "rnpcpw1", "RnpcOld"
try:
    srv("stop"); srv("start"); time.sleep(5)
    if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % USER) == "0":
        try: rostub.Session(USER + "_M", PW, log=lambda *a: None).login()
        except Exception: pass
        time.sleep(1)
    if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % USER) == "0":
        s = enter_map(USER, PW, NAME, log=lambda *a: None); s.quit_game(wait=2); time.sleep(3)
    srv("stop")
    sql("UPDATE `char` SET last_map='ein_fild01', last_x=28, last_y=263 WHERE name='%s'" % NAME)
    m0 = mark("map.out"); srv("start"); time.sleep(5)
    boot = since("map.out", m0)
    mm = mark("map.out")
    for k in range(10):
        try:
            s = rostub.Session(USER, PW, log=lambda *a: None); s.login(); break
        except RuntimeError:
            if k == 9: raise
            time.sleep(2)
    s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, L); list(st.packets(3))
    x, y = 28, 261
    s.map_sock.sendall(struct.pack("<H", 0xA7) + bytes(3) + bytes([(x >> 2) & 0xFF, ((x << 6) | ((y >> 4) & 0x3F)) & 0xFF, (y << 4) & 0xFF]))
    pk = list(st.packets(4))
    out = since("map.out", mm)
    check("1 no 'some bug' for the hidden Renewal warp", "npc_touch_areanpc : some bug" not in out,
          out.count("npc_touch_areanpc : some bug"))
    check("2 no map change by the hidden warp", not any(pid in (0x91, 0x92) for pid, _ in pk), [hex(p) for p, _ in pk][:20])
    check("3 no UNKNOWN_ITEM in the shops, the left-out items reported", "UNKNOWN_ITEM" not in boot
          and "left out of the shop" in boot, [l for l in boot.splitlines() if "UNKNOWN_ITEM" in l][:2])
    try: s.quit_game(wait=2)
    except Exception: pass
finally:
    srv("stop")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
