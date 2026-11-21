#!/usr/bin/env python3
"""Wake-ups and CPU of running server processes, per thread, over an interval (from /proc, no strace).

A blocking epoll_wait / cond_wait that ends = one voluntary context switch of that thread, so the delta of
voluntary_ctxt_switches over N seconds is the thread's wake-up rate.
Usage: python3 -I wakeups.py <seconds> <name>=<pid> [<name>=<pid> ...]
"""
import os
import sys
import time

HZ = os.sysconf("SC_CLK_TCK")


def threads(pid):
    out = {}
    for tid in os.listdir("/proc/%d/task" % pid):
        base = "/proc/%d/task/%s/" % (pid, tid)
        try:
            st = open(base + "status").read()
            stat = open(base + "stat").read()
        except OSError:
            continue
        name = [ln.split(":", 1)[1].strip() for ln in st.splitlines() if ln.startswith("Name:")][0]
        vol = int([ln.split(":")[1] for ln in st.splitlines() if ln.startswith("voluntary_ctxt_switches")][0])
        inv = int([ln.split(":")[1] for ln in st.splitlines() if ln.startswith("nonvoluntary_ctxt_switches")][0])
        f = stat.rsplit(")", 1)[1].split()
        cpu = (int(f[11]) + int(f[12])) / HZ  # utime + stime
        out[int(tid)] = (name, vol, inv, cpu)
    return out


def main():
    secs = float(sys.argv[1])
    procs = [(a.split("=")[0], int(a.split("=")[1])) for a in sys.argv[2:]]
    before = {p: threads(p) for _, p in procs}
    time.sleep(secs)
    after = {p: threads(p) for _, p in procs}
    for name, p in procs:
        tot_w = tot_c = 0.0
        rows = []
        for tid, (tn, vol, inv, cpu) in sorted(after[p].items()):
            if tid not in before[p]:
                continue
            _, v0, i0, c0 = before[p][tid]
            w = (vol - v0) / secs
            c = (cpu - c0) / secs * 100
            tot_w += w
            tot_c += c
            rows.append("    %s %-16s wake-ups %7.1f/s  cpu %5.2f%%%s" % (tid, tn, w, c, "  (main)" if tid == p else ""))
        print("%s pid %d: %.1f wake-ups/s, cpu %.2f%% over %.0f s" % (name, p, tot_w, tot_c, secs))
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
