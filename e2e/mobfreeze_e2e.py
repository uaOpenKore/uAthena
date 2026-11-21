#!/usr/bin/env python3
"""e2e: permanent mobs on a map nobody visited for > 24.8 days must still walk, attack and respawn (the 32-bit
tick wraps DIFF_TICK of stale mob ticks; S.: "after ~2 months without a restart, mobs on some maps did not walk,
attack or spawn").

Mobs with a respawn delay are not "dynamic" (npc.c: dynamic_mobs caches only delay-0 spawns), so they stay on
their map for the whole uptime. The run dir loads e2e_npc/mobfreeze.txt: 20 Porings all over new_1-1 (a map with
no NPCs and no other spawns) and 6 aggressive Zombies around (114,42), all with a 2 s / 1 s respawn delay.
The map-server runs with warp.so (LD_PRELOAD): its CLOCK_MONOTONIC runs ahead by the ms in $WARP_FILE.
  1. GM (E2eTesterA, level 99) goes to new_1-1 114 42: mobs walk, zombies attack (baseline).
  2. GM goes back to new_zone01: new_1-1 is empty, its mobs are not processed (mob_ai_*_emptymap / active maps).
  3. The map-server's clock jumps 10 + 10 + 6 days (steps < 24.8 days, the loop runs between them).
  4. GM goes to new_1-1 114 42 again: the mobs must walk and the zombies attack.
  5. @killmonster2 there: the mobs must respawn within 20 s.

Usage: python3 -I mobfreeze_e2e.py <run dir> <BornRok src/net/PacketTable.cpp> <warp file> [cumulative days, default 10,20,26]
(10,20,30,40,50,60 takes the tick past 2^32 ms: TICK_START_MS 1 day + 60 days > 49.7 days)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402

USER, PW, NAME = "e2etesta", "e2epass1", "E2eTesterA"
TEST_MOBS = {1002, 1015}  # Poring, Zombie (e2e_npc/mobfreeze.txt)
DAY = 86400000


class Gm:
    def __init__(self, st, sock, aid):
        self.st, self.sock, self.aid = st, sock, aid

    def run(self, seconds, on=None):
        for pid, p in self.st.packets(seconds):
            if pid == 0x91:  # map change: the client must ack the load
                self.sock.sendall(struct.pack("<H", 0x7D))
            if on:
                on(pid, p)

    def cmd(self, text, wait=1.5):
        msg = ("%s : %s" % (NAME, text)).encode("latin-1") + b"\0"
        self.sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
        said = []
        self.run(wait, lambda pid, p: said.append(p[4:].split(b"\0")[0].decode("latin-1")) if pid == 0x8E else None)
        return said

    def watch(self, seconds):
        """Moves (0x86) of other units and attacks (0x8a) on the GM during `seconds`."""
        r = {"moves": 0, "movers": set(), "hits": 0, "attackers": set()}

        def on(pid, p):
            if pid == 0x86:
                uid = struct.unpack_from("<I", p, 2)[0]
                if uid != self.aid:
                    r["moves"] += 1
                    r["movers"].add(uid)
            elif pid == 0x8A:
                src, dst = struct.unpack_from("<II", p, 2)
                if dst == self.aid and src != self.aid:
                    r["hits"] += 1
                    r["attackers"].add(src)
        self.run(seconds, on)
        return r

    def watch_spawns(self, seconds):
        spawned = set()

        def on(pid, p):
            if pid == 0x7C and struct.unpack_from("<H", p, 20)[0] in TEST_MOBS:
                spawned.add(struct.unpack_from("<I", p, 2)[0])
        self.run(seconds, on)
        return len(spawned)


def warp_clock(path, ms):
    with open(path, "w") as f:
        f.write("%d\n" % ms)


def main():
    run, table, warp_file = sys.argv[1], sys.argv[2], sys.argv[3]
    steps = [int(d) for d in (sys.argv[4] if len(sys.argv) > 4 else "10,20,26").split(",")]
    warp_clock(warp_file, 0)
    lengths = load_lengths(table)
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    assert kind == "list" and chars, "no character"
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok", "map enter failed"
    gm = Gm(Stream(s.map_sock, lengths), s.map_sock, s.aid)
    gm.run(2)
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)

    def visit(label):
        gm.cmd("@heal", 1)
        gm.cmd("@warp new_1-1 114 42", 3)
        w = gm.watch(12)
        check("%s: mobs on new_1-1 walk" % label, w["moves"] > 0,
              "%d moves by %d units in 12 s" % (w["moves"], len(w["movers"])))
        check("%s: zombies attack the GM" % label, w["hits"] > 0,
              "%d hits by %d mobs" % (w["hits"], len(w["attackers"])))

    visit("baseline")
    gm.cmd("@heal", 1)
    gm.cmd("@warp new_zone01 56 100", 3)
    gm.run(3)  # new_1-1 is empty again
    for total in [d * DAY for d in steps]:
        warp_clock(warp_file, total)
        gm.run(4)  # the map-server runs a few rounds with the new clock
        print("    clock +%d days" % (total // DAY), flush=True)

    visit("after %d days without players" % steps[-1])
    said = gm.cmd("@killmonster2", 2)
    print("    @killmonster2: %s" % " | ".join(said), flush=True)
    n = gm.watch_spawns(20)
    check("after %d days: killed mobs respawn within 20 s" % steps[-1], n > 0, "%d test mobs respawned in view" % n)

    gm.cmd("@heal", 1)
    s.quit_game()
    warp_clock(warp_file, 0)
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
