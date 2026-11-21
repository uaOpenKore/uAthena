#!/usr/bin/env python3
"""e2e check of the element mark (uAthena [elemark]) on a local stand.

A GM Mage spawns a Hugeling (1284: Water 1, 5000 HP, MDEF 0) and casts level-1 bolts at it:
  phase A  N rounds of  Fire Bolt (50%, marks) -> Lightning Bolt (175% boosted to 350%) -> Lightning Bolt (normal)
  phase B  1 round of   Fire Bolt (marks) -> Fire Bolt (uses the mark, must NOT re-mark) -> Lightning Bolt (normal)
  phase C  element_mark: no + @reloadbattleconf, M rounds of Fire Bolt -> Lightning Bolt (never boosted, no emote)
Checks: mean boosted LB / mean normal LB ~ 350/175; an emote (0xc0) over the mob after every marking Fire Bolt
and nowhere else.

Usage: python3 -I elemark_e2e.py <run dir> <BornRok src/net/PacketTable.cpp> [rounds]
"""
import os
import re
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402

FIRE_BOLT, LIGHTNING_BOLT = 19, 20
HUGELING = 1284
USER, PW, NAME = "e2etesta", "e2epass1", "E2eTesterA"


def load_lengths(path):
    txt = open(path, encoding="utf-8").read()
    return {int(a, 16): int(b) for a, b in re.findall(r"\{0x([0-9a-fA-F]{4}),(-?\d+)\}", txt)}


class Stream:
    def __init__(self, sock, lengths):
        self.s, self.L, self.buf = sock, lengths, b""
        self.next_keepalive = 0.0

    def packets(self, seconds):
        """Yield (id, bytes) for every packet that arrives within `seconds`."""
        end = time.time() + seconds
        while True:
            while len(self.buf) >= 2:
                pid = struct.unpack_from("<H", self.buf)[0]
                ln = self.L.get(pid, 0)
                if ln == 0:
                    raise RuntimeError("unknown packet 0x%04x: stream framing lost" % pid)
                if ln < 0:
                    if len(self.buf) < 4:
                        break
                    ln = struct.unpack_from("<H", self.buf, 2)[0]
                if len(self.buf) < ln:
                    break
                pkt, self.buf = self.buf[:ln], self.buf[ln:]
                yield pid, pkt
            left = end - time.time()
            if left <= 0:
                return
            if time.time() >= self.next_keepalive:
                self.s.sendall(struct.pack("<HHI", 0x89, 0, int(time.time() * 1000) & 0xFFFFFFFF))
                self.next_keepalive = time.time() + 5
            self.s.settimeout(min(left, 0.5))
            try:
                d = self.s.recv(65536)
            except socket.timeout:
                continue
            if not d:
                raise ConnectionError("map server closed the connection")
            self.buf += d

    def drain(self, seconds):
        for _ in self.packets(seconds):
            pass


def chat(sock, text):
    msg = ("%s : %s" % (NAME, text)).encode("latin-1") + b"\0"
    sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)


def use_skill(sock, skill, target):
    # ServerType 8 skill-use-on-target: 0072 <4 pad> lv.W <2 pad> skill.W <9 pad> target.L (25 B)
    pkt = (struct.pack("<H", 0x72) + b"\0" * 4 + struct.pack("<H", 1) + b"\0" * 2
           + struct.pack("<H", skill) + b"\0" * 9 + struct.pack("<I", target))
    assert len(pkt) == 25
    sock.sendall(pkt)


class MobDied(Exception):
    pass


class Fight:
    def __init__(self, st, sock):
        self.st, self.sock = st, sock
        self.mob = None
        self.mob_dead = False

    def spawn(self):
        chat(self.sock, "@monster %d 1" % HUGELING)
        for pid, p in self.st.packets(6):
            if pid == 0x7C and struct.unpack_from("<H", p, 20)[0] == HUGELING:
                self.mob = struct.unpack_from("<I", p, 2)[0]
                self.mob_dead = False
                self.st.drain(0.5)
                return self.mob
        raise RuntimeError("no Hugeling spawn packet seen")

    def cast(self, skill):
        """Cast `skill` lv1 on the mob. Returns (damage or None, [emote types seen on the mob])."""
        for attempt in range(4):
            if self.mob_dead:
                raise MobDied()
            use_skill(self.sock, skill, self.mob)
            dmg, emotes, failed, seen = None, [], False, []
            deadline = time.time() + 5
            for pid, p in self.st.packets(5):
                seen.append("%04x" % pid)
                if pid == 0x1DE:
                    sid, src, dst = struct.unpack_from("<HII", p, 2)
                    if sid == skill and dst == self.mob:
                        dmg = struct.unpack_from("<i", p, 24)[0]
                        deadline = min(deadline, time.time() + 0.4)  # late packets of this hit
                elif pid == 0xC0:
                    gid, typ = struct.unpack_from("<IB", p, 2)
                    if gid == self.mob:
                        emotes.append(typ)
                elif pid == 0x110:  # skill failed: skill@2 btype@4 result@8 cause@9
                    failed = True
                    print("    skill %d failed: %s (cause %d)" % (skill, p.hex(), p[9]))
                    break
                elif pid == 0x80 and struct.unpack_from("<I", p, 2)[0] == self.mob and p[6] == 1:
                    self.mob_dead = True
                if time.time() >= deadline:
                    break
            if dmg is not None:
                self.st.drain(1.3)  # after-cast delay of a level-1 bolt
                return dmg, emotes
            if self.mob_dead:
                raise MobDied()
            if not failed:
                raise RuntimeError("no damage packet for skill %d on %d; packets: %s" % (skill, self.mob, " ".join(seen)))
            self.st.drain(1.0)
        raise RuntimeError("skill %d kept failing" % skill)


