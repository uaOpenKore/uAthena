#!/usr/bin/env python3
"""e2e: the wedding status of marriage.txt must last. sc_start SC_Wedding,3600000000 (1000 h, the value marriage.txt
had since eAthena) does not fit a script int: it became -694967296 and the status ended at once. TimerTest NPC
(run_npctimer.sh writes it): wed_old / wed_new start it with the old / new literal, wedcheck reports checkoption(0x1000)
2 s later and ends it. Usage: python3 -I wedding_e2e.py <BornRok src/net/PacketTable.cpp>"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402
s = rostub.Session("e2etesta", "e2epass1")
s.login()
_, (kind, chars) = s.char_enter()
s.select_char(chars[0][0])
assert s.map_enter()[0] == "ok"
st = Stream(s.map_sock, load_lengths(sys.argv[1]))


def run_for(sec):
    said = []
    for pid, p in st.packets(sec):
        if pid == 0x91:
            s.map_sock.sendall(struct.pack("<H", 0x7D))
        elif pid in (0x8E, 0x17F):
            said.append(p[4:].split(b"\0")[0].decode("latin-1"))
    return said


def whisper(text, wait=1.0):
    msg = text.encode("latin-1") + b"\0"
    s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:TimerTest", 24) + msg)
    return run_for(wait)


results = []
run_for(2)
for name, expect in (("wed_old", None), ("wed_new", "1")):
    whisper(name)
    run_for(2)
    said = [x for x in whisper("wedcheck") if "wedding on=" in x]
    got = said[0].split("=")[1] if said else "?"
    print("    %s: still on after 2 s = %s" % (name, got), flush=True)
    results.append((name, got))
old = dict(results)["wed_old"]
new = dict(results)["wed_new"]
print("info  the old literal (3600000000): wedding still on = %s (0 = ended at once)" % old)
print(("ok  " if new == "1" else "FAIL") + "  the new literal (3600000 = 1 h): the wedding status stays")
s.quit_game()
sys.exit(0 if new == "1" else 1)
