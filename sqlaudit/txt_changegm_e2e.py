#!/usr/bin/env python3
"""e2e (TXT): @changegm to "Alex" must make Alex the guild master, not "Alexander" who joined earlier
(the TXT char-server matched member names by prefix, as the SQL one did).

txtgmuser (account 2000002 = GM 99 in conf/GM_account.txt) creates a guild, "Alexander" and then "Alex" join, @changegm Alex,
everyone logs out, the stand stops (save/guild.txt written) and the guild's master and first member are read.

Usage: python3 -I txt_changegm_e2e.py <txt run dir>   (c1 TXT stand, allowed_regs raised)
"""
import os
import struct
import subprocess
import sys
import time

C1 = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e"
sys.path.insert(0, C1)
from e2elib import Stream, chat, ensure_account, enter_map, load_lengths  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def join(gm, sgm, member, smember):
    gm.map_sock.sendall(struct.pack("<HIII", 0x168, member.aid, gm.aid, gm.cid))
    gid = None
    for pid, p in smember.packets(5):
        if pid == 0x16A:
            gid = struct.unpack_from("<I", p, 2)[0]
            break
    member.map_sock.sendall(struct.pack("<HII", 0x16B, gid or 0, 1))
    smember.collect(2)
    sgm.collect(1)
    return gid


def main():
    run = sys.argv[1]
    lengths = load_lengths()
    for user in ("txtgmuser", "txtalexander", "txtalex"):  # the first new account is 2000002 = GM 99 (GM_account.txt)
        print("account %s: %s" % (user, ensure_account(user, "txtpw123")))
    # The TXT login-server drops GM_account.txt entries of accounts that don't exist when it reads the file:
    # restart the stand now that 2000002 exists.
    subprocess.run([os.path.join(C1, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
    subprocess.run([os.path.join(C1, "srv.sh"), "start", run], stdout=subprocess.DEVNULL)
    gm = enter_map("txtgmuser", "txtpw123", "TxtGuildGM")
    sgm = Stream(gm.map_sock, lengths)
    sgm.collect(2)
    chat(gm.map_sock, "TxtGuildGM", "@guild TxtPrefix")
    sgm.collect(3)
    a = enter_map("txtalexander", "txtpw123", "Alexander")
    sa = Stream(a.map_sock, lengths)
    sa.collect(1)
    b = enter_map("txtalex", "txtpw123", "Alex")
    sb = Stream(b.map_sock, lengths)
    sb.collect(1)
    gid = join(gm, sgm, a, sa)
    join(gm, sgm, b, sb)
    print("guild id", gid)
    gm_name = None
    chat(gm.map_sock, "TxtGuildGM", "@changegm Alex")
    sgm.collect(3)
    for s in (a, b, gm):
        s.quit_game(wait=1)
    time.sleep(2)
    subprocess.run([os.path.join(C1, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
    line = ""
    for ln in open(os.path.join(run, "save", "guild.txt"), encoding="latin-1"):
        if "\tTxtPrefix\t" in ln:
            line = ln.rstrip("\n")
    print("guild line:", line[:400])
    fields = line.split("\t")
    master = fields[2] if len(fields) > 2 else None
    names = [f for f in fields[3:] if f in ("TxtGuildGM", "Alexander", "Alex")]  # member names, master field excluded
    gm_name = names[0] if names else None
    check("the guild's master is Alex", master == "Alex", master)
    check("the first member (the real master) is Alex", gm_name == "Alex", names)
    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
