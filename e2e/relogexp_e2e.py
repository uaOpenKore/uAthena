#!/usr/bin/env python3
"""e2e: frequent reconnects must not roll the exp back. Prod char logs 15-20.11: the Priest bot Sacerdote11 logged
in 3135 times in 4.6 days (every ~2 min) and 11 autosaves were dropped as "non-existant/offline character"; a player
says his Priest bot's exp went down although it never died.

Each cycle: log in, read the exp (TimerTest whisper "exp"), gain 20000/20000 ("gexp"), then end the session:
  kill   drop the map connection with RST (the bot or client process died), log in again at once
  quit   0x18a quit, log in again at once
  csel   back to the char select (0xb2) and select the char again
  killw  RST, wait 0-12 s, log in again
The exp seen at the start of a cycle must be >= the exp seen at the end of the cycle before it.
The TimerTest NPC comes from run_npctimer.sh (run it once on the run dir first).
Usage: python3 -I relogexp_e2e.py <BornRok src/net/PacketTable.cpp> [cycles, default 24]
"""
import os
import random
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402

MODES = ["kill", "quit", "csel", "killw"]


class Game:
    def __init__(self, lengths):
        self.lengths = lengths
        self.s = rostub.Session(USER, PW, log=lambda *a: None)
        self.st = None

    def enter(self, relogin=True):
        t0 = time.time()
        if relogin:
            self.s.login()
        for _ in range(3):
            _, res = self.s.char_enter()
            if res[0] == "list":
                break
            print("    char_enter refused: %s, retry" % (res,), flush=True)
            time.sleep(2)
            self.s.login()
        else:
            raise RuntimeError("char_enter kept refusing")
        self.s.select_char(res[1][0][0])
        r = self.s.map_enter()
        if r[0] != "ok":
            raise RuntimeError("map_enter: %s" % (r,))
        self.st = Stream(self.s.map_sock, self.lengths)
        return time.time() - t0

    def said(self, seconds):
        out = []
        for pid, p in self.st.packets(seconds):
            if pid == 0x91:
                self.s.map_sock.sendall(struct.pack("<H", 0x7D))
            elif pid in (0x8E, 0x17F):
                out.append(p[4:].split(b"\0")[0].decode("latin-1"))
        return out

    def whisper(self, text, wait=1.0):
        msg = text.encode("latin-1") + b"\0"
        self.s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:TimerTest", 24) + msg)
        for line in self.said(wait):
            if line.startswith("expnow "):
                # digits only: before the 0x17f NUL fix (main 195547b7) the line could end in a stale byte
                return tuple(int("".join(ch for ch in x if ch.isdigit()) or 0) for x in line.split()[1:5])
        return None


def total(e):
    """(base level, base exp, job level, job exp) -> comparable (levels first)."""
    return (e[0], e[1]), (e[2], e[3])


def main():
    lengths = load_lengths(sys.argv[1])
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    random.seed(20261120)
    g = Game(lengths)
    g.enter()
    g.said(1.5)
    last_end, rollbacks, waits = None, [], []
    for c in range(cycles):
        mode = MODES[c % len(MODES)]
        start = g.whisper("exp")
        if start is None:
            raise RuntimeError("cycle %d: no exp answer" % c)
        if last_end is not None:
            b0, j0 = total(last_end)
            b1, j1 = total(start)
            if b1 < b0 or j1 < j0:
                rollbacks.append((c, mode_prev, last_end, start))
                print("    ROLLBACK cycle %d (after %s): end %s -> start %s" % (c, mode_prev, last_end, start), flush=True)
        end = g.whisper("gexp")
        if end is None:
            raise RuntimeError("cycle %d: no gexp answer" % c)
        last_end, mode_prev = end, mode
        if mode == "kill":
            g.s.kill_map()
            w = g.enter()
        elif mode == "quit":
            g.s.quit_game(wait=0.2)
            w = g.enter()
        elif mode == "csel":
            g.s.charselect_return(wait=1.0)
            w = g.enter(relogin=False)
        else:
            g.s.kill_map()
            time.sleep(random.uniform(0, 12))
            w = g.enter()
        waits.append(w)
        g.said(1.0)
        print("  %2d %-5s end %s, back in %.1f s" % (c, mode, end, w), flush=True)
    final = g.whisper("exp")
    if final is not None and (total(final)[0] < total(last_end)[0] or total(final)[1] < total(last_end)[1]):
        rollbacks.append((cycles, mode_prev, last_end, final))
    g.s.quit_game()
    print("reconnect time: median %.1f s, max %.1f s" % (sorted(waits)[len(waits) // 2], max(waits)))
    ok = not rollbacks
    print(("ok  " if ok else "FAIL") + "  %d reconnects (kill/quit/csel/killw), exp rollbacks: %d" % (cycles, len(rollbacks)))
    print("ALL PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
