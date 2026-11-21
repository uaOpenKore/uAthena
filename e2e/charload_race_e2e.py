#!/usr/bin/env python3
"""e2e: a character load still running for a closed char-select connection must not be answered on the NEW
connection of the same account (Linux hands the next connection the lowest free fd, i.e. usually the same one).

  1. Another DB connection holds LOCK TABLES inventory WRITE: the async load worker stops at its inventory query.
  2. S1 (testacc) selects slot 0 (0x66) and closes its char-server connection while the load is stuck.
  3. S2 (testacc again, new login ids) enters the char-server and stays on the character list.
  4. The lock is released: the load of S1 finishes.
  5. S2 must get NOTHING (old char-server: 0x71 with S1's character + an auth for S1's login ids).
  6. S2 selects slot 0 itself: it must get its 0x71 (the normal path still works).

Scenario "order" (python3 -I charload_race_e2e.py order): while S1's load is stuck, S1 also sends a char
creation (0x67). The old synchronous load answered packets in order; the async one must too: nothing may come
back while the load is stuck, and the 0x71 must come before the 0x6d of the new character.

Usage: python3 -I charload_race_e2e.py [order]
"""
import os
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok"]
USER, PW = "testacc", "testpass"


def read_for(sock, seconds):
    """Every packet id the char-server sends within `seconds` (0x71 is 28 bytes, the rest only matter as ids)."""
    sock.settimeout(0.3)
    buf, end = b"", time.time() + seconds
    while time.time() < end:
        try:
            d = sock.recv(65536)
        except socket.timeout:
            continue
        if not d:
            break
        buf += d
    ids = []
    while len(buf) >= 2:
        pid = struct.unpack_from("<H", buf)[0]
        ids.append(pid)
        if pid == 0x71:
            buf = buf[28:]
        else:
            break  # anything else: stop parsing, the id is enough
    return ids


def order():
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)

    name = "RaceOrd%d" % (int(time.time()) % 100000)
    subprocess.run(MYSQL + ["-e", "DELETE FROM `char` WHERE account_id=2000001 AND char_num=1"], check=False)
    # memo: read by the load (3rd query), not written by the char creation (char + inventory), so a stuck load
    # does not also stop the main thread
    lock = subprocess.Popen(MYSQL + ["-e", "LOCK TABLES memo WRITE; SELECT SLEEP(6); UNLOCK TABLES;"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1)
    s1 = rostub.Session(USER, PW)
    s1.login()
    _, (kind, chars) = s1.char_enter()
    assert kind == "list" and chars, "S1: no character list"
    make = (struct.pack("<H", 0x67) + rostub._fixed(name, 24) + bytes([5, 5, 5, 5, 5, 5, 1]) + struct.pack("<HH", 1, 1))
    s1.char_sock.sendall(struct.pack("<HB", 0x66, chars[0][0]) + make)
    early = read_for(s1.char_sock, 2.5)  # the load is stuck on the memo lock
    check("nothing comes back while the char-select load is stuck", early == [],
          "packets: %s" % ["0x%04x" % i for i in early])
    lock.wait(timeout=20)
    err = lock.stderr.read().decode(errors="replace").strip()
    if err:
        print("    lock connection: " + err, flush=True)
    later = read_for(s1.char_sock, 4)
    seq = early + later
    first = seq[0] if seq else None
    check("the 0x71 of the char select comes first (packets answered in order)", first == 0x71,
          "packets: %s" % ["0x%04x" % i for i in seq])
    s1.char_sock.close()
    cid = subprocess.run(MYSQL + ["-N", "-e", "SELECT char_id FROM `char` WHERE name='%s'" % name],
                         stdout=subprocess.PIPE, text=True).stdout.strip()
    if cid:
        subprocess.run(MYSQL + ["-e", "DELETE FROM inventory WHERE char_id=%s; DELETE FROM `char` WHERE char_id=%s"
                                % (cid, cid)], check=False)
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "order":
        return order()
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)

    lock = subprocess.Popen(MYSQL + ["-e", "LOCK TABLES inventory WRITE; SELECT SLEEP(10); UNLOCK TABLES;"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1)
    s1 = rostub.Session(USER, PW)
    s1.login()
    _, (kind, chars) = s1.char_enter()
    assert kind == "list" and chars, "S1: no character list"
    s1.char_sock.sendall(struct.pack("<HB", 0x66, chars[0][0]))
    time.sleep(1.5)  # the load is stuck on the inventory lock now
    s1.char_sock.close()
    s1.char_sock = None
    time.sleep(2)  # the char-server closes S1 and tells the login-server the account is offline

    s2 = rostub.Session(USER, PW)
    s2.login()
    _, (kind, chars2) = s2.char_enter()
    check("S2 (same account, new login) gets its character list", kind == "list" and bool(chars2), str(kind))
    print("    S1 login ids %08x/%08x, S2 login ids %08x/%08x" % (s1.lid1, s1.lid2, s2.lid1, s2.lid2), flush=True)
    lock.wait(timeout=20)  # SLEEP(10) ends: the lock is released, the stuck load of S1 finishes
    ids = read_for(s2.char_sock, 5)
    check("S2 gets nothing for the load S1 started (no 0x71 it did not ask for)", 0x71 not in ids,
          "packets: %s" % ["0x%04x" % i for i in ids])
    try:
        cid = s2.select_char(chars2[0][0], timeout=10)
        check("S2 selecting its character itself still works", bool(cid), "cid %s" % cid)
    except Exception as e:  # noqa: BLE001
        check("S2 selecting its character itself still works", False, str(e))
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
