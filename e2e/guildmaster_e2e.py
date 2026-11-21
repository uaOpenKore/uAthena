#!/usr/bin/env python3
"""e2e: a guild master who broke his guild must not keep master rights (sd->state.gmaster_flag pointed at the
freed guild: guild_broken cleared guild_id but not the flag, so every "is master" check still passed).

Setup (run_guildmaster.sh, local DB): guild 996 "BreakMe" = E2eTesterV alone (master), guild 997 "Target" =
E2eTesterA (master), notice "orig".
  1. V breaks 996 (0x15d).
  2. A invites V into 997 (0x168), V accepts (0x16b): V is a plain member of 997.
  3. V sends a guild notice change for 997 (0x16e, master only).
  4. A must NOT receive the changed notice (0x16f). (The char-server writes guild changes to SQL on a timer,
     so the test watches the packets, not the DB.)

Usage: python3 -I guildmaster_e2e.py <BornRok src/net/PacketTable.cpp>
"""
import os
import struct
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B", "-e"]
V = ("e2etestv", "e2epass1", 2000007)
A = ("e2etesta", "e2epass1", 2000006)


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, text=True).stdout.strip()


def enter(acc):
    s = rostub.Session(acc[0], acc[1])
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok", "map enter failed for %s" % acc[0]
    return s


class Client:
    def __init__(self, s, lengths):
        self.s, self.st, self.notices, self.belong = s, Stream(s.map_sock, lengths), [], []

    def run(self, seconds):
        for pid, p in self.st.packets(seconds):
            if pid == 0x91:
                self.s.map_sock.sendall(struct.pack("<H", 0x7D))
            elif pid == 0x16C:  # guild belong info: guild id, ..., is-master byte
                self.belong.append((struct.unpack_from("<I", p, 2)[0], p[14]))
            elif pid == 0x16F:
                self.notices.append((p[2:62].split(b"\0")[0].decode("latin-1"), p[62:182].split(b"\0")[0].decode("latin-1")))


def main():
    lengths = load_lengths(sys.argv[1])
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)

    sv, sa = enter(V), enter(A)
    v, a = Client(sv, lengths), Client(sa, lengths)
    both = lambda t: [th.join() for th in [threading.Thread(target=c.run, args=(t,)) for c in (v, a)] if not th.start()]
    both(3)
    a.notices.clear()

    sv.map_sock.sendall(struct.pack("<H", 0x15D) + rostub._fixed("BreakMe", 40))  # break the guild
    both(3)
    check("V's guild 996 is broken", sql("SELECT COUNT(*) FROM guild WHERE guild_id=996") == "0",
          sql("SELECT COUNT(*) FROM guild WHERE guild_id=996"))

    sa.map_sock.sendall(struct.pack("<HIII", 0x168, V[2], A[2], 150003))  # A invites V
    both(2)
    sv.map_sock.sendall(struct.pack("<HIi", 0x16B, 997, 1))                 # V accepts
    both(3)
    joined = [b for b in v.belong if b[0] == 997]
    check("V joined guild 997 as a plain member (0x16c for 997)", bool(joined), str(v.belong))

    a.notices.clear()
    sv.map_sock.sendall(struct.pack("<HI", 0x16E, 997) + rostub._fixed("hacked subject", 60) + rostub._fixed("hacked body", 120))
    both(3)
    hacked = [n for n in a.notices if "hacked" in n[0] or "hacked" in n[1]]
    check("a plain member cannot change the guild notice (A got no changed notice)", not hacked, str(hacked))
    sv.quit_game()
    sa.quit_game()
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
