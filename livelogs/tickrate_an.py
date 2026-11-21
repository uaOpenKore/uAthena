#!/usr/bin/env python3
"""tick_rate (logout lines, server 5176452b) by client kind, per account and per IP.

Usage: python3 -I tickrate_an.py <map log of one run>
Client kind is taken from the walk pad (PADMETRIC): original uaRO.exe sends varying ASCII-hex bytes,
OpenKore and BornRok before 0.0.53.0 send 000044, BornRok 0.0.53.0+ sends 010101 (marker).
BornRok sends one tick every 4 s (0.25/s); OpenKore with ai_sync 0.1 about 9/s.
"""
import re
import sys
from collections import Counter, defaultdict

LOGIN = re.compile(r"'(?P<name>.*)' logged in\. \(AID/CID: '(?P<aid>\d+)/(?P<cid>\d+)', Packet Ver: '(?P<ver>\d+)', IP: '(?P<ip>[\d.]+)'")
LOGOUT = re.compile(r"\[PADMETRIC\] logout aid=(?P<aid>\d+) cid=(?P<cid>\d+) name='(?P<name>.*)' ver=\d+ "
                    r"online=(?P<online>\d+)s tick_rate=(?P<rate>[\d.]+)/s(?P<rest>.*)$")
WALK = re.compile(r" walk=(\d+)/z\d+/c\d+ first=([0-9a-f-]+) last=([0-9a-f-]+)")
TICK = re.compile(r" tick=(\d+)/z\d+/c\d+ first=([0-9a-f-]+) last=([0-9a-f-]+)")


def kind_of(walk_pad):
    if walk_pad is None:
        return "no-walk"
    if walk_pad == "000044":
        return "okore/old-bornrok"
    if walk_pad == "010101":
        return "bornrok-0.0.53+"
    if set(walk_pad) == {"0"}:
        return "zero"
    return "uaro.exe"


def pct(vals, p):
    v = sorted(vals)
    return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else 0


def main(path):
    ip_of = {}
    sess = []
    for line in open(path, encoding="latin-1"):
        m = LOGIN.search(line)
        if m:
            ip_of[m["aid"]] = m["ip"]
            continue
        m = LOGOUT.search(line)
        if m:
            w = WALK.search(m["rest"])
            t = TICK.search(m["rest"])
            sess.append(dict(aid=m["aid"], cid=m["cid"], name=m["name"], online=int(m["online"]),
                             rate=float(m["rate"]), walks=int(w.group(1)) if w else 0,
                             ticks=int(t.group(1)) if t else 0, kind=kind_of(w.group(2) if w else None),
                             ip=ip_of.get(m["aid"], "?")))
    print("logout lines: %d" % len(sess))
    long_ = [s for s in sess if s["online"] >= 60]
    print("sessions >= 60 s: %d\n" % len(long_))
    print("%-20s %6s %8s %8s %8s %8s %8s" % ("kind", "sess", "p10", "median", "p90", "max", ">1/s"))
    by_kind = defaultdict(list)
    for s in long_:
        by_kind[s["kind"]].append(s)
    for k, ss in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        r = [s["rate"] for s in ss]
        print("%-20s %6d %8.2f %8.2f %8.2f %8.2f %8d" % (k, len(ss), pct(r, .1), pct(r, .5), pct(r, .9), max(r),
                                                       sum(1 for x in r if x > 1.0)))
    # rate histogram
    print("\ntick_rate histogram (sessions >= 60 s):")
    bins = [(0, 0.05), (0.05, 0.2), (0.2, 0.3), (0.3, 1.0), (1.0, 5.0), (5.0, 8.0), (8.0, 10.0), (10.0, 1e9)]
    for lo, hi in bins:
        n = sum(1 for s in long_ if lo <= s["rate"] < hi)
        print("  [%5.2f, %5s): %5d" % (lo, ("%.2f" % hi) if hi < 1e8 else "inf", n))
    # accounts above 1/s
    fast = [s for s in long_ if s["rate"] > 1.0]
    acc = defaultdict(lambda: [0, 0, set(), set(), Counter()])
    for s in fast:
        a = acc[s["aid"]]
        a[0] += 1
        a[1] += s["online"]
        a[2].add(s["name"])
        a[3].add(s["ip"])
        a[4][s["kind"]] += 1
    print("\nsessions > 1 tick/s: %d, accounts: %d, online hours: %.1f" % (len(fast), len(acc),
                                                                         sum(s["online"] for s in fast) / 3600))
    allh = sum(s["online"] for s in long_) / 3600
    print("all sessions >= 60 s: online hours %.1f (fast share %.0f%%)" % (allh, 100 * sum(s["online"] for s in fast) / 3600 / allh if allh else 0))
    ips = Counter()
    ipacc = defaultdict(set)
    for s in fast:
        ips[s["ip"]] += s["online"]
        ipacc[s["ip"]].add(s["aid"])
    print("\nIPs of the > 1/s sessions, by online time:")
    for ip, sec in ips.most_common(25):
        print("  %-16s %6.1f h  %3d accounts" % (ip, sec / 3600, len(ipacc[ip])))
    # slow sessions with okore pad: candidates for old BornRok / slow bots
    slow_okore = [s for s in long_ if s["kind"] == "okore/old-bornrok" and s["rate"] <= 0.3]
    print("\nokore-pad sessions at <= 0.3/s (old BornRok or a slow bot): %d, accounts %d" %
          (len(slow_okore), len({s["aid"] for s in slow_okore})))
    for s in sorted(slow_okore, key=lambda s: -s["online"])[:12]:
        print("  aid=%s %-16s %-16s online=%5ds rate=%.2f walks=%d ticks=%d" % (s["aid"], s["name"][:16], s["ip"],
                                                                           s["online"], s["rate"], s["walks"], s["ticks"]))
    # uaro.exe sessions
    ua = [s for s in long_ if s["kind"] == "uaro.exe"]
    print("\nuaro.exe sessions: %d, accounts %d" % (len(ua), len({s["aid"] for s in ua})))
    for s in sorted(ua, key=lambda s: -s["online"])[:10]:
        print("  aid=%s %-16s %-16s online=%5ds rate=%.2f walks=%d ticks=%d" % (s["aid"], s["name"][:16], s["ip"],
                                                                           s["online"], s["rate"], s["walks"], s["ticks"]))
    mk = [s for s in sess if s["kind"] == "bornrok-0.0.53+"]
    print("\nBornRok 0.0.53+ (marker) sessions: %d" % len(mk))
    for s in mk[:10]:
        print("  aid=%s %-16s %-16s online=%5ds rate=%.2f" % (s["aid"], s["name"][:16], s["ip"], s["online"], s["rate"]))


if __name__ == "__main__":
    main(sys.argv[1])
