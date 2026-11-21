#!/usr/bin/env python3
"""e2e: NPC timer bookkeeping (audit item 9, S. 2026-11-20). An NPC-level timer (StopTest, OnTimer1000 / OnTimer5000;
every whisper answers "tmr <getnpctimer(0)> <OnTimer1000 count> <OnTimer5000 count>"):
  1. initnpctimer; at 1.5 s getnpctimer must be ~1500. After OnTimer1000 fired, npc_timerevent set timertick to the
     tick the sequence STARTED (ted->otick) while timer already held the event time: getnpctimer counted twice (2500).
  2. stopnpctimer at 2 s; 1 s later getnpctimer must still be ~2000: stop left timertick set, the value kept running.
  3. startnpctimer: OnTimer5000 must fire 3 s later.
  4. stopnpctimer 0.5 s after it (total ~5500, OnTimer8000 still pending); startnpctimer again: OnTimer5000 must
     not fire again. Stop had saved only the time since the last start (~3500): the resumed timer fired it twice.
NPCs: run_msgbuf.sh <run> timerstop. Usage: python3 -I timerstop_e2e.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402

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
    st.drain(2)

    def ask(cmd):
        """whisper StopTest; returns (timer, f1, f5) from its answer"""
        msg = cmd.encode("latin-1") + b"\0"
        s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:StopTest", 24) + msg)
        for pid, p in st.packets(1.0):
            if pid == 0x91:
                s.map_sock.sendall(struct.pack("<H", 0x7D))
            elif pid in (0x8E, 0x17F):
                text = p[4:].split(b"\0")[0].decode("latin-1")
                if text.startswith("tmr "):
                    v = text.split()
                    return int(v[1]), int(v[2]), int(v[3])
        raise RuntimeError("no answer to %s" % cmd)

    def at(t0, sec):
        left = t0 + sec - time.time()
        if left > 0:
            time.sleep(left)

    t0 = time.time()
    ask("init")
    at(t0, 1.5)
    v = ask("get")
    print("    1.5 s: %s" % (v,), flush=True)
    check("1 running timer after OnTimer1000: getnpctimer ~1500", abs(v[0] - 1500) <= 250 and v[1] == 1, str(v))
    at(t0, 2.0)
    ask("stop")
    at(t0, 3.0)
    v = ask("get")
    print("    stopped at 2.0 s, read at 3.0 s: %s" % (v,), flush=True)
    check("2 stopped timer keeps its value: getnpctimer ~2000 a second after the stop", abs(v[0] - 2000) <= 250, str(v))
    t1 = time.time()
    ask("start")
    fired = None
    while time.time() - t1 < 6.0:
        time.sleep(0.2)
        v = ask("get")
        if v[2] >= 1:
            fired = time.time() - t1
            break
    print("    resumed: OnTimer5000 after %s s (%s)" % ("%.2f" % fired if fired else None, v), flush=True)
    check("3 resumed timer: OnTimer5000 3 s after the resume", fired is not None and abs(fired - 3.0) <= 0.5,
          "after %s s" % fired)
    time.sleep(0.5)
    v_stop = ask("stop")
    v = ask("get")
    ask("start")
    time.sleep(2.5)
    v2 = ask("get")
    ask("stop")
    print("    second stop: %s, after the second resume: %s" % (v, v2), flush=True)
    check("4 second stop keeps the total (~5500) and the second resume fires nothing again",
          abs(v[0] - 5500) <= 400 and v2[1] == 1 and v2[2] == 1, "stop %s, then %s" % (v, v2))
    s.quit_game()
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
