#!/bin/bash
# srv.sh start|stop <run-dir> -- SQL login/char/map servers of an audit run dir.
# Output goes to <run>/{login,char,map}.out (appended). Stop = SIGINT (servers save in do_final), SIGKILL after 20 s.
# Only processes whose working directory is <run> are ever signalled.
RUN="$2"
[ -d "$RUN" ] || { echo "no run dir $RUN"; exit 2; }
cd "$RUN" || exit 2

pid_of() {
	local p
	for p in $(pgrep -f "^\./$1-server_sql"); do
		[ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$RUN" ] && echo "$p"
	done
}

start_one() {
	[ -n "$(pid_of "$1")" ] && { echo "$1-server_sql already running"; return; }
	setsid nohup stdbuf -oL -eL "./$1-server_sql" >> "$RUN/$1.out" 2>&1 < /dev/null &
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
			echo "$1-server_sql ($p) did not stop on SIGINT, killing"
			kill -9 "$p"
		fi
	done
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
	for i in $(seq 1 240); do
		n=$(online_count)
		[ "$n" -gt "$before" ] && { echo "map online after ${i}s"; exit 0; }
		sleep 1
	done
	echo "map NOT online after 240s"; exit 1
	;;
stop)
	stop_one map; stop_one char; stop_one login
	echo stopped
	;;
esac
