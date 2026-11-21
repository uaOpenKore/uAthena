#!/usr/bin/env python3
# PADMETRIC summary of one map-server log segment: who sends what in the unused packet bytes.
# usage: python3 -I padm.py <map-log.txt>
import re
import sys
from collections import Counter, defaultdict

LOGIN = re.compile(r"'(?P<name>.*)' logged in\. \(AID/CID: '(?P<aid>\d+)/(?P<cid>\d+)', Packet Ver: '(?P<ver>\d+)', IP: '(?P<ip>[\d.]+)'")
FIRST = re.compile(r"\[PADMETRIC\] first_walk aid=(?P<aid>\d+) cid=(?P<cid>\d+) name='(?P<name>.*)' ip=(?P<ip>[\d.]+) ver=\d+ cmd=0x[0-9a-f]+ pad=(?P<pad>[0-9a-f-]+)")
LOGOUT = re.compile(r"\[PADMETRIC\] logout aid=(?P<aid>\d+) cid=(?P<cid>\d+) name='(?P<name>.*)' ver=\d+(?P<rest>.*)$")
KIND = re.compile(r" (walk|act|skill|tick)=(\d+)/z(\d+)/c(\d+) first=([0-9a-f-]+) last=([0-9a-f-]+)")
BOTS_1118 = ["5.83.145.35", "200.187.162.217", "180.75.246.248", "136.158.40.200", "188.163.120.138"]


