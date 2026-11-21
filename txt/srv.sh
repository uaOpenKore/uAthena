#!/bin/bash
# srv.sh start|stop|stopchar|startchar <run-dir> -- TXT login/char/map servers of a c1 run dir.
# Output goes to <run>/{login,char,map}.out (appended, so restarts keep the whole history).
# Stop = SIGINT (the servers save their TXT files in do_final), SIGKILL only after 20 s.
# Only processes whose working directory is <run> are ever signalled.
RUN="$2"
[ -d "$RUN" ] || { echo "no run dir $RUN"; exit 2; }
cd "$RUN" || exit 2

pid_of() {
	local p
	for p in $(pgrep -x "$1-server"); do
		[ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$RUN" ] && echo "$p"
	done
}

start_one() {
	[ -n "$(pid_of "$1")" ] && { echo "$1-server already running"; return; }
	# not a subshell: the background job must not keep this script's stdout open
	setsid nohup stdbuf -oL -eL "./$1-server" >> "$RUN/$1.out" 2>&1 < /dev/null &
}

stop_one() {
	local p i
	for p in $(pid_of "$1"); do
		kill -INT "$p" 2>/dev/null
		for i in $(seq 1 40); do
			kill -0 "$p" 2>/dev/null || break
			sleep 0.5
		done
		if kill -0 "$p" 2>/dev/null; then
			echo "$1-server ($p) did not stop on SIGINT, killing"
			kill -9 "$p"
		fi
	done
}

wait_map_online() {
	# "Map Server is now online" is printed every time the map-server (re)connects to the char-server
	local before="$1" i n
	for i in $(seq 1 240); do
		n=$(grep -c "Map Server is now online" "$RUN/map.out" 2>/dev/null)
		[ "${n:-0}" -gt "$before" ] && { echo "map online after ${i}s"; return 0; }
		sleep 1
	done
	echo "map NOT online after 240s"; return 1
}

online_count() {
	local n
	n=$(grep -c "Map Server is now online" "$RUN/map.out" 2>/dev/null)
	echo "${n:-0}"
}

case "$1" in
start)
	before=$(online_count)
	start_one login; sleep 1
	start_one char; sleep 1
	start_one map
	wait_map_online "$before"
	;;
stop)
	stop_one map; stop_one char; stop_one login
	echo stopped
	;;
stopchar)
	stop_one char
	echo "char stopped"
	;;
startchar)
	before=$(online_count)
	start_one char
	wait_map_online "$before"
	;;
esac
