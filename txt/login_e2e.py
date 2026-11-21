#!/usr/bin/env python3
"""RED/GREEN e2e: a character login on the TXT stack must complete.

Logs a character in (account + char auto-created on the first run) and checks that after LoadEndAck the
map-server sends the post-login burst (status 0x00b0, skill list 0x010f) and that char.out has no
"Unknown packet" / "disconnecting" line. On the unfixed TXT char-server the quest-log request 0x3060 sent
from pc_authok makes the char-server drop the map-server link, the registry reply is lost, state.auth
stays 0 and nothing follows LoadEndAck.

Usage: python3 -I login_e2e.py <run dir> [seconds to wait, default 8]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2elib import Stream, ensure_account, enter_map, load_lengths, read_out  # noqa: E402

USER, PW, NAME = "c1quser", "c1qpass1", "C1Quester"


def main():
    run = sys.argv[1]
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    lengths = load_lengths()
    print("account:", ensure_account(USER, PW))
    s = enter_map(USER, PW, NAME)
    st = Stream(s.map_sock, lengths)
    t0 = time.time()
    first = {}
    try:
        for pid, p in st.packets(wait):
            first.setdefault(pid, time.time() - t0)
    except ConnectionError as e:
        print("map connection closed: %s" % e)
    ids = sorted(first)
    print("after LoadEndAck: %d distinct packet ids in %.0f s: %s" % (len(ids), wait, " ".join("%04x" % i for i in ids)))
    for pid in (0xB0, 0x10F, 0xBD):
        print("  0x%04x %s" % (pid, ("at +%.2f s" % first[pid]) if pid in first else "NOT received"))
    try:
        s.quit_game()
    except OSError:
        pass
    time.sleep(1)
    out = read_out(run, "char")
    bad = [ln for ln in out.splitlines() if "Unknown packet" in ln or "disconnecting" in ln]
    for ln in bad[:10]:
        print("  char.out: " + ln.strip())
    checks = [
        ("status 0x00b0 after LoadEndAck", 0xB0 in first),
        ("skill list 0x010f after LoadEndAck", 0x10F in first),
        ("no 'Unknown packet'/'disconnecting' in char.out", not bad),
    ]
    fails = 0
    for name, ok in checks:
        print("%s  %s" % ("ok  " if ok else "FAIL", name))
        fails += not ok
    print("ALL PASSED" if not fails else "%d CHECK(S) FAILED" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
