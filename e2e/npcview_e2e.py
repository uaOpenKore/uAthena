#!/usr/bin/env python3
"""npcview_e2e.py <PacketTable.cpp>: NPC sprites per client. The Novice vending machine in prt_church (renewal
sprite 2_VENDING_MACHINE1 = 564) must reach BornRok (map login marked "BRK\\x01") as 564 and the original client
(37 33 36 64) as its classic stand-in 888; and the original client must get NO sprite id outside what uaRO.exe
knows (45, 46-125, 139, 700-957, hidden/invisible) from any NPC on the maps visited."""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths, chat  # noqa: E402
lengths = load_lengths(sys.argv[1])
SAFE = set(range(46, 126)) | set(range(700, 958)) | set(range(1001, 4000)) | {45, 111, 139, 844, 32767, 65535}  # mobs too
def visit(pad, where):
    s = rostub.Session(USER, PW, log=lambda *a: None)
    s.login(); _, r = s.char_enter(); s.select_char(r[1][0][0]); assert s.map_enter(pad13=pad)[0] == "ok"
    st = Stream(s.map_sock, lengths); s.map_sock.sendall(struct.pack("<H", 0x7D))
    seen = {}
    def collect(sec):
        for pid, p in st.packets(sec):
            if pid == 0x91: s.map_sock.sendall(struct.pack("<H", 0x7D))
            if pid in (0x78, 0x1d8, 0x22a, 0x7c, 0x1b0) and len(p) >= 22:
                bid = struct.unpack_from("<I", p, 2)[0]
                if bid < 1100000000: continue
                cls = struct.unpack_from("<H", p, 20 if pid == 0x7c else 14)[0] if pid != 0x1b0 else struct.unpack_from("<I", p, 7)[0]
                seen[bid] = cls
    collect(2)
    for w in where:
        chat(s.map_sock, "@warp " + w); collect(4)
    chat(s.map_sock, "@warp new_zone01 55 99"); collect(2)  # leave the char where the other tests expect it
    s.quit_game(wait=1)
    return seen
maps = ["prt_church 187 31", "malangdo 140 115", "mora 56 140", "dicastes01 200 200", "prontera 156 180"]
brk = visit(b"BRK\x01", maps)
old = visit(b"\x37\x33\x36\x64", maps)   # the same server run: the NPC ids are the same
bad = sorted(set(c for c in old.values() if c not in SAFE))
print("original client: %d NPCs seen, sprite ids outside uaRO.exe's set: %s" % (len(old), bad))
print("BornRok: %d NPCs seen, renewal sprites among them: %d" % (len(brk), sum(1 for c in brk.values() if 400 <= c <= 699)))
vm = [i for i, c in brk.items() if c == 564]
vm_brk = bool(vm); vm_old = bool(vm) and old.get(vm[0]) == 888
print("Novice vending machine: original client gets 888: %s, BornRok gets 564: %s" % (vm_old, vm_brk))
if bad or not vm_old or not vm_brk:
    print("FAIL"); sys.exit(1)
print("ok"); print("ALL PASSED")