def pad_class(kind, pad):
    if pad == "-":
        return "none"
    if kind == "walk" and pad == "000044":
        return "okore"          # OpenKore / old BornRok bytes
    if set(pad) == {"0"}:
        return "zero"
    if pad == "01" * (len(pad) // 2):
        return "marker"         # BornRok 0.0.53.0+
    return "other"


def main(path):
    ip_of = {}
    logins = Counter()
    chars_per_ip = defaultdict(set)
    accounts_per_ip = defaultdict(set)
    first_walk = Counter()
    sessions = []
    for line in open(path, encoding="latin-1"):
        m = LOGIN.search(line)
        if m:
            ip_of[m["aid"]] = m["ip"]
            logins[m["ip"]] += 1
            chars_per_ip[m["ip"]].add(m["cid"])
            accounts_per_ip[m["ip"]].add(m["aid"])
            continue
        m = FIRST.search(line)
        if m:
            first_walk[pad_class("walk", m["pad"])] += 1
            continue
        m = LOGOUT.search(line)
        if m:
            kinds = {k: dict(total=int(t), zero=int(z), changed=int(c), first=f, last=l)
                     for k, t, z, c, f, l in KIND.findall(m["rest"])}
            sessions.append(dict(aid=m["aid"], cid=m["cid"], name=m["name"], ip=ip_of.get(m["aid"], "?"), kinds=kinds))

    print("logins:", sum(logins.values()), "from", len(logins), "IPs;", "first_walk classes:", dict(first_walk))
    print("logout summaries:", len(sessions))

    # signature = class per kind, plus whether any kind changed inside the session
    sig_count = Counter()
    sig_ips = defaultdict(Counter)
    sig_names = defaultdict(set)
    for s in sessions:
        parts = []
        for k in ("walk", "act", "skill", "tick"):
            if k in s["kinds"]:
                d = s["kinds"][k]
                c = pad_class(k, d["first"])
                if d["changed"]:
                    c += "~"
                parts.append(f"{k}:{c}")
        sig = " ".join(parts) if parts else "(no packets)"
        sig_count[sig] += 1
        sig_ips[sig][s["ip"]] += 1
        sig_names[sig].add(s["name"])
    print("\n== session signatures (class per packet kind; ~ = changed within the session)")
    for sig, n in sig_count.most_common():
        top = ", ".join(f"{ip}x{c}" for ip, c in sig_ips[sig].most_common(4))
        print(f"{n:5d}  {sig}\n       IPs {len(sig_ips[sig])}: {top}")

    # sessions whose walk is NOT the OpenKore/old-BornRok bytes: real clients (or unknown tools)
    print("\n== sessions with a walk pad other than 000044 (aid / name / ip / walk first..last, changed)")
    shown = 0
    for s in sessions:
        w = s["kinds"].get("walk")
        if w and pad_class("walk", w["first"]) != "okore":
            other = " ".join(f"{k}={d['first']}" for k, d in s["kinds"].items() if k != "walk")
            print(f"  {s['aid']} '{s['name']}' {s['ip']} walk {w['first']}..{w['last']} c{w['changed']}/{w['total']}  {other}"[:230])
            shown += 1
    print("  total:", shown)

    # constant non-zero bytes outside the walk (like act ...3766613200): not stock OpenKore, not old BornRok
    print("\n== sessions with walk 000044 but non-zero bytes in act/skill/tick")
    odd = Counter()
    odd_ips = defaultdict(Counter)
    for s in sessions:
        w = s["kinds"].get("walk")
        if not w or pad_class("walk", w["first"]) != "okore":
            continue
        for k in ("act", "skill", "tick"):
            d = s["kinds"].get(k)
            if d and pad_class(k, d["first"]) not in ("zero", "none"):
                odd[(k, d["first"])] += 1
                odd_ips[(k, d["first"])][s["ip"]] += 1
    for (k, p), n in odd.most_common(12):
        print(f"  {n:4d} {k} first={p}  IPs: " + ", ".join(f"{ip}x{c}" for ip, c in odd_ips[(k, p)].most_common(4)))

    # one client type per session: original client (varying bytes), OpenKore/old BornRok (000044 + zeros),
    # the 7fa2 variant (OpenKore walk, constant 37666132 in the attack), BornRok 0.0.53.0 (01 marker), no packets
    def client_type(s):
        ks = s["kinds"]
        if not ks:
            return "no packets"
        if any(pad_class(k, d["first"]) == "marker" for k, d in ks.items()):
            return "BornRok 0.0.53+ (01)"
        w = ks.get("walk")
        if w and pad_class("walk", w["first"]) not in ("okore",):
            return "original client"
        if any(pad_class(k, d["first"]) == "other" and k == "tick" for k, d in ks.items()):
            return "original client"
        if "37666132" in ks.get("act", {}).get("first", ""):
            return "OpenKore walk + 7fa2 attack"
        return "OpenKore / old BornRok (000044, zeros)"

    per_type = defaultdict(lambda: dict(sessions=0, aids=set(), ips=set()))
    for s in sessions:
        t = per_type[client_type(s)]
        t["sessions"] += 1
        t["aids"].add(s["aid"])
        t["ips"].add(s["ip"])
    print("\n== client type per session (sessions / accounts / IPs)")
    for name, t in sorted(per_type.items(), key=lambda kv: -kv[1]["sessions"]):
        print(f"  {name:40s} {t['sessions']:5d} / {len(t['aids']):4d} / {len(t['ips']):3d}  IPs: {', '.join(sorted(t['ips']))[:150]}")
    aid_types = defaultdict(set)
    for s in sessions:
        aid_types[s["aid"]].add(client_type(s))
    mixed = {a: ts for a, ts in aid_types.items() if len(ts - {"no packets"}) > 1}
    print("  accounts seen with more than one client type:", len(mixed))
    for a, ts in list(mixed.items())[:10]:
        print(f"    {a}: {sorted(ts)}")

    # BornRok sends one tick every 4 s in game (GameScene lastPing_ > 4.0), so over a run of N seconds one account
    # (sessions of one account never overlap) can send at most N/4 ticks from BornRok.
    if len(sys.argv) > 2:
        run_s = int(sys.argv[2])
        cap = run_s // 4
        ticks = Counter()
        nsess = Counter()
        for s in sessions:
            ticks[s["aid"]] += s["kinds"].get("tick", {}).get("total", 0)
            nsess[s["aid"]] += 1
        over = [a for a in ticks if ticks[a] > cap]
        print(f"\n== tick packets per account over the run ({run_s} s -> BornRok max {cap})")
        print(f"  accounts over the cap: {len(over)} of {len(ticks)}; their sessions: {sum(nsess[a] for a in over)}")
        type_over = Counter()
        for s in sessions:
            if s["aid"] in over:
                type_over[client_type(s)] += 1
        print("  their sessions by client type:", dict(type_over))
        ip_over = Counter(s["ip"] for s in sessions if s["aid"] in over)
        print("  their IPs:", ", ".join(f"{ip}x{c}" for ip, c in ip_over.most_common(12)))
        for a in sorted(over, key=lambda a: -ticks[a])[:8]:
            names = sorted({s['name'] for s in sessions if s['aid'] == a})
            print(f"    {a} {names[:3]} ticks={ticks[a]} sessions={nsess[a]} -> {ticks[a] / run_s:.1f} ticks/s at least")
        # accounts under the cap that only ever showed 000044/zeros: could be old BornRok or a bot
        okore_only = [a for a in ticks if a not in over and aid_types[a] <= {"OpenKore / old BornRok (000044, zeros)", "no packets"}]
        print(f"  000044/zeros accounts under the cap (old BornRok or a bot, can't tell yet): {len(okore_only)}")

    print("\n== top IPs by logins (logins / accounts / chars)")
    for ip, n in logins.most_common(15):
        print(f"  {ip:16s} {n:5d} / {len(accounts_per_ip[ip]):3d} / {len(chars_per_ip[ip]):3d}" + ("  (bot IP 18.11)" if ip in BOTS_1118 else ""))


if __name__ == "__main__":
    main(sys.argv[1])
