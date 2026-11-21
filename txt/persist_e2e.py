#!/usr/bin/env python3
"""e2e: quest log, achievements, hired mercenary and guild-storage unlock on the TXT stack.

Drives one character through logins, logouts and char-server restarts and checks what the map-server
reports back (@quests / @achievements / @merc chat output) and what lands in the TXT save files.
Run after login_e2e.py (it creates the account c1quser = 2000002, GM 99 in conf/GM_account.txt, and its
character). Restarts the whole stand first so the login-server reads the GM level.

Usage: python3 -I persist_e2e.py <run dir>
"""
import os
import re
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths, messages, read_out, whisper  # noqa: E402

USER, PW, NAME = "c1quser", "c1qpass1", "C1Quester"
LENGTHS = load_lengths()
RUN = None
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, ("  [%s]" % detail) if detail and not ok else ""))
    return ok


STOPCHAR = [0]


def srv(cmd):
    if cmd == "stopchar":
        STOPCHAR[0] += 1
    r = subprocess.run([os.path.join(HERE, "srv.sh"), cmd, RUN], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=300)
    print("  srv %s: %s" % (cmd, r.stdout.strip().replace("\n", " | ")))
    if r.returncode != 0:
        raise RuntimeError("srv.sh %s failed" % cmd)


def save_file(name):
    try:
        return open(os.path.join(RUN, "save", name), encoding="latin-1").read()
    except FileNotFoundError:
        return None


def show_files(*names):
    for n in names:
        txt = save_file(n)
        print("  --- save/%s ---" % n)
        for ln in (txt or "(missing)\n").splitlines():
            print("  | " + ln)


class Game:
    def __init__(self, label):
        print("[%s] login" % label)
        self.s = enter_map(USER, PW, NAME)
        self.st = Stream(self.s.map_sock, LENGTHS)
        self.login_pkts = self.st.collect(4.5)   # the post-login burst (initial status is deferred ~3 s on TXT)
        self.login_msgs = messages(self.login_pkts)
        for m in self.login_msgs:
            print("    login msg: " + m)

    def cmd(self, text, wait=1.5):
        return self.cmd_pkts(text, wait)[0]

    def cmd_pkts(self, text, wait=1.5):
        chat(self.s.map_sock, NAME, text)
        pkts = self.st.collect(wait)
        out = messages(pkts)
        for m in out:
            print("    %s> %s" % (text, m))
        print("    %s> packets: %s" % (text, " ".join("%04x" % i for i in sorted({pid for pid, _ in pkts}))))
        return out, {pid for pid, _ in pkts}

    def npc(self, text, wait=1.5):
        whisper(self.s.map_sock, "npc:C1Test", text)
        out = messages(self.st.collect(wait))
        for m in out:
            print("    npc %s> %s" % (text, m))
        return out

    def quit(self):
        self.s.quit_game(wait=2)
        time.sleep(2)   # final save (0x2b01 + quest/achievement/mercenary saves) reaches the char-server


def has(lines, pattern):
    return any(re.search(pattern, ln) for ln in lines)


def login_retry(user, pw, seconds=30):
    """The login-server refuses an account it still holds online (code 3) for a few seconds after a logout."""
    end = time.time() + seconds
    while True:
        s = rostub.Session(user, pw)
        try:
            s.login()
            return s
        except RuntimeError as e:
            if time.time() >= end or "code=3" not in str(e):
                raise
            time.sleep(2)


def delete_char(cid):
    """Delete a character on the char-server (0x68 <char_id>.L <email>.40B -> 0x6f ok / 0x70 refused)."""
    s = login_retry(USER, PW)
    _, res = s.char_enter()
    sock = s.char_sock
    sock.sendall(struct.pack("<HI", 0x68, cid) + rostub._fixed("a@a.com", 40))
    cmd = struct.unpack("<H", rostub._recv_exact(sock, 2, time.time() + 10))[0]
    sock.close()
    return cmd


def char_id_of_test_char():
    s = login_retry(USER, PW)
    _, res = s.char_enter()
    s.char_sock.close()
    return res[1][0][1] if res[0] == "list" and res[1] else None


