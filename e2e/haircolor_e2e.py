#!/usr/bin/env python3
"""e2e: the Stylist (npc/custom/dye.txt) offers hair colours 0-20 with setlook 6; the server clamped everything
above max_hair_color (8) to 8, so colours 9-20 became red 8 and were saved so. Both clients have hair palettes
0-127 for every style. Checks: setlook 6 with 15 and 20 keeps them (getlook(6)), 21 is clamped to 20, and the
colour is still there after a relog. NPCs: run_msgbuf.sh <run> haircolor.
Usage: python3 -I haircolor_e2e.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def session(lengths):
    s = rostub.Session(USER, PW, log=lambda *a: None)
    s.login()
    _, res = s.char_enter()
    s.select_char(res[1][0][0])
    assert s.map_enter()[0] == "ok"
    return s, Stream(s.map_sock, lengths)


def hair(s, st, n):
    msg = ("hair#%d" % n).encode() + b"\0"
    s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:MsgTest", 24) + msg)
    for pid, p in st.packets(1.5):
        if pid == 0x91:
            s.map_sock.sendall(struct.pack("<H", 0x7D))
        elif pid in (0x8E, 0x17F):
            t = p[4:].split(b"\0")[0].decode("latin-1")
            if t.startswith("hair "):
                return int(t.split()[1])
    return None


def main():
    lengths = load_lengths(sys.argv[1])
    s, st = session(lengths)
    st.drain(1.5)
    got = {n: hair(s, st, n) for n in (5, 15, 20, 21)}
    print("    setlook 6 -> getlook(6): %s" % got, flush=True)
    check("colours 9-20 stay what the Stylist set (15 -> 15, 20 -> 20)", got[15] == 15 and got[20] == 20, str(got))
    check("above the limit is clamped to it (21 -> 20)", got[21] == 20, str(got))
    hair(s, st, 15)
    s.quit_game(wait=1)                   # the logout save writes hair_color (it can take a few seconds here)
    saved = None
    for _ in range(50):                  # the quit may wait prevent_logout (10 s) before the final save
        out = subprocess.run(["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-e",
                              "SELECT hair_color FROM `char` WHERE char_id=150003"], capture_output=True, text=True).stdout
        saved = int(out.strip()) if out.strip().isdigit() else None
        if saved == 15:
            break
        time.sleep(0.5)
    check("colour 15 is what the logout saves", saved == 15, "hair_color in the db: %s" % saved)
    s, st = session(lengths)              # back to the default colour for the other tests
    st.drain(1)
    hair(s, st, 0)
    s.quit_game(wait=1)
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
