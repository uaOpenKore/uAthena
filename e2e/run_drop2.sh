#!/bin/bash
# run_drop2.sh <bin-dir> [rounds]: run-drop (login, char, map#1 without prontera) + run-drop2 (map#2: prontera,
# port 5122) with the binaries of <bin-dir>; dropuaf2_e2e.py; stop everything.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
D=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/run-drop
D2=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/run-drop2
BIN="$1"; ROUNDS="${2:-3}"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
cp -p "$BIN"/login-server_sql "$BIN"/char-server_sql "$BIN"/map-server_sql "$D"/ && cp -p "$BIN"/map-server_sql "$D2"/
$M -e "UPDATE login SET level=99 WHERE account_id=2000006; DELETE FROM inventory WHERE char_id IN (150003,150004) AND nameid<>714"
bash "$E/srv.sh" stop "$D" > /dev/null 2>&1
bash "$E/srv.sh" start "$D" | tail -1
( cd "$D2" && setsid nohup stdbuf -oL -eL ./map-server_sql > "$D2/map.out" 2>&1 < /dev/null & echo $! > "$D2/map.pid" )
for i in $(seq 1 120); do
	grep -q "Map Server is now online\|Server is 'ready'" "$D2/map.out" 2>/dev/null && break
	sleep 1
done
echo "map#2: $(grep -a -m1 "Map Server is now online\|Server is 'ready'" "$D2/map.out" | cut -c1-60) after ${i}s; char-server sees $(grep -ac 'Map-Server.*connected\|map-server.*connected' "$D/char.out") map-server connection(s)"
GDBP=""
if [ -n "$DROP_DELAY_MS" ]; then
	# Widen the race window like warp.so does for the clock: gdb adds DROP_DELAY_MS to the tick the delayed-drop timer
	# is set for (logic unchanged). Here the char-server's save makes the map-server change ack come after 500 ms.
	MP=""; for p in $(pgrep -f map-server_sql); do [ "$(readlink /proc/$p/cwd)" = "$D" ] && MP=$p; done
	printf 'set pagination off\nset confirm off\nbreak add_timer if func == mob_delay_item_drop\ncommands\n  silent\n  set var tick = tick + %d\n  printf "drop timer +%d ms\\n"\n  continue\nend\ncontinue\n' "$DROP_DELAY_MS" "$DROP_DELAY_MS" > "$D/delay.gdb"
	gdb -p "$MP" -x "$D/delay.gdb" > "$D/delay-gdb.log" 2>&1 &
	GDBP=$!
	sleep 4
fi
(cd "$E" && timeout 600 python3 -I dropuaf2_e2e.py /root/BornRok/src/net/PacketTable.cpp "$ROUNDS"); rc=$?
if [ -n "$GDBP" ]; then kill -INT "$GDBP" 2>/dev/null; sleep 1; kill "$GDBP" 2>/dev/null; sleep 1; echo "gdb: $(grep -c 'drop timer +' "$D/delay-gdb.log") drop timer(s) delayed"; fi
[ -f "$D2/map.pid" ] && kill -INT "$(cat "$D2/map.pid")" 2>/dev/null
for p in $(pgrep -f map-server_sql); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$D2" ] && kill -INT "$p" 2>/dev/null; done
sleep 3
for p in $(pgrep -f map-server_sql); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$D2" ] && kill -9 "$p" 2>/dev/null; done
rm -f "$D2/map.pid"
bash "$E/srv.sh" stop "$D" > /dev/null 2>&1
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
exit $rc
