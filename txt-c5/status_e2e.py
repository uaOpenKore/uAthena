#!/usr/bin/env python3
"""e2e (TXT): the first status block (0x00bd) must come right after LoadEndAck.

The map-server holds a character's first status block until the char-server answers the status-change
request 0x2afc with 0x2b1d. The TXT char-server only answered when the character had saved status
changes, so a character without buffs got its status ~3 s late, from a safety timer that also logs
"sc_data reply never arrived".

Usage: python3 -I status_e2e.py <run dir>   (uses the c1 e2e helpers; stand on ports 16900/16121/15121)
"""
import os
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
from e2elib import Stream, ensure_account, enter_map, load_lengths, read_out  # noqa: E402

USER, PW, NAME = "c5stat", "c5statpw", "C5Stat"


def main():
    run = sys.argv[1]
    lengths = load_lengths()
    mark = len(read_out(run, "map"))
    print("account:", ensure_account(USER, PW))
    s = enter_map(USER, PW, NAME)
    st = Stream(s.map_sock, lengths)
    t0 = time.time()
    first_bd = None
    for pid, _ in st.packets(6.0):
        if pid == 0x00BD and first_bd is None:
            first_bd = time.time() - t0
    s.quit_game()
    time.sleep(1)
    late = "sc_data reply never arrived" in read_out(run, "map")[mark:]
    ok = True
    print("0x00bd after LoadEndAck: %s" % ("never" if first_bd is None else "+%.2f s" % first_bd))
    if first_bd is None or first_bd > 1.0:
        print("FAIL  status block late or missing")
        ok = False
    else:
        print("ok    status block right after LoadEndAck")
    if late:
        print("FAIL  map.out: 'sc_data reply never arrived'")
        ok = False
    else:
        print("ok    no 'sc_data reply never arrived' in map.out")
    print("ALL PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
