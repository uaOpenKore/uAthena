#!/usr/bin/env python3
"""e2e check of «Натиск» (uAthena [streak]) on a local stand.

A GM Swordsman (STR 1, DEX 60, LUK 1) fights Hugelings (1284: Water 1, large, DEF 0). Bare hands (and later an Axe:
wLV1, ATK 38, large 100%) give damage with no random part, so every landed normal hit at step k must be exactly
floor(B * (100 + 25k) / 100) - c (B = base attack, c = the target's flat defense; both fitted from phase 1), and a
Bash lv10 floor(floor(B * rate / 100) * 400 / 100) - c.
  1 growth   30 hits on mob A: 100, 125, ... 700% from the 25th hit on
  2 skill    5 hits on mob B, Bash on B (225% base), next hit 100%; 1 hit, Bash (125%), next hit 100%
  3 switch   first hits on A after B = 100%, 125%
  4 teleport 3 hits, @jump to the same cell, next hit 100%
  5 death    3 hits, @die + @alive, next hit 100%
  6 weapon   equip an Axe (restart with the new base), unequip (bare-hand step 0), re-equip (axe step 0)
  7 misses   Punk (1199, FLEE 148) with DEX 19 (~50% hit): every landed hit fits the step tracked +1 hit / -1 miss
  8 off      weapon_streak: no + @reloadbattleconf: no growth
Usage: python3 -I streak_e2e.py <run dir> <BornRok src/net/PacketTable.cpp>
"""
import os
import re
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, NAME, Stream, chat, load_lengths  # noqa: E402

HUGELING, PUNK, AXE, BASH = 1284, 1199, 1301, 5


def rate(k):
    return min(100 + 25 * k, 700)


def pos3(p, o):  # WBUFPOS
    return (p[o] << 2) | (p[o + 1] >> 6), ((p[o + 1] & 0x3F) << 4) | (p[o + 2] >> 4)


def pos5_dest(p, o):  # WBUFPOS2 destination
    return ((p[o + 2] & 0x0F) << 6) | (p[o + 3] >> 2), ((p[o + 3] & 0x03) << 8) | p[o + 4]


