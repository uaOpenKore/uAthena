#!/usr/bin/env python3
"""npcidwrap_e2e.py <map-server pid>: the npc/mob id counter at the end of the int range must wrap back to the
NPC range and skip the ids in use, not overflow into negative ids. gdb puts the counter 8 below INT_MAX, a GM
spawns 30 porings; then the counter must be positive and id_db must hold at least 30 more objects (a reused id
still in use would replace an entry)."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, chat  # noqa: E402

pid = sys.argv[1]
def gdb(*cmds):
    args = ["gdb", "-p", pid, "-batch", "-nx"]
    for c in cmds:
        args += ["-ex", c]
    out = subprocess.run(args, capture_output=True, text=True, timeout=120).stdout
    return [l.split("=", 1)[1].strip() for l in out.splitlines() if l.startswith("$")]

s = rostub.Session(USER, PW, log=lambda *a: None)
s.login(); _, r = s.char_enter(); s.select_char(r[1][0][0]); assert s.map_enter()[0] == "ok"
s.map_alive(2)
before = gdb("set var npc_id = 2147483639", "print id_db->size(id_db)", "print npc_id")
print("before: id_db=%s npc_id=%s" % (before[0], before[1]), flush=True)
chat(s.map_sock, "@monster poring 30")
s.map_alive(4)
after = gdb("print id_db->size(id_db)", "print npc_id")
print("after:  id_db=%s npc_id=%s" % (after[0], after[1]), flush=True)
grown, nid = int(after[0]) - int(before[0]), int(after[1])
ok = True
if nid <= 0:
    print("FAIL  the id counter overflowed to %d" % nid); ok = False
if grown < 30: # (+3 more on both builds: objects spawned with the porings)
    print("FAIL  id_db grew by %d, under 30 (ids reused while in use replace entries)" % grown); ok = False
s.quit_game(wait=1)
if not ok:
    sys.exit(1)
print("ok    counter wrapped to %d, 30 new objects, none replaced" % nid); print("ALL PASSED")