def main():
    global RUN
    RUN = sys.argv[1]
    srv("stop")
    srv("start")
    map_start = len(read_out(RUN, "map"))
    cid = char_id_of_test_char()
    print("test character id: %s" % cid)

    # ---------------------------------------------------------------- session A: create everything
    g = Game("A")
    out = g.npc("setquest#2150")
    check("A: setquest 2150 -> active", has(out, r"setquest 2150 -> 1$"), out)
    out = g.npc("setquest#1015") + g.npc("completequest#1015")
    check("A: quest 1015 completed", has(out, r"completequest 1015 -> 2$"), out)
    check("A: achievement 'First Steps' unlocked by it", has(out, r"Achievement unlocked: First Steps"), out)
    out = g.npc("merc#6017#600000", wait=2.5) + g.cmd("@merc")
    check("A: mercenary Mina hired", has(out, r"--- Mercenary: Mina"), out)
    g.cmd("@guild C1Guild", wait=2.5)
    _, ids = g.cmd_pkts("@gstorage", wait=2.5)
    check("A: guild storage opened (0x00f2 amount packet)", 0xF2 in ids, ids)
    g.cmd("@quests")
    g.cmd("@achievements")
    g.quit()   # the guild storage is still open: logout sends 0x301a (unlock)
    out = read_out(RUN, "char")
    check("A: char-server kept the map-server link (no Unknown packet)", "Unknown packet" not in out)

    # ---------------------------------------------------------------- session B: same char-server
    g = Game("B")
    q = g.cmd("@quests")
    check("B: quest 2150 active after relog", has(q, r'2150 "Attitude to the New" - active'), q)
    check("B: quest 1015 complete after relog", has(q, r'1015 "Your first quest" - complete'), q)
    a = g.cmd("@achievements")
    check("B: achievement 40 First Steps DONE after relog", has(a, r"\[40\] First Steps - DONE"), a)
    check("B: no second reward at login", not has(g.login_msgs, r"Achievement unlocked"), g.login_msgs)
    m = g.cmd("@merc")
    check("B: mercenary Mina back after relog", has(m, r"--- Mercenary: Mina"), m)
    check("B: mercenary calls = 1", has(m, r"Calls: 1$"), m)
    g.quit()

    # ---------------------------------------------------------------- char-server restart: files
    srv("stopchar")
    show_files("quest.txt", "achievement.txt", "mercenary.txt", "mercenary_owner.txt")
    qf, af, mf, of = (save_file(n) or "" for n in ("quest.txt", "achievement.txt", "mercenary.txt", "mercenary_owner.txt"))
    check("files: quest.txt has 2150 active", re.search(r"^%d,2150,1,0,0,0,0$" % cid, qf, re.M), qf)
    check("files: quest.txt has 1015 complete", re.search(r"^%d,1015,2,0,0,0,0$" % cid, qf, re.M), qf)
    check("files: achievement.txt has 40 completed+rewarded", re.search(r"^%d,40,1,[1-9]\d*,1$" % cid, af, re.M), af)
    check("files: mercenary.txt has merc 1 (class 6017) of the char", re.search(r"^1,%d,6017,\d+,\d+,0,[1-9]\d*$" % cid, mf, re.M), mf)
    check("files: mercenary.txt next id 2", re.search(r"^2\t%newid%$", mf, re.M), mf)
    check("files: mercenary_owner.txt mer_id 1, archer calls 1", re.search(r"^%d,1,1,0,0,0,0,0$" % cid, of, re.M), of)
    ath = save_file("athena.txt") or ""
    check("files: athena.txt still written (char + newid)", NAME in ath and "%newid%" in ath)

    # quest counts round trip: give 2150 a count through the file
    qpath = os.path.join(RUN, "save", "quest.txt")
    open(qpath, "w", encoding="latin-1").write(re.sub(r"^(%d,2150,1,0),0," % cid, r"\g<1>,7,", qf, flags=re.M))
    srv("startchar")

    # ---------------------------------------------------------------- session C: after the restart
    g = Game("C")
    q = g.cmd("@quests")
    check("C: quest 2150 loaded from the file with count 7", has(q, r'2150 "Attitude to the New" - active \| .* 7/30'), q)
    check("C: quest 1015 complete after restart", has(q, r'1015 "Your first quest" - complete'), q)
    a = g.cmd("@achievements")
    check("C: achievement 40 DONE after restart", has(a, r"\[40\] First Steps - DONE"), a)
    check("C: no second reward at login", not has(g.login_msgs, r"Achievement unlocked"), g.login_msgs)
    m = g.cmd("@merc")
    check("C: mercenary Mina back after char-server restart", has(m, r"--- Mercenary: Mina"), m)
    out = g.npc("setquest#2151")
    check("C: setquest 2151", has(out, r"setquest 2151 -> 1$"), out)
    out = g.cmd("@merc reset", wait=2.0)
    check("C: @merc reset", has(out, r"Mercenary removed"), out)
    out = g.npc("merc#6037#600000", wait=2.5) + g.cmd("@merc")
    check("C: new mercenary Rodin hired", has(out, r"--- Mercenary: Rodin"), out)
    g.quit()

    srv("stopchar")
    show_files("quest.txt", "mercenary.txt", "mercenary_owner.txt")
    qf, mf, of = (save_file(n) or "" for n in ("quest.txt", "mercenary.txt", "mercenary_owner.txt"))
    check("files: quest 2150 kept count 7 through load+save", re.search(r"^%d,2150,1,0,7,0,0$" % cid, qf, re.M), qf)
    check("files: quest 2151 added", re.search(r"^%d,2151,1,0,0,0,0$" % cid, qf, re.M), qf)
    check("files: merc 1 deleted", not re.search(r"^1,", mf, re.M), mf)
    check("files: merc 2 (class 6037) created with the next id", re.search(r"^2,%d,6037," % cid, mf, re.M), mf)
    check("files: mercenary.txt next id 3", re.search(r"^3\t%newid%$", mf, re.M), mf)
    check("files: owner row mer_id 2, archer calls/faith 1/1, sword calls 1",
          re.search(r"^%d,2,1,1,0,0,1,0$" % cid, of, re.M), of)
    srv("startchar")

    # ---------------------------------------------------------------- session D + character deletion
    g = Game("D")
    m = g.cmd("@merc")
    check("D: mercenary Rodin back after restart", has(m, r"--- Mercenary: Rodin"), m)
    g.quit()
    time.sleep(1)
    r = delete_char(cid)
    check("char deletion accepted (0x6f)", r == 0x6F, "reply 0x%04x" % r)
    srv("stopchar")
    show_files("quest.txt", "achievement.txt", "mercenary.txt", "mercenary_owner.txt")
    for n in ("quest.txt", "achievement.txt", "mercenary_owner.txt"):
        txt = save_file(n) or ""
        check("deletion: no rows of %d left in %s" % (cid, n), not re.search(r"^%d," % cid, txt, re.M), txt)
    mf = save_file("mercenary.txt") or ""
    check("deletion: no mercenary of %d left, next id kept (3)" % cid,
          not re.search(r"^\d+,%d," % cid, mf, re.M) and re.search(r"^3\t%newid%$", mf, re.M), mf)
    ath = save_file("athena.txt") or ""
    check("deletion: athena.txt written without the character", NAME not in ath and "%newid%" in ath)
    srv("startchar")

    out = read_out(RUN, "char")
    bad = [ln for ln in out.splitlines() if "Unknown packet" in ln or "disconnecting" in ln]
    check("whole run: no 'Unknown packet'/'disconnecting' in char.out", not bad, bad[:5])
    lost = read_out(RUN, "map")[map_start:].count("Map Server disconnected from Char Server")
    check("whole run: the map-server lost the char-server only at the %d deliberate restarts" % STOPCHAR[0],
          lost == STOPCHAR[0], "%d disconnects" % lost)

    fails = [n for n, ok in RESULTS if not ok]
    print("ALL PASSED (%d checks)" % len(RESULTS) if not fails else "%d CHECK(S) FAILED: %s" % (len(fails), fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
