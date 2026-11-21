#!/bin/bash
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
$M -e "UPDATE login SET level=99 WHERE account_id=2000006"
bash "$E/srv.sh" stop "$RUN" > /dev/null; bash "$E/srv.sh" start "$RUN" | tail -1
t0=$(date +%s)
(cd "$E" && timeout 300 python3 -I metrics_e2e.py /root/BornRok/src/net/PacketTable.cpp)
while [ $(( $(date +%s) - t0 )) -lt 310 ]; do sleep 5; done
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
for f in login char map; do echo "== $f"; grep -a 'METRIC\]' "$RUN/$f.out" | grep -v 'DCMETRIC\|PADMETRIC' | cut -c1-230; done
