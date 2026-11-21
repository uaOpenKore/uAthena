#!/usr/bin/env python3
"""e2e: a mob's drops fall 500 ms after its death (delay_battle_damage: no) and the drop list kept the killer's
map_session_data pointer (audit item 5, S. 2026-11-20). If the killer leaves within those 500 ms, its session is
freed and mob_delay_item_drop reads first_sd->bl.id from freed memory - and the next player who logs in gets the
same block, so the loot priority goes to that player.
Round: V (E2eTesterV) has selected its char and waits; A (E2eTesterA, GM) kills a Poring at new_zone01 56,100 and
quits at once; V enters the map 0.1 s later, standing on the same spot (its saved position), sees the drops and
tries to pick one up inside item_first_get_time (3 s): the drops belong to A, so V must not get them.
The login event turns @autoloot on for everyone (on the server only drops autoloot cannot take go this way), the
test switches it off for A. Stand: run-drop (prevent_logout 0, item_rate_* 10000).
Usage: python3 -I dropuaf_e2e.py <BornRok src/net/PacketTable.cpp> [rounds, default 3]
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402
from streak_e2e import Me  # noqa: E402

PORING = 1002
USER_V, PW_V, CID_V = "e2etestv", "e2epass1", 150004
SPOT = ("new_zone01", 56, 100)
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def sql(q):
    subprocess.run(["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-e", q],
                   check=True)


def to_char_select(user, pw):
    s = rostub.Session(user, pw, log=lambda *a: None)
    s.login()
    _, res = s.char_enter()
    assert res[0] == "list", res
    s.select_char(res[1][0][0])
    return s


def main():
    lengths = load_lengths(sys.argv[1])
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for r in range(rounds):
        sql("UPDATE `char` SET last_map='%s', last_x=%d, last_y=%d WHERE char_id=%d" % (SPOT + (CID_V,)))
        v = to_char_select(USER_V, PW_V)                 # V waits with its char selected
        a = to_char_select(USER, PW)
        assert a.map_enter()[0] == "ok"
        st = Stream(a.map_sock, lengths)
        me = Me(st, a.map_sock, a.aid)
        me.drain(1.5)
        for c in ("@autoloot 0", "@job 1", "@str -300", "@str 99", "@warp %s %d %d" % SPOT, "@cleanmap"):
            me.cmd(c)  # @cleanmap: no items of earlier rounds (their priority is over) on the floor
        me.drain(1)
        (mob,) = me.spawn(PORING, 1)
        for _ in range(5):
            me.attack(mob)
            if mob in me.dead:
                break
        t_kill = time.time()
        a.map_sock.sendall(struct.pack("<HH", 0x18A, 0))  # A quits right after the kill
        time.sleep(0.05)
        a.map_sock.close()
        time.sleep(0.1)
        ok = v.map_enter()[0] == "ok"                     # V's session is allocated while the drops still wait
        vst = Stream(v.map_sock, lengths)
        drops, got = [], []
        end = t_kill + 2.5                                # inside item_first_get_time (3 s from the drop)
        while time.time() < end:
            for pid, p in vst.packets(0.2):
                if pid in (0x9E, 0x9D):  # 0x9d: V's view filled after the drop (the floor was cleaned before)
                    oid = struct.unpack_from("<I", p, 2)[0]
                    if oid not in drops:
                        drops.append(oid)
                        v.map_sock.sendall(struct.pack("<HHI", 0xF5, 0, oid))  # take it
                elif pid == 0xA0 and p[22] == 0:
                    got.append(struct.unpack_from("<H", p, 6)[0])
                elif pid == 0x91:
                    v.map_sock.sendall(struct.pack("<H", 0x7D))
        print("    round %d: Poring %d killed %s, V in: %s, drops seen by V %d, V picked up %s"
              % (r, mob, mob in me.dead, ok, len(drops), got), flush=True)
        check("round %d: A's drops are not V's to take while A's priority lasts" % r,
              ok and bool(drops) and not got, "drops %d, V got %s" % (len(drops), got))
        v.quit_game(wait=0.5)
        time.sleep(1)
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
