#!/usr/bin/env python3
"""killexp_e2e.py <PacketTable.cpp>: the exp of a kill reaches the killer. mob_dead finds every attacker of the
mob by char_id (map_charid2sd, now an index): A (GM) kills 3 porings one after another, then goes back to the char
select, picks the character again and kills 3 more (the index must follow the new session). Base exp (0xb1
type 1) must grow with every kill."""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402
from streak_e2e import Me  # noqa: E402

lengths = load_lengths(sys.argv[1])

class ExpMe(Me):
    exp = None
    def note(self, pid, p):
        Me.note(self, pid, p)
        if pid == 0xB1 and struct.unpack_from("<H", p, 2)[0] == 1:
            self.exp = struct.unpack_from("<I", p, 4)[0]

def session():
    s = rostub.Session(USER, PW, log=lambda *a: None)
    s.login(); _, r = s.char_enter(); s.select_char(r[1][0][0]); assert s.map_enter()[0] == "ok"
    me = ExpMe(Stream(s.map_sock, lengths), s.map_sock, s.aid)
    s.map_sock.sendall(struct.pack("<H", 0x7D))  # map loaded -> the server sends the status, exp included
    me.drain(2)
    for c in ("@str -300", "@str 99", "@dex 99", "@heal"):
        me.cmd(c)
    return s, me

def kills(me, n, tag):
    # a first kill only to learn the exp: the server sends base exp (0xb1) on a change, not at map load
    (mob,) = me.spawn(1002, 1)
    for _ in range(30):
        if mob in me.dead or me.attack(mob) is None:
            break
    me.drain(1.5)
    ok = 0
    for i in range(n):
        (mob,) = me.spawn(1002, 1)
        before = me.exp
        for _ in range(30):
            if mob in me.dead or me.attack(mob) is None:
                break
        me.drain(1.5)
        got = me.exp is not None and before is not None and me.exp > before
        print("  %s kill %d: exp %s -> %s %s" % (tag, i + 1, before, me.exp, "ok" if got else "NO EXP"), flush=True)
        ok += got
    return ok

s, me = session()
a = kills(me, 3, "first session")
s.charselect_return(wait=3)
s2, me2 = session()
b = kills(me2, 3, "after char select")
s2.quit_game(wait=1)
if a + b != 6:
    print("FAIL  %d of 6 kills gave the killer exp" % (a + b)); sys.exit(1)
print("ok    6 of 6 kills gave the killer exp"); print("ALL PASSED")