def main():
    run, table = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    lengths = load_lengths(table)

    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    assert kind == "list" and chars, (kind, chars)
    s.select_char(chars[0][0])
    res = s.map_enter()
    assert res[0] == "ok", res
    sock = s.map_sock
    st = Stream(sock, lengths)
    st.drain(3)

    for cmd in ("@job 2", "@lvup 80", "@allskill", "@int -300", "@int 20", "@dex -300", "@dex 160", "@heal"):
        chat(sock, cmd)
        st.drain(0.8)

    f = Fight(st, sock)
    f.spawn()
    print("Hugeling gid=%d" % f.mob)

    boosted, normal, fb_emotes, other_emotes, log = [], [], 0, 0, []

    def fresh_if_dead():
        if f.mob_dead:
            f.spawn()
            print("  (mob died, spawned gid=%d)" % f.mob)

    # ---- phase A
    for r in range(rounds):
        chat(sock, "@heal")
        st.drain(0.5)
        fresh_if_dead()
        try:
            d1, e1 = f.cast(FIRE_BOLT)
            d2, e2 = f.cast(LIGHTNING_BOLT)
            d3, e3 = f.cast(LIGHTNING_BOLT)
        except MobDied:
            print("  round %d dropped (mob died)" % r)
            fresh_if_dead()
            continue
        log.append((d1, e1, d2, e2, d3, e3))
        print("  A%-2d FB=%-4d emotes=%s  LB(marked)=%-4d emotes=%s  LB=%-4d emotes=%s" % (r, d1, e1, d2, e2, d3, e3))
        boosted.append(d2)
        normal.append(d3)
        fb_emotes += len(e1)
        other_emotes += len(e2) + len(e3)

    # ---- phase B: FB, FB, LB -- the 2nd FB uses the mark up and must not mark again
    b_lb, b_emote_ok = [], True
    for r in range(3):
        chat(sock, "@heal")
        st.drain(0.5)
        fresh_if_dead()
        try:
            b1, be1 = f.cast(FIRE_BOLT)
            b2, be2 = f.cast(FIRE_BOLT)
            b3, be3 = f.cast(LIGHTNING_BOLT)
        except MobDied:
            fresh_if_dead()
            continue
        print("  B%-2d FB=%-4d emotes=%s  FB=%-4d emotes=%s  LB=%-4d emotes=%s" % (r, b1, be1, b2, be2, b3, be3))
        b_lb.append(b3)
        b_emote_ok = b_emote_ok and len(be1) == 1 and not be2 and not be3

    # ---- phase C: switch off
    conf = os.path.join(run, "conf/battle/battle.conf")
    txt = open(conf, encoding="latin-1").read()
    assert "element_mark: yes" in txt
    open(conf, "w", encoding="latin-1").write(txt.replace("element_mark: yes", "element_mark: no"))
    chat(sock, "@reloadbattleconf")
    st.drain(1.5)
    off_lb, off_emotes = [], 0
    for r in range(4):
        chat(sock, "@heal")
        st.drain(0.5)
        fresh_if_dead()
        try:
            c1, ce1 = f.cast(FIRE_BOLT)
            c2, ce2 = f.cast(LIGHTNING_BOLT)
        except MobDied:
            fresh_if_dead()
            continue
        print("  C%-2d FB=%-4d emotes=%s  LB=%-4d emotes=%s" % (r, c1, ce1, c2, ce2))
        off_lb.append(c2)
        off_emotes += len(ce1) + len(ce2)
    open(conf, "w", encoding="latin-1").write(txt)  # restore

    mb, mn = sum(boosted) / len(boosted), sum(normal) / len(normal)
    moff = sum(off_lb) / len(off_lb)
    print("\nboosted LB: n=%d mean=%.1f min=%d max=%d" % (len(boosted), mb, min(boosted), max(boosted)))
    print("normal  LB: n=%d mean=%.1f min=%d max=%d" % (len(normal), mn, min(normal), max(normal)))
    print("ratio boosted/normal = %.3f (expected ~%.3f)" % (mb / mn, 350 / 175))
    print("switched-off LB: n=%d mean=%.1f min=%d max=%d  ratio to normal = %.3f"
          % (len(off_lb), moff, min(off_lb), max(off_lb), moff / mn))
    print("emotes after marking FB: %d of %d rounds; emotes elsewhere in A: %d" % (fb_emotes, len(boosted), other_emotes))
    checks = [
        ("boosted/normal ratio in [1.85, 2.15]", 1.85 <= mb / mn <= 2.15),
        ("every boosted LB out-damages every normal LB", min(boosted) > max(normal)),
        ("one emote after every marking Fire Bolt", fb_emotes == len(boosted)),
        ("no emote after a Lightning Bolt", other_emotes == 0),
        ("phase B: emote after the 1st FB only", b_emote_ok),
        ("phase B: LB after FB,FB not boosted (mean ratio to normal in [0.85, 1.15])",
         0.85 <= (sum(b_lb) / len(b_lb)) / mn <= 1.15),
        ("switched off: no emotes", off_emotes == 0),
        ("switched off: LB not boosted (ratio to normal in [0.85, 1.15])", 0.85 <= moff / mn <= 1.15),
    ]
    bad = 0
    for name, ok in checks:
        print("%s  %s" % ("ok  " if ok else "FAIL", name))
        bad += not ok
    s.quit_game()
    print("ALL PASSED" if not bad else "%d CHECK(S) FAILED" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
