#!/usr/bin/env python3
"""e2e (SQL): a guild expulsion reason of 40 raw bytes (no NUL) must not overflow the char-server's 80-byte
escape buffer on the guild save, and must be stored (cut to 39 characters).

Talks to the char-server as a map-server would (0x2af8 login with the s1/p1 inter-server account, then the
0x3034 guild leave that intif_guild_leave sends), so the map-server's own checks don't get in the way.
The guild and its two members are written straight into the audit DB before the char-server starts.

Usage: python3 -I expel_direct_e2e.py <run dir> setup|test
  setup: DB rows (run BEFORE srv.sh start); test: send the expulsion, stop the stand, check.
"""
import os
import socket
import struct
import subprocess
import sys
import time

SP = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit"
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
GID = 999
A_ACC, A_CID, B_ACC, B_CID = 2000001, 150001, 2000002, 150002   # synthetic chars Char1 / Char2


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def setup():
    for t in ("guild", "guild_member", "guild_position", "guild_expulsion", "guild_skill", "guild_alliance"):
        sql("DELETE FROM %s WHERE guild_id=%d" % (t, GID))
    sql("INSERT INTO guild (guild_id, name, char_id, master, guild_lv, connect_member, max_member, average_lv, "
        "exp, next_exp, skill_point, mes1, mes2, emblem_len, emblem_id) VALUES "
        "(%d, 'ExpelDirect', %d, 'Char1', 1, 0, 16, 10, 0, 100, 0, '', '', 0, 0)" % (GID, A_CID))
    for acc, cid, pos, name in ((A_ACC, A_CID, 0, "Char1"), (B_ACC, B_CID, 1, "Char2")):
        sql("INSERT INTO guild_member (guild_id, account_id, char_id, hair, hair_color, gender, class, lv, exp, "
            "exp_payper, online, position, rsv1, rsv2, name) VALUES (%d, %d, %d, 1, 1, 0, 1, 10, 0, 0, 0, %d, 0, 0, "
            "'%s')" % (GID, acc, cid, pos, name))
        sql("UPDATE `char` SET guild_id=%d WHERE char_id=%d" % (GID, cid))
    for pos in range(20):
        sql("INSERT INTO guild_position (guild_id, position, name, mode, exp_mode) VALUES (%d, %d, 'P%d', %d, 0)"
            % (GID, pos, pos, 0x11 if pos == 0 else 0))
    print("setup done")


def recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        d = s.recv(n - len(buf))
        if not d:
            raise ConnectionError("closed")
        buf += d
    return buf


def test(run):
    s = socket.create_connection(("127.0.0.1", 16121), timeout=10)
    s.sendall(struct.pack("<H", 0x2AF8) + b"s1".ljust(24, b"\0") + b"p1".ljust(24, b"\0")
              + struct.pack("<I", 0) + socket.inet_aton("127.0.0.1") + struct.pack(">H", 15999))
    cmd, res = struct.unpack("<HB", recv_exact(s, 3))
    ok = cmd == 0x2AF9 and res == 0
    print("%s  fake map-server accepted by the char-server" % ("ok  " if ok else "FAIL"))
    s.sendall(struct.pack("<HIIIB", 0x3034, GID, B_ACC, B_CID, 1) + b"'" * 40)
    time.sleep(2)
    s.close()
    time.sleep(1)
    subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
    out = open(os.path.join(run, "char.out"), encoding="latin-1").read()
    clean = "stack smashing" not in out and out.rstrip().endswith("No memory leaks found.")
    print("%s  char-server saves the guild on shutdown without overflowing%s" % (
        "ok  " if clean else "FAIL", "" if clean else "  [%s]" % out.strip().splitlines()[-1]))
    errors = [ln for ln in out.splitlines() if "guild_expulsion" in ln or "Data too long" in ln]
    mes = sql("SELECT mes FROM guild_expulsion WHERE guild_id=%d" % GID)
    good = mes == "'" * 39
    print("%s  the expulsion reason is stored as 39 quotes%s" % ("ok  " if good else "FAIL",
          "" if good else "  [%r; %s]" % (mes, errors[-1][:160] if errors else "no SQL error")))
    print("ALL PASSED" if ok and clean and good else "FAILED")
    sys.exit(0 if ok and clean and good else 1)


if __name__ == "__main__":
    if sys.argv[2] == "setup":
        setup()
    else:
        test(sys.argv[1])
