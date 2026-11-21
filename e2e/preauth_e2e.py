#!/usr/bin/env python3
"""e2e: a delayed close of a rejected pre-auth map connection must not close the next connection on the same fd
(audit item 2, S. 2026-11-20). clif_setwaitclose gives a connection without session_data 1 s to read its reject
and keyed that timer on the session POINTER; the fd and the socket_data block are reused by the next connection.
  C1 connects and asks for account id 1100000000 (an NPC already has it): 0x6a "rejected", delayed close in 1 s.
  C1 goes away at once; C2 connects right after it (same fd, same socket_data address) and waits 2 s before it
  logs in. The 1 s timer of C1 must not close C2.
Usage: python3 -I preauth_e2e.py [rounds, default 5]
"""
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def map_login_packet(aid, cid=1, lid1=0x1234567):
    pkt = (struct.pack("<H", 0x9B) + b"\x39\x33" + struct.pack("<I", aid) + b"\x65" + struct.pack("<I", cid)
           + b"\x37\x33\x36\x64" + struct.pack("<I", lid1) + struct.pack("<I", 0) + b"\x00")
    assert len(pkt) == 26
    return pkt


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for r in range(rounds):
        c1 = socket.create_connection((rostub.HOST, rostub.MAP_PORT), timeout=5)
        c1.sendall(map_login_packet(1100000000))
        try:
            reply = c1.recv(64)
        except OSError:
            reply = b""
        c1.close()
        t0 = time.time()
        c2 = socket.create_connection((rostub.HOST, rostub.MAP_PORT), timeout=5)
        c2.settimeout(0.2)
        closed_at = None
        while time.time() - t0 < 2.5:
            try:
                d = c2.recv(64)
                if not d:
                    closed_at = time.time() - t0
                    break
            except socket.timeout:
                continue
            except OSError:
                closed_at = time.time() - t0
                break
        c2.close()
        print("    round %d: C1 got %s, C2 %s" % (r, reply[:3].hex() or "nothing",
              "closed by the server after %.2f s" % closed_at if closed_at is not None else "still open after 2.5 s"),
              flush=True)
        check("round %d: C1's delayed close leaves C2 alone" % r, reply[:2] == b"\x6a\x00" and closed_at is None)
        time.sleep(1.5)  # let C1's timer pass before the next round
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
