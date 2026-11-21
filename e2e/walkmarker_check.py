#!/usr/bin/env python3
"""Does the server still walk a char when the walk packet's unused bytes carry BornRok's marker (01 01 01)?
Usage: python3 -I walkmarker_check.py <BornRok src/net/PacketTable.cpp>"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, NAME, Stream, chat, load_lengths  # noqa: E402

def pos5_dest(p, o):
    return ((p[o + 2] & 0x0F) << 6) | (p[o + 3] >> 2), ((p[o + 3] & 0x03) << 8) | p[o + 4]

s = rostub.Session(USER, PW); s.login(); _, (k, chars) = s.char_enter(); s.select_char(chars[0][0])
assert s.map_enter()[0] == "ok"
st = Stream(s.map_sock, load_lengths(sys.argv[1])); st.drain(2)
chat(s.map_sock, "@where %s" % NAME)
x = y = None
for pid, p in st.packets(1.5):
    if pid == 0x8E:
        m = re.search(r" (\d+) (\d+)$", p[4:].split(b"\0")[0].decode("latin-1"))
        if m: x, y = int(m.group(1)), int(m.group(2))
print("at", x, y)
ok = 0
for dx in (3, -3, 2):
    tx, ty = x + dx, y
    s.map_sock.sendall(struct.pack("<H", 0xA7) + bytes([1, 1, 1])
                       + bytes([(tx >> 2) & 0xFF, ((tx << 6) | ((ty >> 4) & 0x3F)) & 0xFF, (ty << 4) & 0xFF]))
    got = None
    for pid, p in st.packets(2.0):
        if pid == 0x87:
            got = pos5_dest(p, 6)
    print("walk to", (tx, ty), "-> server move ack", got)
    ok += got == (tx, ty)
    x, y = tx, ty
s.quit_game()
print("ALL PASSED" if ok == 3 else "FAILED")
