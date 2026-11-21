#!/usr/bin/env python3
"""e2e with two map-servers: the mob drop list kept the killer's map_session_data pointer for the 500 ms before the
drops fall (audit item 5, S. 2026-11-20). A map-server change frees the session at once (chrif_changemapserverack:
map_quit + map_quit_ack), so: A kills a Poring on new_zone01 (map#1) and a script warp takes it to prontera (map#2) at once; V, who
waited with its char selected, enters map#1 right after the handoff and gets A's freed block for its own session;
the drops then took V as their first looter. V tries to pick them up inside the 3 s priority: they are A's.
Stand: run-drop (login, char, map#1 without prontera; prevent_logout 0, item_rate_* 10000) + run-drop2 (map#2:
only prontera, port 5122). Usage: python3 -I dropuaf2_e2e.py <BornRok src/net/PacketTable.cpp> [rounds, default 3]
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
USER_V, PW_V = "e2etestv", "e2epass1"
CID_A, CID_V = 150003, 150004
SPOT = ("new_zone01", 56, 100)
MAP1, MAP2 = 5121, 5122
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def sql(q):
    subprocess.run(["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-e", q], check=True)


def to_char_select(user, pw):
    s = rostub.Session(user, pw, log=lambda *a: None)
    s.login()
    for _ in range(10):
        _, res = s.char_enter()
        if res[0] == "list":
            break
        time.sleep(2)
        s.login()
    else:
        raise RuntimeError("%s: char select refused %s" % (user, res))
    s.select_char(res[1][0][0])
    return s


def enter(s, port):
    rostub.MAP_PORT = port
    try:
        return s.map_enter()[0] == "ok"
    finally:
        rostub.MAP_PORT = MAP1


def main():
    lengths = load_lengths(sys.argv[1])
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for r in range(rounds):
        for cid in (CID_A, CID_V):
            sql("UPDATE `char` SET last_map='%s', last_x=%d, last_y=%d WHERE char_id=%d" % (SPOT + (cid,)))
        v = to_char_select(USER_V, PW_V)
        a = to_char_select(USER, PW)
        assert enter(a, MAP1)
        st = Stream(a.map_sock, lengths)
        me = Me(st, a.map_sock, a.aid)
        me.drain(1.5)
        for c in ("@autoloot 0", "@job 1", "@str -300", "@str 99", "@cleanmap"):
            me.cmd(c)
        (mob,) = me.spawn(PORING, 1)
        for _ in range(5):
            me.attack(mob)
            if mob in me.dead:
                break
        t_kill = time.time()
        # map-server change through a script warp (@warp only goes to maps of its own server, like a portal or
        # Kafra does): A's session on map#1 is freed at once
        msg = b"go\0"
        a.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:XWarp", 24) + msg)
        hand = None
        for pid, p in st.packets(2.0):
            if pid == 0x92:
                hand = struct.unpack_from("<H", p, 26)[0]   # the new map-server's port
                break
        time.sleep(0.05)
        v_in = enter(v, MAP1)                    # V's session: allocated while the drops still wait
        vst = Stream(v.map_sock, lengths)
        drops, got = [], []
        t_drop = None                            # V tries for 2.5 s from the drop: A's priority lasts 3 s from it
        end = t_kill + 10
        while time.time() < end and (t_drop is None or time.time() < t_drop + 2.5):
            for pid, p in vst.packets(0.2):
                if pid in (0x9E, 0x9D):
                    if t_drop is None:
                        t_drop = time.time()
                    oid = struct.unpack_from("<I", p, 2)[0]
                    if oid not in drops:
                        drops.append(oid)
                        v.map_sock.sendall(struct.pack("<HHI", 0xF5, 0, oid))
                elif pid == 0xA0 and p[22] == 0:
                    got.append(struct.unpack_from("<H", p, 6)[0])
                elif pid == 0x91:
                    v.map_sock.sendall(struct.pack("<H", 0x7D))
        print("    round %d: killed %s, A handed to map port %s, V in %s, drops %d (%.1f s after the kill), V picked up %s"
              % (r, mob in me.dead, hand, v_in, len(drops), (t_drop or t_kill) - t_kill, got), flush=True)
        check("round %d: A's drops are not V's to take while A's priority lasts" % r,
              hand == MAP2 and v_in and bool(drops) and not got, "handoff %s, drops %d, V got %s" % (hand, len(drops), got))
        # A follows the handoff to map#2 and quits there; V quits
        try:
            a.map_sock.close()
        except OSError:
            pass
        if hand == MAP2 and enter(a, MAP2):
            a.quit_game(wait=0.5)
        v.quit_game(wait=0.5)
        time.sleep(1.5)
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
