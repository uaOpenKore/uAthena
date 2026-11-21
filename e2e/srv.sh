#!/bin/bash
# srv.sh start|stop <run-dir>   -- start/stop login+char+map of an e2e run dir
RUN="$2"
case "$1" in
start)
	cd "$RUN" || exit 1
	for s in login char map; do
		setsid nohup stdbuf -oL -eL ./$s-server_sql > "$RUN/$s.out" 2>&1 < /dev/null &
		echo $! > "$RUN/$s.pid"
		sleep 2
	done
	# wait for the map-server to be ready (loads all maps + NPCs)
	for i in $(seq 1 180); do
		if grep -q "Map Server is now online\|Server is 'ready'" "$RUN/map.out" 2>/dev/null \
			&& grep -q "Map-Server.*connected\|Map-server .* connected\|map-server.*Logged in\|Connected to char-server" "$RUN/map.out" "$RUN/char.out" 2>/dev/null; then
			echo "ready after ${i}s"; exit 0
		fi
		sleep 1
	done
	echo "NOT ready after 180s"; exit 1
	;;
stop)
	for s in map char login; do
		[ -f "$RUN/$s.pid" ] && kill -INT "$(cat "$RUN/$s.pid")" 2>/dev/null
	done
	sleep 4
	for s in map char login; do
		[ -f "$RUN/$s.pid" ] && kill -9 "$(cat "$RUN/$s.pid")" 2>/dev/null; rm -f "$RUN/$s.pid"
	done
	# leftovers: only server processes whose working dir is THIS run dir
	for p in $(pgrep -f -- '-server_sql'); do
		[ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$RUN" ] && kill -9 "$p" 2>/dev/null
	done
	echo stopped
	;;
esac
