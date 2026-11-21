#!/usr/bin/env python3
"""authguard_txt_e2e.py <run dir>: the account lock against password guessing on the TXT login-server
(S. 2026-11-21; the TXT server had no protection at all: no IP ban for wrong passwords).
 1 the owner logs in from 127.0.0.50; 9 wrong passwords from 9 other addresses: each "incorrect password"
 2 the 10th locks: the right password from a stranger's address is refused (code 6, "until <time>")
 3 the owner's address still gets in (trusted), and that clears the lock
 4 an unknown name gets code 1 like a wrong password
 5 the login log (log/login.log) has the tried password, never the real one
 6 the attack log has the lock line"""
import os, socket, struct, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rostub  # noqa: E402
from e2elib import ensure_account  # noqa: E402
run = sys.argv[1]
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def login_from(src, user, pw):
    s = socket.create_connection(("127.0.0.1", rostub.LOGIN_PORT), timeout=10, source_address=(src, 0))
    try:
        s.sendall(struct.pack("<HI", 0x64, 20) + rostub._fixed(user, 24) + rostub._fixed(pw, 24) + b"\0")
        dl = time.time() + 10
        cmd = struct.unpack("<H", rostub._recv_exact(s, 2, dl))[0]
        if cmd == 0x69:
            return "ok"
        if cmd == 0x6A:
            rest = rostub._recv_exact(s, 21, dl)
            return "refused code=%d %s" % (rest[0], rest[1:].split(b"\0")[0].decode("latin-1"))
        return "unexpected 0x%04x" % cmd
    finally:
        s.close()
def read(p):
    try: return open(os.path.join(run, p), errors="replace").read()
    except FileNotFoundError: return ""
USER, PW = "agtxtvic", "agtxtright7"
ensure_account(USER, PW)
time.sleep(1)
lg0, at0 = len(read("log/login.log")), len(read("log/attack-login.log"))
first = login_from("127.0.0.50", USER, PW)
r = [login_from("127.0.0.%d" % (11 + i), USER, "guess%d" % i) for i in range(9)]
check("1 the owner logged in; 9 wrong passwords from 9 addresses: each incorrect",
      first == "ok" and all(x.startswith("refused code=1") for x in r), "first=%r %r" % (first, r))
r10 = login_from("127.0.0.20", USER, "guess9")
stranger = login_from("127.0.0.21", USER, PW)
check("2 the 10th locks: a stranger with the right password is refused 'until <time>'",
      r10.startswith("refused code=1") and stranger.startswith("refused code=6 ") and len(stranger) > 20, "10th=%r stranger=%r" % (r10, stranger))
owner = login_from("127.0.0.50", USER, PW)
after = login_from("127.0.0.21", USER, PW)
check("3 the owner's address gets in, and that clears the lock", owner == "ok" and after == "ok", "owner=%r after=%r" % (owner, after))
unk = login_from("127.0.0.30", "nosuchtxt9q", "whatever1")
check("4 an unknown name gets code 1", unk.startswith("refused code=1"), unk)
lg = read("log/login.log")[lg0:]
check("5 the login log has the tried password, never the real one", PW not in lg and "guess0" in lg,
      [l for l in lg.splitlines() if USER in l][:3])
at = read("log/attack-login.log")[at0:]
check("6 the attack log has the lock", "acc='agtxtvic' bruteforce: 10 wrong password(s) from 10 address(es)" in at, at[-400:])
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
