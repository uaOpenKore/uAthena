#!/usr/bin/env python3
"""e2e (SQL): the password-failure auto-ban must ban the one IP, not its whole /24 (S. 2026-11-19:
"нужно банить только ИП а не подсеть").

7 wrong passwords from 127.0.0.1 within 5 minutes trigger the ban (dynamic_pass_failure_ban, limit 7).
Then 127.0.0.1 must be refused, and 127.0.0.2 (same /24, any 127.x address reaches the loopback) must
still log in. Run with ipban + dynamic_pass_failure_ban on (see run_ipban.sh).

Usage: python3 -I ipban_e2e.py <run dir>   (account user8/heavypw8 in the audit DB)
"""
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def login_from(src, user, pw):
    """0x64 login from source address `src`; returns 'ok' or the refusal."""
    s = socket.create_connection(("127.0.0.1", rostub.LOGIN_PORT), timeout=10, source_address=(src, 0))
    try:
        s.sendall(struct.pack("<HI", 0x64, 20) + rostub._fixed(user, 24) + rostub._fixed(pw, 24) + b"\0")
        dl = time.time() + 10
        cmd = struct.unpack("<H", rostub._recv_exact(s, 2, dl))[0]
        if cmd == 0x69:
            return "ok"
        if cmd == 0x6A:
            return "refused code=%d" % rostub._recv_exact(s, 21, dl)[0]
        if cmd == 0x81:
            return "refused 0x81 code=%d" % rostub._recv_exact(s, 1, dl)[0]
        return "unexpected 0x%04x" % cmd
    finally:
        s.close()


def main():
    sql("DELETE FROM ipbanlist")
    sql("DELETE FROM loginlog WHERE ip IN (2130706433, 2130706434)")  # 127.0.0.1 / 127.0.0.2
    sql("UPDATE login SET user_pass='heavypw8' WHERE userid='user8'")
    for i in range(7):
        login_from("127.0.0.1", "user8", "wrongpw%d" % i)
    time.sleep(1)
    bans = sql("SELECT list FROM ipbanlist").splitlines()
    check("the 7th wrong password bans exactly 127.0.0.1", bans == ["127.0.0.1"], bans)
    res1 = login_from("127.0.0.1", "user8", "heavypw8")
    check("127.0.0.1 is refused while banned", res1.startswith("refused"), res1)
    res2 = login_from("127.0.0.2", "user8", "heavypw8")
    check("127.0.0.2 (same /24) still logs in", res2 == "ok", res2)
    sql("DELETE FROM ipbanlist")
    sql("DELETE FROM loginlog WHERE ip IN (2130706433, 2130706434)")
    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
