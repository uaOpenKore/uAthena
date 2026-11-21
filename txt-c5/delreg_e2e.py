#!/usr/bin/env python3
"""e2e (TXT): deleting a character must not hand its character variables to another character.

Deleting a character from the character select (0x68) moves the LAST entry of the char-server's table
into the freed slot. The TXT char-server copied only the status part (sizeof(struct mmo_charstatus)),
not the character's variables (struct character_data), so the moved character kept the DELETED one's
variables. The test makes two characters on one account, writes each its own char variable
(DELREG_CID = its char id) into save/athena.txt while the char-server is stopped, deletes the first
character and checks what the second one carries after the char-server saves again.

Usage: python3 -I delreg_e2e.py <run dir>   (c1 e2e helpers, stand on ports 16900/16121/15121)
"""
import os
import re
import struct
import subprocess
import sys
import time

C1 = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e"
sys.path.insert(0, C1)
import rostub  # noqa: E402
from e2elib import ensure_account  # noqa: E402

USER, PW = "c5del", "c5delpw1"
NAMES = ("DelRegA", "DelRegB")


def srv(cmd, run):
    r = subprocess.run([os.path.join(C1, "srv.sh"), cmd, run], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, timeout=300)
    print("  srv %s: %s" % (cmd, r.stdout.strip().replace("\n", " | ")))


def login(user, pw, seconds=40):
    end = time.time() + seconds
    while True:  # the login-server refuses an account it still holds online (code 3) right after a logout
        s = rostub.Session(user, pw)
        try:
            s.login()
            return s
        except RuntimeError as e:
            if time.time() >= end or "code=3" not in str(e):
                raise
            time.sleep(2)


def athena_path(run):
    return os.path.join(run, "save", "athena.txt")


def line_of(text, name):
    return [ln for ln in text.splitlines() if "\t%s\t" % name in ln]


def main():
    run = sys.argv[1]
    print("account:", ensure_account(USER, PW))
    s = login(USER, PW)
    _, res = s.char_enter()
    assert res[0] == "list", res
    if res[1]:
        print("FAIL  the test account already has characters - use a fresh run dir")
        sys.exit(1)
    cid_a = s.make_char(NAMES[0], slot=0)
    cid_b = s.make_char(NAMES[1], slot=1)
    s.char_sock.close()
    print("  made %s=%d (slot 0), %s=%d (slot 1)" % (NAMES[0], cid_a, NAMES[1], cid_b))

    # Give each character its own char variable, straight in the save file (registry field = the last
    # tab-separated field of a character line: "name,value " pairs).
    srv("stopchar", run)
    lines = open(athena_path(run), encoding="latin-1").read().splitlines()
    out = []
    for ln in lines:
        for name, cid in ((NAMES[0], cid_a), (NAMES[1], cid_b)):
            if "\t%s\t" % name in ln:
                assert ln.endswith("\t"), "unexpected line end: %r" % ln[-20:]
                ln = ln[:-1] + "DELREG_CID,%d \t" % cid
        out.append(ln)
    with open(athena_path(run), "w", encoding="latin-1") as f:
        f.write("\n".join(out) + "\n")
    srv("startchar", run)

    s = login(USER, PW)
    _, res = s.char_enter()
    s.char_sock.sendall(struct.pack("<HI", 0x68, cid_a) + rostub._fixed("a@a.com", 40))
    reply = struct.unpack("<H", rostub._recv_exact(s.char_sock, 2, time.time() + 10))[0]
    s.char_sock.close()
    print("  delete %s -> 0x%04x" % (NAMES[0], reply))

    srv("stopchar", run)  # SIGINT: the char-server writes save/athena.txt
    athena = open(athena_path(run), encoding="latin-1").read()
    line_a, line_b = line_of(athena, NAMES[0]), line_of(athena, NAMES[1])
    vals = re.findall(r"DELREG_CID,(\d+)", line_b[0]) if line_b else []
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""))
        ok = ok and cond

    check("delete accepted (0x6f)", reply == 0x6F, "0x%04x" % reply)
    check("%s gone from athena.txt" % NAMES[0], not line_a)
    check("%s still in athena.txt" % NAMES[1], bool(line_b))
    check("%s keeps its own DELREG_CID=%d" % (NAMES[1], cid_b), vals == [str(cid_b)], "found %s" % vals)
    srv("startchar", run)
    print("ALL PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
