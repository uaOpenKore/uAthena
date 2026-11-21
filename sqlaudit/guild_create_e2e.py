#!/usr/bin/env python3
"""e2e (SQL): a new guild must keep its master's rights after the servers restart.

The char-server set the default positions (master = invite + expel) only in memory and never wrote them,
nor the master's member row, at creation. After the nightly restart the guild loaded with all positions
at mode 0, so the master could neither invite nor expel.

Steps: SqlInj2 (GM) creates a guild with @guild; the DB must hold its 20 positions (master mode 0x11) and
the master's member row right away; then the stand restarts and the master invites SqlInj1, who must
receive the invitation (0x16a).

Usage: python3 -I guild_create_e2e.py <run dir>   (stand from mkrun.sh/srv.sh, accounts from login_sql_e2e)
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit")
from e2elib import Stream, chat, enter_map, load_lengths  # noqa: E402
import names_e2e as N  # noqa: E402  (sql, cleanup)

SP = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit"
results = []


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def main():
    run = sys.argv[1]
    N.cleanup()
    lengths = load_lengths()
    a = enter_map("sqlinj2", "injpw2", "SqlInj2")
    sa = Stream(a.map_sock, lengths)
    sa.collect(1)
    chat(a.map_sock, "SqlInj2", "@guild FreshGuild")
    sa.collect(3)
    gid = N.sql("SELECT guild_id FROM guild WHERE name='FreshGuild'")
    check("the guild is created", gid.isdigit(), gid)
    gid = int(gid) if gid.isdigit() else 0
    npos = N.sql("SELECT COUNT(*) FROM guild_position WHERE guild_id=%d" % gid)
    mode0 = N.sql("SELECT mode FROM guild_position WHERE guild_id=%d AND position=0" % gid)
    check("its 20 positions are in the DB right after creation", npos == "20", npos)
    check("the master position has invite + expel (mode 17)", mode0 == "17", mode0)
    master = N.sql("SELECT position FROM guild_member WHERE guild_id=%d AND char_id=%d" % (gid, a.cid))
    check("the master's member row is in the DB right after creation", master == "0", repr(master))
    a.quit_game()

    subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
    subprocess.run([os.path.join(SP, "srv.sh"), "start", run], stdout=subprocess.DEVNULL)
    a = enter_map("sqlinj2", "injpw2", "SqlInj2")
    sa = Stream(a.map_sock, lengths)
    b = enter_map("sqlinj1", "injpw1", "SqlInj1")
    sb = Stream(b.map_sock, lengths)
    sa.collect(2)
    sb.collect(1)
    a.map_sock.sendall(struct.pack("<HIII", 0x168, b.aid, a.aid, a.cid))
    got = any(pid == 0x16A for pid, _ in sb.packets(5))
    check("after a restart the master can still invite", got)
    a.quit_game()
    b.quit_game()
    time.sleep(2)
    N.sql("DELETE FROM guild_position WHERE guild_id=%d" % gid)
    N.sql("DELETE FROM guild_member WHERE guild_id=%d" % gid)
    N.sql("DELETE FROM guild_skill WHERE guild_id=%d" % gid)
    N.sql("DELETE FROM guild WHERE guild_id=%d" % gid)
    N.sql("UPDATE `char` SET guild_id=0 WHERE name IN ('SqlInj1','SqlInj2')")
    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
