#!/usr/bin/env python3
"""e2e check of the [PADMETRIC] log: send walk/act/tick packets with OpenKore-style and with garbage padding,
log out, and print what the map-server logged for this session.

Usage: python3 -I padmetric_e2e.py <run dir> <BornRok src/net/PacketTable.cpp>
"""
import os
import re
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402


def walk(sock, x, y, pad):
    sock.sendall(struct.pack("<H", 0xA7) + bytes(pad)
                 + bytes([(x >> 2) & 0xFF, ((x << 6) | ((y >> 4) & 0x3F)) & 0xFF, (y << 4) & 0xFF]))


def main():
    run, table = sys.argv[1], sys.argv[2]
    st_len = load_lengths(table)
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok"
    sock = s.map_sock
    st = Stream(sock, st_len)
    st.drain(2)  # the Stream sends one zero-padded tick (89 00 00 00 <tick>) right away
    for i in range(3):
        walk(sock, 50 + i, 100, [0, 0, 0x44])          # OpenKore / BornRok style
        st.drain(0.6)
    walk(sock, 55, 100, [0x12, 0x34, 0x56])            # "real client" garbage
    st.drain(0.6)
    walk(sock, 56, 100, [0x9a, 0x01, 0xfe])
    st.drain(0.6)
    sock.sendall(struct.pack("<H", 0x89) + b"\xab\xcd" + struct.pack("<I", int(time.time() * 1000) & 0xFFFFFFFF))
    st.drain(0.5)
    sock.sendall(struct.pack("<H", 0x190) + b"\0" * 3 + struct.pack("<I", 0x7FFFFFF0) + b"\0" * 9 + b"\0")
    st.drain(0.5)
    sock.sendall(struct.pack("<H", 0x190) + b"\x01\x02\x03" + struct.pack("<I", 0x7FFFFFF0) + b"\x04" * 9 + b"\0")
    st.drain(0.5)
    s.quit_game()
    # an attack request sets prevent_logout: the server quits the session ~10 s later
    for _ in range(30):
        out = open(os.path.join(run, "map.out"), encoding="utf-8", errors="replace").read()
        out = re.sub(r"\x1b\[[0-9;]*m", "", out)
        lines = [ln for ln in out.splitlines() if "[PADMETRIC]" in ln][-2:]
        if lines and " logout " in lines[-1]:
            break
        time.sleep(1)
    for ln in lines:
        print(ln)
    first = [ln for ln in lines if "first_walk" in ln]
    logout = [ln for ln in lines if " logout " in ln]
    ok = (first and first[-1].endswith("pad=000044") and logout
          and " walk=5/z0/c2 first=000044 last=9a01fe" in logout[-1]
          and re.search(r" act=2/z1/c1 first=0{24} last=010203040404040404040404", logout[-1])
          and re.search(r" tick=\d+/z\d+/c1 first=0000 last=", logout[-1]))
    print("ALL PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
