#!/usr/bin/env python3
"""EXPLAIN every distinct query shape of a MariaDB general log against the audit instance.

Usage: python3 -I explain_log.py <general.log>
Prints one line per shape: count, access type per table, rows examined estimate, key used, and the
first example (cut). Shapes are the query text with numbers and quoted strings replaced by '?'.
"""
import re
import subprocess
import sys

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-B", "-e"]


def shape(q):
    q = re.sub(r"'(?:[^'\\]|\\.)*'", "?", q)
    q = re.sub(r"\b\d+\b", "?", q)
    q = re.sub(r"\(\?(?:,\s*\?)+\)", "(?...)", q)
    return re.sub(r"\s+", " ", q).strip()


def main():
    shapes = {}
    order = []
    for line in open(sys.argv[1], encoding="latin-1"):
        m = re.search(r"\sQuery\t(.*)$", line.rstrip("\n"))
        if not m:
            continue
        q = m.group(1).strip()
        if q.startswith("SELECT 'MARK:") or q.startswith("SET NAMES") or q.startswith("SHOW ") or q.startswith("EXPLAIN"):
            continue
        sh = shape(q)
        if sh not in shapes:
            shapes[sh] = [0, q]
            order.append(sh)
        shapes[sh][0] += 1
    for sh in order:
        cnt, q = shapes[sh]
        verb = q.split(None, 1)[0].upper()
        plan = "-"
        if verb in ("SELECT", "UPDATE", "DELETE"):
            r = subprocess.run(MYSQL + ["EXPLAIN " + q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="latin-1")
            rows = [ln.split("\t") for ln in r.stdout.strip().splitlines()]
            if rows and rows[0] and rows[0][0] == "id":
                hdr = rows[0]
                parts = []
                for row in rows[1:]:
                    d = dict(zip(hdr, row))
                    parts.append("%s:%s key=%s rows=%s %s" % (d.get("table"), d.get("type"), d.get("key"),
                                                            d.get("rows"), d.get("Extra", "")))
                plan = " | ".join(parts)
            else:
                plan = "EXPLAIN failed: " + r.stdout.strip()[:120]
        print("%4d  %-7s %s\n      %s" % (cnt, verb, plan, q[:200]))


if __name__ == "__main__":
    main()
