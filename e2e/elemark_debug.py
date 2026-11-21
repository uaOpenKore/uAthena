#!/usr/bin/env python3
"""Debug helper for elemark_e2e.py: shows GM command replies and every packet id after a cast.

Usage: python3 -I elemark_debug.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, chat, load_lengths, use_skill, HUGELING  # noqa: E402


def show(st, seconds, tag):
    ids = []
    for pid, p in st.packets(seconds):
        ids.append("%04x" % pid)
        if pid == 0x8E:
            print("   [%s] msg: %r" % (tag, p[4:].split(b"\0")[0].decode("latin-1")))
        elif pid == 0x110:
            print("   [%s] skill fail: %s" % (tag, p.hex()))
        elif pid == 0x13E:
            print("   [%s] casting: %s" % (tag, p.hex()))
    print("   [%s] packets: %s" % (tag, " ".join(ids)))


def main():
    lengths = load_lengths(sys.argv[1])
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    print("map_enter:", s.map_enter())
    st = Stream(s.map_sock, lengths)
    show(st, 3, "enter")
    for cmd in ("@job 2", "@allskill", "@heal"):
        chat(s.map_sock, cmd)
        show(st, 1.5, cmd)
    chat(s.map_sock, "@monster %d 1" % HUGELING)
    mob = None
    for pid, p in st.packets(4):
        if pid == 0x7C and struct.unpack_from("<H", p, 20)[0] == HUGELING:
            mob = struct.unpack_from("<I", p, 2)[0]
    print("mob", mob)
    use_skill(s.map_sock, 19, mob)
    show(st, 4, "cast FB")
    s.quit_game()


if __name__ == "__main__":
    main()
