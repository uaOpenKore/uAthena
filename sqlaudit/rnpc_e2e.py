#!/usr/bin/env python3
"""rnpc_e2e.py <run dir>: NPCs with a Renewal sprite the old client cannot draw are not shown to it (S. 2026-11-25:
"old clients crash, the Renewal NPCs are suspected"); BornRok (its marked map login) still sees them. S. 2026-11-26:
"only the Renewal ones, not all" -- npc/backport also holds ports of classic quests (Umbala's #Skulldoor) and
classic-sprite NPCs, which every client must see.
 1 prt_in: the old client sees the Tool Dealer (npc/merchants) and the Trap Specialist (npc/backport, sprite 66)
 2 BornRok sees both
 3 umbala: the old client sees #Skulldoor (npc/backport/quests, sprite 111) at 221,193
 4 nameless_in: the old client does not see Creature#Aru (sprite 1864, no stand-in) at 13,53, BornRok does"""
import os, struct, subprocess, sys, time, socket
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, load_lengths  # noqa: E402
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
UNIT = (0x78, 0x7c, 0x22a, 0x22b, 0x22c, 0x1d7, 0x1d8, 0x1d9, 0x1da, 0x2ee, 0x2ef)
def enter(user, name, brk):
    s = rostub.Session(user, "rnpcpw1", log=lambda *a: None); s.login(); s.char_enter()
    s.select_char(0)
    orig = s.map_enter
    if brk:  # BornRok: "BRK" + bit 0 in the map login's padding bytes 13-16
        def map_enter(cid=None, lid1=None, timeout=15):
            sock = socket.create_connection((rostub.HOST, rostub.MAP_PORT), timeout=timeout); s.map_sock = sock
            pkt = (struct.pack("<H", 0x9b) + b"\x39\x33" + struct.pack("<I", s.aid) + b"\x65" + struct.pack("<I", s.cid)
                   + b"BRK\x01" + struct.pack("<I", s.lid1) + struct.pack("<I", int(time.time() * 1000) & 0xFFFFFFFF) + bytes([s.sex or 0]))
            sock.sendall(pkt); dl = time.time() + timeout
            rostub._recv_exact(sock, 4, dl); cmd = struct.unpack("<H", rostub._recv_exact(sock, 2, dl))[0]
            assert cmd == 0x73, hex(cmd); rostub._recv_exact(sock, 9, dl); sock.sendall(struct.pack("<H", 0x7d))
            return ("ok", None)
        s.map_enter = map_enter
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, L); gids = set()
    seen = {}
    for pid, p in st.packets(4):
        seen[pid] = seen.get(pid, 0) + 1
        if pid == 0x78:
            b = p[46:49]; x = (b[0] << 2) | (b[1] >> 6); y = ((b[1] & 0x3f) << 4) | (b[2] >> 4)
            gids.add((struct.unpack_from("<H", p, 14)[0], x, y))
    return s, {(x, y) for c, x, y in gids}
USERS = [("rnpcold", "RnpcOld"), ("rnpcbrk", "RnpcBrk")]
try:
    srv("stop"); srv("start"); time.sleep(5)
    for u, n in USERS:
        if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) == "0":
            try: rostub.Session(u + "_M", "rnpcpw1", log=lambda *a: None).login()
            except Exception: pass
            time.sleep(1)
        if sql("SELECT COUNT(*) FROM `char` c JOIN login l USING(account_id) WHERE l.userid='%s'" % u) == "0":
            from e2elib import enter_map
            s = enter_map(u, "rnpcpw1", n, log=lambda *a: None); s.quit_game(wait=2); time.sleep(3)
    srv("stop")
    def place(m, x, y):
        srv("stop")
        for u, n in USERS:
            sql("UPDATE `char` SET last_map='%s', last_x=%d, last_y=%d WHERE name='%s'" % (m, x, y, n))
        srv("start"); time.sleep(5)
        so, old = enter("rnpcold", "RnpcOld", False)
        sb, brk = enter("rnpcbrk", "RnpcBrk", True)
        for s in (so, sb):
            try: s.quit_game(wait=1)
            except Exception: pass
        time.sleep(2)
        return old, brk
    old, brk = place("prt_in", 122, 79)
    TOOL, BAG = (126, 76), (109, 68)  # npc/merchants/shops.txt Tool Dealer, npc/backport/re_merchants/shops.txt Trap Specialist
    check("1 the old client sees the Tool Dealer and the Trap Specialist (backport, classic sprite)", TOOL in old and BAG in old, sorted(old))
    check("2 BornRok sees both", TOOL in brk and BAG in brk, sorted(brk))
    old, brk = place("umbala", 218, 193)
    check("3 the old client sees #Skulldoor (backport quest, sprite 111)", (221, 193) in old, sorted(old))
    old, brk = place("nameless_in", 12, 53)
    check("4 Creature#Aru (sprite 1864): hidden from the old client, BornRok sees it", (13, 53) not in old and (13, 53) in brk,
          (sorted(old), sorted(brk)))
finally:
    srv("stop")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
