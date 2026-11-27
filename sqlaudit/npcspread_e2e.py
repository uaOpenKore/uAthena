#!/usr/bin/env python3
"""npcspread_e2e.py <run dir>: NPCs standing on one cell are moved apart (S. 2026-11-27: "those on one cell must be
put on different ones, within 3-5 cells"). The first one loaded keeps its cell, each other one goes to a free walkable
cell 3-5 cells away; an NPC with a touch area (warps, OnTouch) never moves.
 1 niflheim: no two NPCs the client is shown share a cell
 2 niflheim 153,215: Feline (794, classic) stays, Feylin (794, npc/backport) is 3-5 cells away
 3 hu_in01 365,170: Rachel and Girl#Hu (both 793) are both shown, on different cells, 3-5 apart
 4 the map-server log names the moves"""
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
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % (d,)) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run([os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
L = load_lengths()
USER, NAME, PW = "rnpcold", "RnpcOld", "rnpcpw1"
INVIS = {-1, 111, 139, 32767}

def npcs_at(m, x, y):
    srv("stop")
    sql("UPDATE `char` SET last_map='%s', last_x=%d, last_y=%d WHERE name='%s'" % (m, x, y, NAME))
    srv("start"); time.sleep(5)
    for k in range(10):
        try:
            s = rostub.Session(USER, PW, log=lambda *a: None); s.login(); break
        except RuntimeError:
            if k == 9: raise
            time.sleep(2)
    s.char_enter(); s.select_char(0)
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, L); out = []
    for pid, p in st.packets(4):
        if pid == 0x78 and struct.unpack_from("<I", p, 2)[0] >= 1100000000:  # NPC ids (START_NPC_NUM)
            b = p[46:49]; px = (b[0] << 2) | (b[1] >> 6); py = ((b[1] & 0x3f) << 4) | (b[2] >> 4)
            out.append((struct.unpack_from("<h", p, 14)[0], px, py))
    try: s.quit_game(wait=1)
    except Exception: pass
    time.sleep(2)
    return out

def dist(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
try:
    srv("stop"); srv("start"); time.sleep(5)
    if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % USER) == "0":
        try: rostub.Session(USER + "_M", PW, log=lambda *a: None).login()
        except Exception: pass
        time.sleep(1)
        s = enter_map(USER, PW, NAME, log=lambda *a: None); s.quit_game(wait=2); time.sleep(3)
    nf = npcs_at("niflheim", 150, 212)
    cells = [(x, y) for c, x, y in nf if c not in INVIS]
    dup = sorted({c for c in cells if cells.count(c) > 1})
    check("1 niflheim: no two shown NPCs on one cell", not dup and len(cells) > 5, (dup, len(cells)))
    fel = [(x, y) for c, x, y in nf if c == 794 and dist((x, y), (153, 215)) <= 5]
    check("2 one Feline/Feylin stays at 153,215, the other is 3-5 cells away", (153, 215) in fel and len(fel) == 2
          and 3 <= dist(*fel) <= 5, fel)
    hu = [(x, y) for c, x, y in npcs_at("hu_in01", 362, 170) if c == 793]
    near = [p for p in hu if dist(p, (365, 170)) <= 5]
    check("3 hu_in01: Rachel and Girl#Hu on different cells, 3-5 apart", len(set(near)) == 2 and 3 <= dist(*near[:2]) <= 5, hu)
    log = open(os.path.join(run, "map.out"), errors="replace").read()
    check("4 the moves are logged", "Feylin" in log and "moved off" in log)
finally:
    srv("stop")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
