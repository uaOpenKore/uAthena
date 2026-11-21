#!/usr/bin/env python3
"""e2e: @reloadscript must not free the item-script NPC (fake_nd, FAKE_NPC): it is made once at startup and every
item script runs with its id. Probe: TimerTest's whisper "fake" runs getnpctimer(1,"FAKE_NPC") - the map-server
logs "getnpctimer: Invalid NPC" when no NPC of that name exists any more (run_fakenpc.sh checks map.out).
Usage: python3 -I fakenpc_e2e.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402
NAME = "E2eTesterA"
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


def whisper(text, wait=1.5):
    msg = text.encode("latin-1") + b"\0"
    s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:TimerTest", 24) + msg)
    return run_for(wait)


run_for(2)
print("    before: %s" % " | ".join(whisper("fake")), flush=True)
msg = ("%s : @reloadscript" % NAME).encode("latin-1") + b"\0"
s.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
print("    @reloadscript: %s" % " | ".join(run_for(25)), flush=True)
print("    after: %s" % " | ".join(whisper("fake")), flush=True)
s.quit_game()
