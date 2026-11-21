#!/usr/bin/env python3
"""Debug helper for streak_e2e.py: shows replies to @where and the packets after attacking a second mob.

Usage: python3 -I streak_debug.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, chat, load_lengths  # noqa: E402

HUGELING = 1284


def show(st, seconds, tag, aid):
    t0 = time.time()
    for pid, p in st.packets(seconds):
        dt = time.time() - t0
        if pid == 0x8E:
            print("   [%s %.1fs] msg: %r" % (tag, dt, p[4:].split(b"\0")[0].decode("latin-1")))
        elif pid == 0x8A:
            src, dst = struct.unpack_from("<II", p, 2)
            print("   [%s %.1fs] 8a src=%d dst=%d dmg=%d type=%d" % (tag, dt, src, dst, struct.unpack_from("<h", p, 22)[0], p[26]))
        elif pid in (0x7C, 0x78, 0x7B):
            print("   [%s %.1fs] unit %04x id=%d" % (tag, dt, pid, struct.unpack_from("<I", p, 2)[0]))
        elif pid == 0x80:
            print("   [%s %.1fs] vanish id=%d type=%d" % (tag, dt, struct.unpack_from("<I", p, 2)[0], p[6]))
        elif pid in (0x87, 0x86):
            pass
        elif pid == 0x139:
            print("   [%s %.1fs] attack range/out of range %s" % (tag, dt, p.hex()))


def main():
    lengths = load_lengths(sys.argv[1])
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    print("map_enter:", s.map_enter())
    st = Stream(s.map_sock, lengths)
    st.drain(3)
    chat(s.map_sock, "@where")
    show(st, 1.5, "@where", s.aid)
    chat(s.map_sock, "@monster %d 2" % HUGELING)
    ids = []
    for pid, p in st.packets(4):
        if pid == 0x7C and struct.unpack_from("<H", p, 20)[0] == HUGELING:
            ids.append(struct.unpack_from("<I", p, 2)[0])
    print("mobs", ids)
    for target in ids:
        pkt = struct.pack("<H", 0x190) + b"\0" * 3 + struct.pack("<I", target) + b"\0" * 9 + b"\0"
        s.map_sock.sendall(pkt)
        show(st, 5, "attack %d" % target, s.aid)
    s.quit_game()


if __name__ == "__main__":
    main()
