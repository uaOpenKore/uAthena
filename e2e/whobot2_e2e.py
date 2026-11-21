#!/usr/bin/env python3
"""e2e check of the 20.11 @whobot rules: more than 0.4 ticks/s, or OpenKore's walk padding with under 0.15 ticks/s.

Five sessions, each walks once (its padding) and then ticks at its own pace:
  FAST   E2eTesterV  pad 00 00 44, a tick every 1.43 s (0.7/s)  - the ~1/s farm, under the old 1/s threshold
  OKSLOW TestChar    pad 00 00 44, a tick every 12 s (0.08/s)   - the 5.83.145.35 / 180.190.136.76 farms
  ORIG   TestChar2   pad 37 34 00, a tick every 12 s            - the original client: must NOT be listed
  BORN   TestChar3   pad 00 00 44, a tick every 4 s (0.25/s)    - BornRok before 0.0.53.0: must NOT be listed
  GM     E2eTesterA  no walk, a tick every 5 s (Stream)         - runs @whobot after ~70 s; level >= 60 needed
New build: FAST and OKSLOW listed (with their reason), the others not, summary "2 of 5 online".
Old build (> 1 tick/s only): nobody listed.

Usage: python3 -I whobot2_e2e.py <run dir> <BornRok src/net/PacketTable.cpp> [seconds online, default 70]
"""
import os
import re
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402

GM = ("e2etesta", "e2epass1", "E2eTesterA")
OKORE, ORIG = bytes([0x00, 0x00, 0x44]), bytes([0x37, 0x34, 0x00])
BOTS = [  # account, password, name, walk padding, seconds between ticks
    ("e2etestv", "e2epass1", "E2eTesterV", OKORE, 1.43),
    ("testacc", "testpass", "TestChar", OKORE, 12.0),
    ("testacc2", "testpass", "TestChar2", ORIG, 12.0),
    ("testacc3", "testpass", "TestChar3", OKORE, 4.0),
]


def enter(acc, pw):
    s = rostub.Session(acc, pw)
    s.login()
    _, (kind, chars) = s.char_enter()
    assert kind == "list" and chars, "no character for %s" % acc
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok", "map enter failed for %s" % acc
    return s


def bot_loop(sock, every, stop, sent):
    """Tick every `every` seconds and swallow whatever the server sends, until `stop` is set."""
    sock.setblocking(False)
    nxt = time.time()
    while not stop.is_set():
        now = time.time()
        if now >= nxt:
            sock.sendall(struct.pack("<HHI", 0x89, 0, int(now * 1000) & 0xFFFFFFFF))
            sent[0] += 1
            nxt += every
        try:
            while sock.recv(65536):
                pass
        except (BlockingIOError, socket.timeout):
            pass
        time.sleep(0.02)
    sock.setblocking(True)


def chat(sock, name, text):
    msg = ("%s : %s" % (name, text)).encode("latin-1") + b"\0"
    sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)


def main():
    run, table = sys.argv[1], sys.argv[2]
    online = int(sys.argv[3]) if len(sys.argv) > 3 else 70
    lengths = load_lengths(table)

    stop, threads, sessions, sent = threading.Event(), [], [], {}
    for acc, pw, name, pad, every in BOTS:
        s = enter(acc, pw)
        # one walk with this client's padding, so @whobot knows it (pos 50,100 like whobot_e2e.py)
        s.map_sock.sendall(struct.pack("<H", 0xA7) + pad + bytes([50 >> 2, ((50 << 6) | (100 >> 4)) & 0xFF, (100 << 4) & 0xFF]))
        sent[name] = [0]
        th = threading.Thread(target=bot_loop, args=(s.map_sock, every, stop, sent[name]), daemon=True)
        th.start()
        threads.append(th)
        sessions.append(s)
    t_last = time.time()

    gm = enter(GM[0], GM[1])
    st = Stream(gm.map_sock, lengths)
    st.drain(max(0, online - (time.time() - t_last)))   # the Stream ticks every 5 s, like a client

    chat(gm.map_sock, GM[2], "@whobot")
    said = []
    for pid, p in st.packets(4):
        if pid == 0x8E:
            said.append(p[4:].split(b"\0")[0].decode("latin-1"))
    print("ticks sent: " + ", ".join("%s %d" % (n, c[0]) for n, c in sent.items()))
    print("@whobot said:")
    for ln in said:
        print("  | " + ln)

    stop.set()
    for th in threads:
        th.join()
    for s in sessions:
        s.quit_game()
    gm.quit_game()

    fails = []

    def line_of(name):
        ls = [ln for ln in said if ln.startswith(name + " (")]
        return ls[0] if ls else ""

    v = line_of("E2eTesterV")
    m = re.search(r"(\d+\.\d\d) ticks/s", v)
    if not v or not m or not 0.5 <= float(m.group(1)) <= 0.9 or "ticks too often" not in v:
        fails.append("@whobot lists E2eTesterV (0.7 ticks/s) as ticking too often")
    t = line_of("TestChar")
    m = re.search(r"(\d+\.\d\d) ticks/s", t)
    if not t or not m or float(m.group(1)) >= 0.15 or "OpenKore walk pad, ticks too rarely" not in t or "000044" not in t:
        fails.append("@whobot lists TestChar (OpenKore pad, 0.08 ticks/s) as OpenKore walk pad + ticks too rarely")
    if line_of("TestChar2"):
        fails.append("@whobot does not list TestChar2 (the original client's pad, 0.08 ticks/s)")
    if line_of("TestChar3"):
        fails.append("@whobot does not list TestChar3 (OpenKore pad, a tick every 4 s = BornRok)")
    if line_of("E2eTesterA"):
        fails.append("@whobot does not list the GM (a tick every 5 s, no walk)")
    if not any(re.search(r"\b2 of 5 online: 1 tick more than 0\.40/s, 1 walk like OpenKore and tick under 0\.15/s", ln) for ln in said):
        fails.append("@whobot summary: 2 of 5 online, 1 + 1")
    for f in fails:
        print("FAIL: " + f)
    print("ALL PASSED" if not fails else "FAILED (%d)" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