def fit(triples, hi_extra=12):
    """(B, c) with damage == floor(B*rate(k)/100) - (0 if crit else c) for every (k, damage, crit), or None."""
    d0 = min(d for k, d, cr in triples if k == 0)
    for B in range(d0, d0 + hi_extra):
        for c in range(0, hi_extra):
            if all(B * rate(k) // 100 - (0 if cr else c) == d for k, d, cr in triples):
                return B, c
    return None


class Me:
    def __init__(self, st, sock, aid):
        self.st, self.sock, self.aid = st, sock, aid
        self.dead, self.pos = set(), {}
        self.crit = False  # the last attack was a critical (crits ignore defense: no flat -c)

    def note(self, pid, p):
        if pid == 0x91:  # map change (also @jump on the same map): the client must ack the load again
            self.sock.sendall(struct.pack("<H", 0x7D))
        elif pid == 0x80 and p[6] == 1:
            self.dead.add(struct.unpack_from("<I", p, 2)[0])
        elif pid == 0x7C:
            self.pos[struct.unpack_from("<I", p, 2)[0]] = pos3(p, 36)
        elif pid == 0x86:
            self.pos[struct.unpack_from("<I", p, 2)[0]] = pos5_dest(p, 6)

    def drain(self, sec):
        for pid, p in self.st.packets(sec):
            self.note(pid, p)

    def cmd(self, text, wait=0.8):
        chat(self.sock, text)
        out = []
        for pid, p in self.st.packets(wait):
            self.note(pid, p)
            if pid == 0x8E:
                out.append(p[4:].split(b"\0")[0].decode("latin-1"))
        return out

    def spawn(self, mob, n=1):
        chat(self.sock, "@monster %d %d" % (mob, n))
        ids = []
        for pid, p in self.st.packets(6):
            self.note(pid, p)
            if pid == 0x7C and struct.unpack_from("<H", p, 20)[0] == mob:
                ids.append(struct.unpack_from("<I", p, 2)[0])
                if len(ids) == n:
                    break
        self.drain(0.5)
        assert len(ids) == n, "spawned %d of %d" % (len(ids), n)
        return ids

    def walk_to(self, target):
        x, y = self.pos[target]
        self.sock.sendall(struct.pack("<HBBB", 0xA7, 0, 0, 0x44)
                          + bytes([(x >> 2) & 0xFF, ((x << 6) | ((y >> 4) & 0x3F)) & 0xFF, (y << 4) & 0xFF]))
        self.drain(2.0)

    def attack(self, target):
        """One single attack (0x190 action 0). Returns damage (0 = miss) or None."""
        for attempt in range(5):
            pkt = struct.pack("<H", 0x190) + b"\0" * 3 + struct.pack("<I", target) + b"\0" * 9 + b"\0"
            self.sock.sendall(pkt)
            far = False
            for pid, p in self.st.packets(3):
                self.note(pid, p)
                if pid == 0x8A:
                    src, dst = struct.unpack_from("<II", p, 2)
                    if src == self.aid and dst == target:
                        dmg = struct.unpack_from("<h", p, 22)[0] + struct.unpack_from("<h", p, 27)[0]
                        self.crit = p[26] == 10
                        self.drain(0.75)  # attack delay of a bare-hand Swordsman
                        return dmg
                elif pid == 0x139:  # out of attack range: walk next to it and try again
                    far = True
                    break
            if far and target in self.pos:
                self.walk_to(target)
                continue
            if target in self.dead:
                print("    attack: target %d is dead" % target)
                return None
        print("    attack on %d: no damage packet (pos %s)" % (target, self.pos.get(target)))
        return None

    def bash(self, target):
        for _ in range(3):
            self.sock.sendall(struct.pack("<H", 0x72) + b"\0" * 4 + struct.pack("<H", 10) + b"\0" * 2
                              + struct.pack("<H", BASH) + b"\0" * 9 + struct.pack("<I", target))
            for pid, p in self.st.packets(3):
                self.note(pid, p)
                if pid == 0x1DE:
                    sid, src, dst = struct.unpack_from("<HII", p, 2)
                    if sid == BASH and dst == target:
                        self.drain(1.0)
                        return struct.unpack_from("<i", p, 24)[0]
                elif pid == 0x110:
                    print("    Bash failed: cause %d" % p[9])
                    break
            self.drain(1.0)
        return None


def main():
    run, table = sys.argv[1], sys.argv[2]
    lengths = load_lengths(table)
    s = rostub.Session(USER, PW)
    s.login()
    _, (kind, chars) = s.char_enter()
    s.select_char(chars[0][0])
    assert s.map_enter()[0] == "ok"
    st = Stream(s.map_sock, lengths)
    st.drain(3)
    me = Me(st, s.map_sock, s.aid)

    for c in ("@job 1", "@lvup 98", "@allskill", "@str -300", "@dex -300", "@dex 60", "@luk -300",
              "@vit -300", "@vit 80", "@agi -300", "@int -300", "@heal"):
        me.cmd(c)
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok))
        print("%s  %s %s" % ("ok  " if ok else "FAIL", name, detail))

    # Each Hugeling is spawned right before its phase: one spawned earlier wanders off out of sight during the
    # 30 hits on A (no position updates any more -> the attacks find no target; the test flaked ~1 in 3).
    (a,) = me.spawn(HUGELING, 1)
    print("Hugeling A=%d" % a)

    # ---- 1 growth + cap
    seq, crits = [], []
    for _ in range(30):
        seq.append(me.attack(a))
        crits.append(me.crit)
    print("  1: %s crits at %s" % (seq, [i for i, x in enumerate(crits) if x]))
    fitted = fit([(k, d, crits[k]) for k, d in enumerate(seq)]) if None not in seq else None
    check("1 growth 100..700% and the cap from the 25th hit", fitted is not None, "B, c = %s" % (fitted,))
    if fitted is None:
        print("cannot continue without the base")
        return 1
    B, cdef = fitted

    def dmg(k, base=None, crit=False):
        return (base or B) * rate(k) // 100 - (0 if crit else cdef)

    def hit(target, k, base=None):
        """attack once; True when the damage is the step-k damage (crit or not)"""
        d = me.attack(target)
        return d, d == dmg(k, base, me.crit)

    def bash_dmg(k, base=None):
        return ((base or B) * rate(k) // 100) * 400 // 100 - cdef

    # ---- 2 an active skill spends the streak
    (b,) = me.spawn(HUGELING, 1)
    hits = [hit(b, k) for k in range(5)]
    bash5 = me.bash(b)
    after = hit(b, 0)
    bash1 = me.bash(b)
    after2 = hit(b, 0)
    print("  2: hits %s Bash %s next %s Bash %s next %s" % ([h[0] for h in hits], bash5, after[0], bash1, after2[0]))
    check("2 hits on B: 100..200%", all(h[1] for h in hits))
    check("2 Bash after 5 hits gets the 225% base", bash5 == bash_dmg(5), "exp %d" % bash_dmg(5))
    check("2 the hit after Bash starts again at 100%", after[1])
    check("2 Bash after 1 hit gets the 125% base", bash1 == bash_dmg(1), "exp %d" % bash_dmg(1))
    check("2 and 100% again after it", after2[1])

    # ---- 3 switching back to A restarts there (A had a full streak)
    sw = [hit(a, 0), hit(a, 1)]
    check("3 switch back to A: 100%, 125%", sw[0][1] and sw[1][1], str([x[0] for x in sw]))

    # ---- 4 teleport (@jump to the same cell)
    me.attack(a)  # 150%
    where = me.cmd("@where %s" % NAME, 1.0)
    m = [re.search(r" (\d+) (\d+)$", w) for w in where]
    m = [x for x in m if x]
    if not m:
        check("4 @where answered", False, str(where))
    else:
        x, y = int(m[-1].group(1)), int(m[-1].group(2))
        me.cmd("@jump %d %d" % (x, y), 1.5)
        t = hit(a, 0)
        check("4 @jump resets: next hit 100%", t[1], "got %s at %d,%d" % (t[0], x, y))

    # ---- 5 death
    me.attack(a)
    me.attack(a)
    me.cmd("@die", 1.0)
    me.cmd("@alive", 1.5)
    me.cmd("@heal")
    t = hit(a, 0)
    check("5 death resets: next hit 100%", t[1], "got %s" % t[0])

    # ---- 6 weapon change
    chat(s.map_sock, "@item %d 1" % AXE)
    idx = None
    for pid, p in st.packets(2):
        me.note(pid, p)
        if pid in (0xA0, 0x2D4) and struct.unpack_from("<H", p, 6)[0] == AXE:
            idx = struct.unpack_from("<H", p, 2)[0]
    me.drain(0.5)
    if idx is None:
        check("6 got an Axe", False)
    else:
        (c,) = me.spawn(HUGELING, 1)
        me.attack(c)
        me.attack(c)  # bare-hand streak on C: 2 steps
        s.map_sock.sendall(struct.pack("<HHH", 0xA9, idx, 0x0002))  # equip in the right hand
        me.drain(1.0)
        first = me.attack(c)
        bx = (first + (0 if me.crit else cdef)) if first else 0
        ax = [hit(c, 1, bx), hit(c, 2, bx)]
        check("6 equip resets: axe hits restart at 100%",
              bx > B and ax[0][1] and ax[1][1], "%s (axe base %d)" % ([first] + [x[0] for x in ax], bx))
        s.map_sock.sendall(struct.pack("<HH", 0xAB, idx))  # unequip
        me.drain(1.0)
        bare = [hit(c, 0), hit(c, 1)]
        check("6 unequip resets: bare hands at 100%, 125%", bare[0][1] and bare[1][1], str([x[0] for x in bare]))
        s.map_sock.sendall(struct.pack("<HHH", 0xA9, idx, 0x0002))
        me.drain(1.0)
        t = hit(c, 0, bx)
        check("6 re-equip resets: axe at 100%", t[1], "got %s" % t[0])
        s.map_sock.sendall(struct.pack("<HH", 0xAB, idx))
        me.drain(1.0)

    # ---- 7 misses step back (Punk: FLEE 148; DEX 19 -> ~50% hit)
    me.cmd("@dex -300")
    me.cmd("@dex 19")
    me.cmd("@str 30")  # bare-hand base ~43: well above Punk's flat defense, still no random part
    me.cmd("@heal")
    (punk,) = me.spawn(PUNK, 1)
    count, pairs, landed, missed = 0, [], 0, 0
    for i in range(60):
        d = me.attack(punk)
        if d is None:
            break
        if d == 0:
            missed += 1
            count = max(0, count - 1)
        else:
            pairs.append((count, d, me.crit))
            landed += 1
            count = min(count + 1, 24)
        if i % 10 == 9:
            me.cmd("@heal", 0.3)
    f7 = fit(pairs) if any(k == 0 for k, _, _ in pairs) else None
    print("  7: landed %d missed %d fit %s pairs %s" % (landed, missed, f7, pairs[:12]))
    check("7 a miss takes one step back (all landed hits fit the tracked steps)",
          landed >= 10 and missed >= 5 and f7 is not None, "landed %d missed %d" % (landed, missed))

    # ---- 8 switched off
    me.cmd("@dex -300")
    me.cmd("@dex 60")
    me.cmd("@str -300")
    me.cmd("@heal")
    (fresh,) = me.spawn(HUGELING, 1)
    conf = os.path.join(run, "conf/battle/battle.conf")
    txt = open(conf, encoding="latin-1").read()
    assert "weapon_streak: yes" in txt
    open(conf, "w", encoding="latin-1").write(txt.replace("weapon_streak: yes", "weapon_streak: no"))
    me.cmd("@reloadbattleconf", 1.5)
    # No growth = every hit has the same damage (a crit: + the flat defense it ignores). Compared with the
    # first hit, not with phase 1's base: the bare-hand base can move by a point after phase 7.
    off = []
    for _ in range(10):  # 5 landed hits; an attack can find a fresh Hugeling walked out of reach (None)
        d = me.attack(fresh)
        if d:
            off.append((d, me.crit))
        if len(off) == 5:
            break
    open(conf, "w", encoding="latin-1").write(txt)
    me.cmd("@reloadbattleconf", 1.5)
    plain = [d - (cdef if cr else 0) for d, cr in off if d]
    check("8 weapon_streak: no -> no growth", len(plain) == 5 and len(set(plain)) == 1, str(off))

    s.quit_game()
    bad = [n for n, ok in results if not ok]
    print("ALL PASSED" if not bad else "%d CHECK(S) FAILED: %s" % (len(bad), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
