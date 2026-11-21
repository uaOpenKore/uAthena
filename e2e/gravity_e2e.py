#!/usr/bin/env python3
"""e2e: SC_GRAVITATION kept a raw pointer to its skill group (audit item 8, S. 2026-11-20).
A GM High Wizard casts Gravitation Field (484) at (x+6, y), outside the field itself (standing on it, the unit's
removal under the caster ends its SC): its SC_GRAVITATION (val4) points at the group. A Pupa
(immobile) casts Ganbantein (483, 3x3) on the field's 4 corners until no unit is left: the group is freed (ERS).
The Pupa then casts Land Protector (288), a new group that takes the freed ERS entry, and Fire Bolt on the caster:
status_damage took val4 and called skill_delunitgroup on the freed group - here the Land Protector (in WoE:
another player's ground skill). The runner checks map.out for skill_delunitgroup errors
("Group not found!"); the test checks that the Land Protector is still there after the hit.
NPCs: run_msgbuf.sh <run> gravity. Usage: python3 -I gravity_e2e.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402
from streak_e2e import Me  # noqa: E402

UNIT_GRAVITATION, UNIT_LANDPROTECTOR = 0xB8, 0x9D
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
    me = Me(st, s.map_sock, s.aid)
    units = {}      # skill unit id -> unit type, while it is on the ground
    gone = []       # (time, unit id, unit type) of every 0x120
    spawned = {}    # mob class -> gid
    hits = []
    pos, walks = [None], []
    note = me.note

    def note_all(pid, p):
        if pid in (0x11F, 0x1C9):
            units[struct.unpack_from("<I", p, 2)[0]] = p[14] if pid == 0x11F else p[14]
        elif pid == 0x120:
            uid = struct.unpack_from("<I", p, 2)[0]
            gone.append((time.time(), uid, units.pop(uid, None)))
        elif pid == 0x7C:
            spawned[struct.unpack_from("<H", p, 20)[0]] = struct.unpack_from("<I", p, 2)[0]
        elif pid == 0x1DE:  # skill damage: the Pupa's Fire Bolt on the caster (magic always lands)
            sid, src, dst = struct.unpack_from("<HII", p, 2)
            if dst == s.aid and struct.unpack_from("<i", p, 24)[0] > 0:
                hits.append(time.time())
        elif pid == 0x110:
            print("    skill %d failed, cause %d" % (struct.unpack_from("<H", p, 2)[0], p[9]), flush=True)
        elif pid == 0x13E:
            print("    casting skill %d, %d ms" % (struct.unpack_from("<H", p, 14)[0], struct.unpack_from("<I", p, 20)[0]), flush=True)
        elif pid in (0x8E, 0x17F):
            text = p[4:].split(b"\0")[0].decode("latin-1")
            if text.startswith("grav"):
                print("    npc: %s" % text, flush=True)
                xy = text.rsplit(" ", 1)[-1].split(",")
                pos[0] = (int(xy[0]), int(xy[1]))
        elif pid == 0x87:
            walks.append(time.time())
        note(pid, p)
    me.note = note_all
    me.drain(2)

    def whisper(text, wait=1.5):
        msg = text.encode("latin-1") + b"\0"
        s.map_sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:GravTest", 24) + msg)
        me.drain(wait)

    for c in ("@job 4010", "@lvup 98", "@allskill", "@int -300", "@int 99", "@dex -300", "@dex 160",
              "@vit -300", "@vit 99", "@item 717 5", "@heal"):
        me.cmd(c)
    grav = []
    for spot in ("prt_fild08 170 375", "prt_fild08 200 300", "prt_fild08 120 250", "prt_fild08"):
        me.cmd("@warp " + spot, 3)
        me.cmd("@killmonster2", 1)  # the field's own mobs must not walk into it
        whisper("grav", 2.5)
        grav = [u for u, t in units.items() if t == UNIT_GRAVITATION]
        if grav:
            break
    print("    gravitation units on the ground: %d" % len(grav), flush=True)
    whisper("pupa", 2)
    pupa = spawned.get(1008)
    print("    pupa %s" % pupa, flush=True)
    if not grav or not pupa:
        check("setup: Gravitation Field and the Pupa are there", False, "units %s, pupa %s" % (len(grav), pupa))
        return 1
    # Land Protector removes only magic ground skills (Gravitation is misc): Ganbantein (3x3, 80%) on the 4 corners
    for dx, dy in ((5, -1), (7, -1), (5, 1), (7, 1)):
        for _ in range(5):
            if not any(u in units for u in grav):
                break
            before = sum(u in units for u in grav)
            whisper("gb#%d#%d#%d" % (pupa, dx, dy), 1)
            deadline = time.time() + 8
            while time.time() < deadline and sum(u in units for u in grav) == before:
                me.drain(0.5)
            if sum(u in units for u in grav) < before:
                break
    print("    after Ganbantein: gravitation units left %d" % sum(u in units for u in grav), flush=True)
    if any(u in units for u in grav):
        check("setup: Ganbantein removed the Gravitation Field", False)
        return 1
    # a new ground skill takes the freed group's ERS entry: the Pupa's Land Protector next to the caster
    for _ in range(3):  # the Pupa may still be in Ganbantein's cast delay
        me.drain(2.5)
        whisper("lp#%d" % pupa, 1)
        deadline = time.time() + 8
        while time.time() < deadline and not any(t == UNIT_LANDPROTECTOR for t in units.values()):
            me.drain(0.5)
        if any(t == UNIT_LANDPROTECTOR for t in units.values()):
            break
    lp = [u for u, t in units.items() if t == UNIT_LANDPROTECTOR]
    print("    Land Protector units: %d" % len(lp), flush=True)
    if not lp:
        check("setup: the Pupa's Land Protector is there", False)
        return 1
    def can_walk():
        x, y = pos[0]
        n = len(walks)
        s.map_sock.sendall(struct.pack("<HBBB", 0xA7, 0, 0, 0x44)
                           + bytes([((x - 1) >> 2) & 0xFF, (((x - 1) << 6) | ((y >> 4) & 0x3F)) & 0xFF, (y << 4) & 0xFF]))
        me.drain(1.5)
        return len(walks) > n
    print("    caster can walk after the field is gone: %s" % can_walk(), flush=True)
    t_hit = time.time()
    for _ in range(3):
        whisper("fb#%d" % pupa, 1)
        deadline = time.time() + 5
        while time.time() < deadline and not hits:
            me.drain(0.5)
        if hits:
            break
    me.drain(2)
    lp_gone = [g for g in gone if g[2] == UNIT_LANDPROTECTOR and g[0] >= t_hit]
    print("    Fire Bolt hits on the caster: %d, LP units removed after the hit: %d" % (len(hits), len(lp_gone)), flush=True)
    check("a hit on the caster after Land Protector took the field: the Land Protector stays",
          bool(hits) and not lp_gone, "hits %d, LP units removed %d" % (len(hits), len(lp_gone)))
    me.cmd("@killmonster2", 1)
    s.quit_game()
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
