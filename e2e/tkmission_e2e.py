#!/usr/bin/env python3
"""e2e check: Taekwon Mission must only hand out monsters that spawn somewhere, and must re-roll a stuck target.

Each round: log out, put TK_MISSION_ID = 2898 (Solid Antique Book, a backported renewal monster with no spawn
anywhere) and TK_MISSION_COUNT = 0 into the char's registry in the local test DB, log in as a Taekwon Kid, use
Taekwon Mission. Expected: a new target (0x20e mission info), which is a monster with a spawn line in a loaded
script. Then a second use must keep that target (a normal target can't be changed, 99%).
Usage: python3 -I tkmission_e2e.py <BornRok src/net/PacketTable.cpp> <spawned ids file> [rounds]
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, chat, load_lengths  # noqa: E402

CHAR_ID, STUCK, TK_MISSION, TAEKWON = 150003, 2898, 493, 4046


def sql(q):
    return subprocess.run(["mysql", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-e", q],
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()


def put_stuck_mission():
    """Registry TK_MISSION_ID = STUCK, re-applied until a late logout save stops overwriting it."""
    for _ in range(10):
        sql("REPLACE INTO global_reg_value (char_id,str,value,type,account_id) VALUES "
            "(%d,'TK_MISSION_ID','%d',3,0),(%d,'TK_MISSION_COUNT','0',3,0)" % (CHAR_ID, STUCK, CHAR_ID))
        time.sleep(2)
        if sql("SELECT value FROM global_reg_value WHERE char_id=%d AND str='TK_MISSION_ID'" % CHAR_ID) == str(STUCK):
            return
    raise RuntimeError("could not put the stuck mission into the registry")


def mission(st, sock, aid):
    """Use Taekwon Mission on self; returns (mob id from 0x20e or None, failed?)."""
    sock.sendall(struct.pack("<H", 0x72) + b"\0" * 4 + struct.pack("<H", 1) + b"\0" * 2
                 + struct.pack("<H", TK_MISSION) + b"\0" * 9 + struct.pack("<I", aid))
    mob, failed = None, False
    for pid, p in st.packets(2.5):
        if pid == 0x20E and p[31] == 20:
            mob = struct.unpack_from("<I", p, 26)[0]
        elif pid == 0x110 and struct.unpack_from("<H", p, 2)[0] == TK_MISSION:
            failed = True
    return mob, failed


def main():
    lengths = load_lengths(sys.argv[1])
    spawned = {int(x) for x in open(sys.argv[2]).read().split()}
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    first = True
    picks, kept, bad = [], 0, []
    for r in range(rounds):
        put_stuck_mission()
        s = rostub.Session(USER, PW)
        s.login()
        _, (kind, chars) = s.char_enter()
        s.select_char(chars[0][0])
        assert s.map_enter()[0] == "ok"
        st = Stream(s.map_sock, lengths)
        st.drain(2)
        cmds = ("@job %d" % TAEKWON, "@allskill", "@heal") if first else ("@heal",)
        for c in cmds:
            chat(s.map_sock, c)
            st.drain(1.0)
        first = False
        m1, f1 = mission(st, s.map_sock, s.aid)
        st.drain(0.5)
        m2, f2 = mission(st, s.map_sock, s.aid)
        print("  round %2d: use 1 -> %s%s; use 2 -> %s%s" % (r, m1, " (failed)" if f1 else "",
                                                          m2, " (failed)" if f2 else ""))
        picks.append(m1)
        if m1 is None or m1 == STUCK or m1 not in spawned:
            bad.append((r, m1))
        if m2 == m1 and f2:
            kept += 1
        s.quit_game()
        time.sleep(4)  # let the char-server save the registry before the next REPLACE
    ok1 = not bad
    ok2 = kept >= rounds - 2
    print("%s  the stuck target is re-rolled to a monster that spawns (%d/%d)" % ("ok  " if ok1 else "FAIL",
                                                                                rounds - len(bad), rounds))
    print("%s  a normal target can't be changed right away (kept %d/%d)" % ("ok  " if ok2 else "FAIL", kept, rounds))
    print("ALL PASSED" if ok1 and ok2 else "FAILED: %s" % bad)
    return 0 if ok1 and ok2 else 1


if __name__ == "__main__":
    sys.exit(main())
