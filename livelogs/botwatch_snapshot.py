#!/usr/bin/env python3
"""snapshot.py <out.tsv> <map log>... : every (account, character, IP) seen logging in to the map, with
first/last log file it appeared in and the login count. Used to track how bot farms move between IPs."""
import re, sys, collections
out, logs = sys.argv[1], sys.argv[2:]
seen = {}
for k, p in enumerate(logs):
    for l in open(p, errors="replace"):
        m = re.search(r"'(.*?)' logged in\. \(AID/CID: '(\d+)/(\d+)'.*IP: '([\d.]+)'", l)
        if not m:
            continue
        key = (int(m.group(2)), int(m.group(3)), m.group(4))
        r = seen.setdefault(key, [m.group(1), k, k, 0])
        r[2] = k; r[3] += 1
with open(out, "w") as f:
    f.write("# logs: " + " ".join(p.rsplit("/", 1)[-1] for p in logs) + "\n")
    f.write("account_id\tchar_id\tname\tip\tlogins\tfirst_log\tlast_log\n")
    for (a, c, ip), (n, f0, f1, cnt) in sorted(seen.items(), key=lambda x: (x[0][2], x[0][0])):
        f.write("%d\t%d\t%s\t%s\t%d\t%d\t%d\n" % (a, c, n, ip, cnt, f0, f1))
