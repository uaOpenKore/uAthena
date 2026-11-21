#!/usr/bin/env python3
"""Split an eAthena server log into runs and summarise the error-ish lines of chosen runs.

Usage: python3 -I runs.py <log> [run index ...]   (index -1 = last run; default: list runs only)
A run starts at "[Status]: Memory manager initialised". Lines carry no timestamps; the ua-start lines do.
Error-ish lines ([Error] [Warning] [SQL] [Debug] [Fatal] + a few keywords) are grouped after digits,
IPs and quoted names are masked, so the counts show which kinds of problems appeared.
"""
import re
import sys
from collections import Counter

KEYS = ("[Error]", "[Warning]", "[SQL]", "[Debug]", "[Fatal", "rolled back", "is written now",
        "DB read failed", "Segmentation", "core dumped", "loop_stall", "assert")


def runs_of(path):
    runs, cur = [], None
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if "[Status]: Memory manager initialised" in line:
                cur = []
                runs.append(cur)
            if cur is None:
                cur = []
                runs.append(cur)
            cur.append(line)
    return runs


def norm(line):
    s = re.sub(r"\x1b\[[0-9;]*m", "", line)
    s = re.sub(r"\d+\.\d+\.\d+\.\d+", "<ip>", s)
    s = re.sub(r"'[^']*'", "'<s>'", s)
    s = re.sub(r"\d+", "N", s)
    return s[:200]


def main():
    path = sys.argv[1]
    runs = runs_of(path)
    for i, r in enumerate(runs):
        stamp = next((l for l in r[:40] if "ua-start" in l and "(20" in l), "")
        print("run %d: %d lines %s" % (i, len(r), stamp[-21:]))
    for a in sys.argv[2:]:
        r = runs[int(a)]
        c = Counter()
        for line in r:
            if any(k in line for k in KEYS):
                c[norm(line)] += 1
        print("\n=== run %s: %d error-ish lines, %d kinds" % (a, sum(c.values()), len(c)))
        for k, n in c.most_common(60):
            print("%7d  %s" % (n, k))


if __name__ == "__main__":
    main()
