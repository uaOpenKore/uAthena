#!/usr/bin/env python3
"""e2e check of @whobot and the tick rate in the [PADMETRIC] logout line.

V ("bot") sends a tick every 0.1 s (OpenKore's default ai_sync) and one OpenKore-style walk; A (GM, needs level
>= 60 in the local DB) ticks every 5 s like a client. After ~66 s online A runs @whobot: V must be listed with
~10 ticks/s and its walk pad, A must not. Then both quit and the logout lines must carry online=/tick_rate=.

Usage: python3 -I whobot_e2e.py <run dir> <BornRok src/net/PacketTable.cpp> [seconds online, default 66]
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

GM = ("e2etesta", "e2epass1", "E2eTesterA", 2000006)
BOT = ("e2etestv", "e2epass1", "E2eTesterV", 2000007)


def enter(acc):
    s = rostub.Session(acc[0], acc[1])
    s.login()
    _, (kind, chars) = s.char_enter()
    assert kind == "list" and chars, "no character for %s" % acc[0]
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok", "map enter failed for %s" % acc[0]
    return s


def bot_loop(sock, stop, sent):
    """Tick every 0.1 s and swallow whatever the server sends, until `stop` is set."""
    sock.setblocking(False)
    nxt = time.time()
    while not stop.is_set():
        now = time.time()
        if now >= nxt:
            sock.sendall(struct.pack("<HHI", 0x89, 0, int(now * 1000) & 0xFFFFFFFF))
            sent[0] += 1
            nxt += 0.1
        try:
            while sock.recv(65536):
                pass
        except (BlockingIOError, socket.timeout):
            pass
        time.sleep(0.01)
    sock.setblocking(True)


def chat(sock, name, text):
    msg = ("%s : %s" % (name, text)).encode("latin-1") + b"\0"
    sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)


def logout_line(run, aid):
    out = open(os.path.join(run, "map.out"), encoding="utf-8", errors="replace").read()
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)
    lines = [ln for ln in out.splitlines() if "[PADMETRIC] logout aid=%d " % aid in ln]
    return lines[-1] if lines else ""


def main():
    run, table = sys.argv[1], sys.argv[2]
    online = int(sys.argv[3]) if len(sys.argv) > 3 else 66
    lengths = load_lengths(table)

    bot = enter(BOT)
    # one OpenKore-style walk (pad 00 00 44) so @whobot has a walk pad to show
    bot.map_sock.sendall(struct.pack("<H", 0xA7) + bytes([0, 0, 0x44]) + bytes([50 >> 2, ((50 << 6) | (100 >> 4)) & 0xFF, (100 << 4) & 0xFF]))
    stop, sent = threading.Event(), [0]
    th = threading.Thread(target=bot_loop, args=(bot.map_sock, stop, sent), daemon=True)
    th.start()
    t0 = time.time()

    gm = enter(GM)
    st = Stream(gm.map_sock, lengths)
    st.drain(max(0, online - (time.time() - t0)))   # the Stream ticks every 5 s, like a client

    chat(gm.map_sock, GM[2], "@whobot")
    said = []
    for pid, p in st.packets(4):
        if pid == 0x8E:
            said.append(p[4:].split(b"\0")[0].decode("latin-1"))
    print("bot sent %d ticks in %.0f s" % (sent[0], time.time() - t0))
    print("@whobot said:")
    for ln in said:
        print("  | " + ln)

    stop.set()
    th.join()
    bot.quit_game()
    gm.quit_game()
    time.sleep(2)
    lb, lg = logout_line(run, BOT[3]), logout_line(run, GM[3])
    print("bot logout: " + lb[:200])
    print("gm  logout: " + lg[:200])

    fails = []
    bl = [ln for ln in said if BOT[2] in ln]
    rate = re.search(r"(\d+\.\d+) ticks/s", bl[0]) if bl else None
    if not bl or not rate or not 8.0 <= float(rate.group(1)) <= 10.5:
        fails.append("@whobot lists the bot at ~10 ticks/s")
    if bl and "000044" not in bl[0]:
        fails.append("@whobot shows the bot's walk pad 000044")
    if bl and "127.0.0.1" not in bl[0]:
        fails.append("@whobot shows the bot's IP")
    if any(GM[2] in ln for ln in said):
        fails.append("@whobot does not list the GM (a tick every 5 s)")
    if not any(re.search(r"\b1 of 2\b", ln) for ln in said):
        fails.append("@whobot summary: 1 of 2 online")
    m = re.search(r" online=(\d+)s tick_rate=(\d+\.\d)/s", lb)
    if not m or int(m.group(1)) < online - 5 or not 8.0 <= float(m.group(2)) <= 10.5:
        fails.append("bot logout line: online >= %d s, tick_rate ~10/s" % (online - 5))
    m = re.search(r" online=(\d+)s tick_rate=(\d+\.\d)/s", lg)
    if not m or float(m.group(2)) > 0.5:
        fails.append("GM logout line: tick_rate ~0.2/s")
    for f in fails:
        print("FAIL: " + f)
    print("ALL PASSED" if not fails else "FAILED (%d)" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
