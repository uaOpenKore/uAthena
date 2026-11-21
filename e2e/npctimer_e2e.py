#!/usr/bin/env python3
"""e2e: a player's attached NPC timer must not stay stuck after its NPC is unloaded (@unloadnpc / @reloadscript).

e2e_npc/timertest.txt: NPC TimerTest, whisper "start" -> attachnpctimer + initnpctimer, OnTimer3000 says "fired".
  1. GM starts the timer, then @unloadnpc TimerTest: the attached timer still fires 3 s later, finds no NPC.
  2. @loadnpc e2e_npc/timertest.txt, start again: the new timer must fire. The old map-server left the fired
     timer's id in sd->npc_timer_id, so every later attached timer of that player silently did not start,
     and the logout "cleaned up" whatever timer had reused that id (another timer deleted, a foreign pointer
     given to ers_free).
  3. GM logs out: no timer errors in the map-server output.

Usage: python3 -I npctimer_e2e.py <run dir> <BornRok src/net/PacketTable.cpp>
"""
import os
import re
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402

USER, PW, NAME = "e2etesta", "e2epass1", "E2eTesterA"


def main():
    run, table = sys.argv[1], sys.argv[2]
    lengths = load_lengths(table)
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, lengths)
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)

    def run_for(seconds):
        said = []
        for pid, p in st.packets(seconds):
            if pid == 0x91:
                s.map_sock.sendall(struct.pack("<H", 0x7D))
            elif pid in (0x8E, 0x17F):
                said.append(p[4:].split(b"\0")[0].decode("latin-1"))
        return said

    def chat(text, wait=1.5):
        msg = ("%s : %s" % (NAME, text)).encode("latin-1") + b"\0"
        s.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
        return run_for(wait)

    def whisper(text, wait=1.0):
        msg = text.encode("latin-1") + b"\0"
        s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:TimerTest", 24) + msg)
        return run_for(wait)

    run_for(2)
    said = whisper("start")
    check("the attached timer starts", any("timertest started" in x for x in said), " | ".join(said))
    said = chat("@unloadnpc TimerTest")
    print("    @unloadnpc: %s" % " | ".join(said), flush=True)
    run_for(4)  # the old timer fires with its NPC gone
    said = chat("@loadnpc e2e_npc/timertest.txt", 2)
    print("    @loadnpc: %s" % " | ".join(said), flush=True)
    said = whisper("start2", 1.0) + run_for(4)  # startnpctimer: does not stop a running timer first
    check("after the NPC was reloaded, a new attached timer starts and fires", any("timertest fired" in x for x in said),
          " | ".join(said))
    s.quit_game(wait=3)
    out = re.sub(r"\x1b\[[0-9;]*m", "", open(os.path.join(run, "map.out"), encoding="latin-1").read())
    bad = [ln for ln in out.splitlines() if "delete_timer error" in ln or "ers_free" in ln or "npc_timerevent_quit" in ln]
    check("no timer errors at logout", not bad, " | ".join(bad[:3]))
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
