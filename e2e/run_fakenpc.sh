#!/bin/bash
# run_fakenpc.sh <run-dir>: TimerTest NPC (written by run_npctimer.sh), GM 99, fakenpc_e2e.py, check map.out.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
sed -n '/^cat > "\$RUN\/e2e_npc\/timertest.txt"/,/^NPC$/p' "$E/run_npctimer.sh" | sed '1d;$d' > "$RUN/e2e_npc/timertest.txt"
grep -q 'e2e_npc/timertest.txt' "$RUN/conf/import/map_conf.txt" || echo 'npc: e2e_npc/timertest.txt' >> "$RUN/conf/import/map_conf.txt"
$M -e "UPDATE login SET level=99 WHERE account_id=2000006"
bash "$E/srv.sh" stop "$RUN" > /dev/null; bash "$E/srv.sh" start "$RUN" | tail -1
cd "$E" && timeout 200 python3 -I fakenpc_e2e.py /root/BornRok/src/net/PacketTable.cpp
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
n=$(grep -a -c 'getnpctimer: Invalid NPC' "$RUN/map.out")
if [ "$n" -gt 0 ]; then echo "FAIL  FAKE_NPC was unloaded by @reloadscript ($n 'Invalid NPC')"; exit 1; fi
echo "ok    FAKE_NPC survives @reloadscript"; exit 0
