#!/usr/bin/env python3
"""e2e (SQL): names and texts the client sends as fixed-size fields without a NUL must not overflow the
char-server's escape buffers (it is built with -fstack-protector, so an overflow aborts it).

Scenarios (one per run, the old char-server dies in each):
  party  - 0x1e8 party create with a 24-byte name of quotes
  guild  - 0x165 guild create with a 24-byte name of quotes
  expel  - 0x15b guild expulsion with a 40-byte reason of quotes, then the char-server's final guild save
  homun  - 0x231 homunculus rename to 24 quotes, then an autosave

Usage: python3 -I names_e2e.py <run dir> <scenario>
  accounts sqlinj2 (GM 99, char SqlInj2) and sqlinj1 (char SqlInj1) from login_sql_e2e.py.
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
from e2elib import Stream, chat, enter_map, load_lengths  # noqa: E402

SP = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit"
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def char_alive(run):
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if os.readlink("/proc/%s/cwd" % pid) == run and \
                    open("/proc/%s/cmdline" % pid, "rb").read().startswith(b"./char-server_sql"):
                return True
        except OSError:
            continue
    return False


def char_out(run):
    return open(os.path.join(run, "char.out"), encoding="latin-1").read()


def cleanup():
    gids = sql("SELECT guild_id FROM guild WHERE name LIKE '\\'%' OR name='ExpelTest'").split()
    for g in gids:
        for t in ("guild", "guild_member", "guild_position", "guild_skill", "guild_expulsion", "guild_alliance"):
            sql("DELETE FROM %s WHERE guild_id=%s" % (t, g))
    sql("DELETE FROM party WHERE name LIKE '\\'%'")
    sql("UPDATE `char` SET party_id=0, guild_id=0, homun_id=0 WHERE name IN ('SqlInj1','SqlInj2')")
    sql("DELETE FROM homunculus WHERE char_id IN (SELECT char_id FROM `char` WHERE name='SqlInj2')")


def main():
    run, scen = sys.argv[1], sys.argv[2]
    cleanup()
    lengths = load_lengths()
    a = enter_map("sqlinj2", "injpw2", "SqlInj2")
    sa = Stream(a.map_sock, lengths)
    sa.collect(1)
    chat(a.map_sock, "SqlInj2", "@allskill")
    sa.collect(1)

    if scen == "party":
        a.map_sock.sendall(struct.pack("<H", 0x1E8) + b"'" * 24 + bytes([1, 1]))
        sa.collect(3)
        check("char-server survives a 24-quote party name", char_alive(run))
        name = sql("SELECT name FROM party WHERE name LIKE '\\'%'")
        check("the party is stored as 23 quotes", name == "'" * 23, repr(name))

    elif scen == "guild":
        chat(a.map_sock, "SqlInj2", "@item 714 1")
        sa.collect(1)
        a.map_sock.sendall(struct.pack("<HI", 0x165, a.aid) + b"'" * 24)
        sa.collect(3)
        check("char-server survives a 24-quote guild name", char_alive(run))
        name = sql("SELECT name FROM guild WHERE name LIKE '\\'%'")
        check("the guild is stored as 23 quotes", name == "'" * 23, repr(name))

    elif scen == "expel":
        chat(a.map_sock, "SqlInj2", "@guild ExpelTest")
        sa.collect(3)
        b = enter_map("sqlinj1", "injpw1", "SqlInj1")
        sb = Stream(b.map_sock, lengths)
        sb.collect(1)
        a.map_sock.sendall(struct.pack("<HIII", 0x168, b.aid, a.aid, a.cid))
        gid = None
        for pid, p in sb.packets(5):
            if pid == 0x16A:
                gid = struct.unpack_from("<I", p, 2)[0]
                break
        check("the invitee gets the guild invitation", gid is not None)
        b.map_sock.sendall(struct.pack("<HII", 0x16B, gid or 0, 1))
        sb.collect(2)
        sa.collect(1)
        a.map_sock.sendall(struct.pack("<HIII", 0x15B, gid or 0, b.aid, b.cid) + b"'" * 40)
        sa.collect(3)
        b.kill_map()
        a.quit_game()
        time.sleep(2)
        subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
        out = char_out(run)
        check("char-server saves the guild on shutdown without overflowing",
              "stack smashing" not in out and out.rstrip().endswith("No memory leaks found."),
              out.strip().splitlines()[-1] if out.strip() else "")
        mes = sql("SELECT mes FROM guild_expulsion WHERE guild_id=%d" % (gid or 0))
        check("the expulsion reason is stored as 39 quotes", mes == "'" * 39, repr(mes))
        cleanup()
        print("ALL PASSED" if all(results) else "FAILED")
        sys.exit(0 if all(results) else 1)

    elif scen == "homun":
        chat(a.map_sock, "SqlInj2", "@makehomun 6001")
        sa.collect(3)
        a.map_sock.sendall(struct.pack("<H", 0x231) + b"'" * 24)
        sa.collect(3)
        sa.collect(5)
        a.quit_game(wait=4)  # the logout save writes the homunculus
        check("char-server survives saving a 24-quote homunculus name", char_alive(run))
        name = sql("SELECT name FROM homunculus WHERE char_id=(SELECT char_id FROM `char` WHERE name='SqlInj2') "
                   "ORDER BY homun_id DESC LIMIT 1")
        check("the homunculus is stored as 23 quotes", name == "'" * 23, repr(name))

    try:
        a.quit_game()
    except Exception:  # noqa: BLE001
        pass
    time.sleep(2)
    cleanup()
    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
