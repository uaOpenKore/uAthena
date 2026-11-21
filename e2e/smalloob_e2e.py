#!/usr/bin/env python3
"""e2e: three small out-of-bounds accesses (audit item 12, S. 2026-11-20).
  away     @away with 128 chars (only scripts get that far: chat lines are cut at 70): strcpy into
           away_message[128] wrote its NUL into the next field, the «Натиск» streak (streak.target), so the
           next hit on the same mob started again at 100%
  disguise clif_skill_nodamage sent packet_len(0x115) = 35 bytes of a 15-byte 0x11a from buf[32] to a
           disguised GM: the client's packet stream lost its framing
  notice   GuildChangeNotice (0x16e) with msg2 "|xx|AAA..." up to the end of the packet: strnlen(msg2, 120)
           ran past the packet and the trailing-space cut wrote a NUL onto the first byte of the next packet
           in the same read (a whisper "ping" right behind it never got its "pong")
NPCs and GM: run_msgbuf.sh <run> smalloob [parts].
Usage: python3 -I smalloob_e2e.py <BornRok src/net/PacketTable.cpp> [away,disguise,notice]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths  # noqa: E402
from streak_e2e import Me, HUGELING  # noqa: E402

ENDURE = 8
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def whisper_pkt(text):
    msg = text.encode("latin-1") + b"\0"
    return struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:MsgTest", 24) + msg


class T:
    def __init__(self, lengths):
        self.s = rostub.Session(USER, PW)
        self.s.login()
        _, (kind, chars) = self.s.char_enter()
        self.s.select_char(chars[0][0])
        assert self.s.map_enter()[0] == "ok"
        self.st = Stream(self.s.map_sock, lengths)
        self.me = Me(self.st, self.s.map_sock, self.s.aid)
        self.guild_id = None
        note = self.me.note

        def note_guild(pid, p):  # 0x16c guild belong info: at login for a member, after @guild for a new master
            if pid == 0x16C:
                self.guild_id = struct.unpack_from("<I", p, 2)[0]
            note(pid, p)
        self.me.note = note_guild
        self.me.drain(2)
        for c in ("@job 1", "@lvup 98", "@allskill", "@str -300", "@dex -300", "@dex 60", "@luk -300",
                  "@vit -300", "@vit 80", "@agi -300", "@int -300", "@heal"):
            self.me.cmd(c)

    def said(self, seconds):
        out = []
        for pid, p in self.st.packets(seconds):
            self.me.note(pid, p)
            if pid in (0x8E, 0x17F):
                out.append(p[4:].split(b"\0")[0].decode("latin-1"))
        return out

    def whisper(self, text, wait=1.5):
        self.s.map_sock.sendall(whisper_pkt(text))
        return self.said(wait)

    def away(self):
        """4 hits, @away with 128 chars, the 5th hit must go on with the streak"""
        me = self.me
        (h,) = me.spawn(HUGELING, 1)
        first = [me.attack(h) for _ in range(4)]
        got = self.whisper("away")
        fifth = me.attack(h)
        self.whisper("awayoff")
        print("    hits %s, %s, 5th hit %s" % (first, [x for x in got if "away" in x.lower()], fifth), flush=True)
        check("@away with 128 chars leaves the streak alone (5th hit keeps growing)",
              None not in first and fifth is not None and fifth > first[-1], "hits %s then %s" % (first, fifth))

    def disguise(self):
        """a no-damage skill on a disguised GM must keep the stream framed; False when the stream broke"""
        me, s = self.me, self.s
        me.cmd("@disguise 1002", 1.5)
        framing, seen, pong = None, [], []
        try:
            s.map_sock.sendall(struct.pack("<H", 0x72) + b"\0" * 4 + struct.pack("<H", 10) + b"\0" * 2
                               + struct.pack("<H", ENDURE) + b"\0" * 9 + struct.pack("<I", s.aid))
            for pid, p in self.st.packets(3):
                me.note(pid, p)
                if pid == 0x11A:
                    seen.append((struct.unpack_from("<H", p, 2)[0], struct.unpack_from("<i", p, 6)[0]))
            me.cmd("@undisguise", 1.5)
            pong = [x for x in self.whisper("ping") if x == "pong"]
        except RuntimeError as e:  # Stream: "unknown packet ...: stream framing lost"
            framing = str(e)
        check("Endure on a disguised GM: 0x11a has its own length (stream stays framed)",
              framing is None and any(sk == ENDURE for sk, _ in seen) and bool(pong),
              framing or "0x11a %s" % seen)
        return framing is None

    def notice(self):
        """the guild master sends 0x16e with msg2 up to the packet end and a whisper right behind it"""
        me, s = self.me, self.s
        if self.guild_id is None:
            me.cmd("@guild OobNotice", 1)
            self.said(4)
        gid = self.guild_id
        print("    guild id %s" % gid, flush=True)
        msg1 = rostub._fixed("OOB test", 60)
        msg2 = b"|xx|" + b"A" * 116
        pkt = struct.pack("<HI", 0x16E, gid or 0) + msg1 + msg2
        assert len(msg2) == 120 and len(pkt) == 186
        s.map_sock.sendall(pkt + whisper_pkt("ping"))
        try:
            out = self.said(2.5)
        except (RuntimeError, ConnectionError, OSError) as e:
            out = ["<%s>" % e]
        check("0x16e with msg2 to the packet end leaves the next packet alone (the whisper behind it is answered)",
              gid is not None and "pong" in out, "guild %s, got %s" % (gid, out[:3]))


def main():
    lengths = load_lengths(sys.argv[1])
    parts = (sys.argv[2] if len(sys.argv) > 2 else "away,disguise,notice").split(",")
    t = T(lengths)
    alive = True
    if "away" in parts:
        t.away()
    if "disguise" in parts:
        alive = t.disguise()
    if "notice" in parts and alive:
        t.notice()
    if alive:
        try:
            t.s.quit_game()
        except Exception:
            pass
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
