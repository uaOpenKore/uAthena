#!/bin/bash
# run_mobfreeze.sh <run-dir>: start login+char normally and the map-server under warp.so, run mobfreeze_e2e.py, stop.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; WF="$RUN/warp.ms"
M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
echo 0 > "$WF"
mkdir -p "$RUN/e2e_npc"
printf 'new_1-1,114,42,3,3\tmonster\tZombie\t1015,6,2000,1000\nnew_1-1,0,0,0,0\tmonster\tPoring\t1002,20,2000,1000\n' > "$RUN/e2e_npc/mobfreeze.txt"
grep -q 'e2e_npc/mobfreeze.txt' "$RUN/conf/import/map_conf.txt" || echo 'npc: e2e_npc/mobfreeze.txt' >> "$RUN/conf/import/map_conf.txt"
$M -e "UPDATE login SET level=99 WHERE account_id=2000006; UPDATE \`char\` SET last_map='new_zone01', last_x=56, last_y=100 WHERE char_id=150003"
bash "$E/srv.sh" stop "$RUN" > /dev/null
cd "$RUN" || exit 1
for s in login char; do
	setsid nohup stdbuf -oL -eL ./$s-server_sql > "$RUN/$s.out" 2>&1 < /dev/null &
	echo $! > "$RUN/$s.pid"; sleep 2
done
WARP_FILE="$WF" LD_PRELOAD="$E/warp.so" setsid nohup stdbuf -oL -eL ./map-server_sql > "$RUN/map.out" 2>&1 < /dev/null &
echo $! > "$RUN/map.pid"
for i in $(seq 1 120); do grep -q "Map Server is now online\|Server is 'ready'" "$RUN/map.out" 2>/dev/null && break; sleep 1; done
sleep 8
cd "$E" && timeout 600 python3 -I mobfreeze_e2e.py "$RUN" /root/BornRok/src/net/PacketTable.cpp "$WF" $2; rc=$?
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
grep -a -c 'loop_stall' "$RUN/map.out" | sed 's/^/    map loop_stall lines: /'
exit $rc
