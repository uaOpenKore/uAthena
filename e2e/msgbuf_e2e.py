#!/usr/bin/env python3
"""e2e: chat message buffers (S. 2026-11-20, audit item 7 + what the reconnect test hit).
  name  npctalk of an NPC whose display name is >= 24 chars ("Funny Gatekeeper's Friend#lv20"): nd->name holds 24
        bytes without a NUL, npctalk memcpy'd it into an uninitialised stack buffer -> stack bytes in the message
  self  dispbottom (clif_disp_onlyself, 0x17f): the length counts a NUL that was never written -> the last byte of
        the message is whatever the send buffer held there
  long  npctalk of 250 chars: strncat(message[255], str, 254) and clif_message's buf[256] overflow the stack
  unit  unittalk of 250 chars: clif_message's buf[256] overflows
After each, "ping" must still answer (the map-server is alive).
NPCs: run_msgbuf.sh. Usage: python3 -I msgbuf_e2e.py <BornRok src/net/PacketTable.cpp> npc|unit
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, NAME, Stream, load_lengths  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def main():
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, load_lengths(sys.argv[1]))
    alive = [True]

    def run(seconds):
        got = []
        try:
            for pid, p in st.packets(seconds):
                if pid == 0x91:
                    s.map_sock.sendall(struct.pack("<H", 0x7D))
                elif pid in (0x8D, 0x17F, 0x8E):
                    got.append((pid, p))
        except (OSError, EOFError, ConnectionError) as e:
            alive[0] = False
            print("    connection lost: %s" % e, flush=True)
        return got

    def gm(text, wait=1.5):
        msg = ("%s : %s" % (NAME, text)).encode("latin-1") + b"\0"
        s.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
        return run(wait)

    def whisper(text, wait=1.5):
        msg = text.encode("latin-1") + b"\0"
        try:
            s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:MsgTest", 24) + msg)
        except OSError:
            alive[0] = False
            return []
        return run(wait)

    def ping(label):
        pong = [p for pid, p in whisper("ping") if pid == 0x17F and b"pong" in p]
        check("%s: the map-server still answers" % label, alive[0] and bool(pong))

    run(2)
    gm("@warp new_zone01 58 101", 3)

    phase = sys.argv[2] if len(sys.argv) > 2 else "npc"
    if phase == "unit":
        msgs = [p for pid, p in whisper("unit", 2) if pid in (0x8D, 0x8E)]
        print("    long unittalk: %d message(s), lengths %s" % (len(msgs), [len(p) for p in msgs]), flush=True)
        ping("after a 250-char unittalk")
        if alive[0]:
            s.quit_game()
        print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
        return 0 if all(results) else 1

    # name: the exact text of the long-name NPC's npctalk (it talks every second on its own timer)
    msgs = [p for pid, p in run(3) if pid == 0x8D]
    want = b"Funny Gatekeeper's Frien : hello"
    texts = [p[8:] for p in msgs]
    good = [t for t in texts if t.split(b"\0")[0] == want and t.endswith(b"\0")]
    check("npctalk of a 30-char NPC name is '<24 chars> : hello', NUL-terminated, no stack bytes",
          bool(msgs) and len(good) == len(msgs), "got %r" % texts[:2])

    # self: every 0x17f must end with its NUL (a long message first fills the send buffer with 'A's)
    bad, seen = [], 0
    for text in ["A" * 200, "x", "A" * 120, "yy", "A" * 60, "zzz"]:
        for pid, p in whisper("self#" + text, 1.0):
            if pid == 0x17F and p[4:].startswith(b"self "):
                seen += 1
                if p[-1] != 0:
                    bad.append(p[4:])
    check("dispbottom (0x17f) ends with a NUL, not a stale send-buffer byte", seen >= 6 and not bad,
          "%d of %d without NUL, e.g. %r" % (len(bad), seen, bad[:1]))

    # long npctalk / long unittalk must not take the map-server down
    msgs = [p for pid, p in whisper("long", 2) if pid == 0x8D]
    print("    long npctalk: %d message(s), lengths %s" % (len(msgs), [len(p) for p in msgs]), flush=True)
    ping("after a 250-char npctalk")
    if alive[0]:
        s.quit_game()
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
