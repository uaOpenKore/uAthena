#!/bin/bash
#
# ua-stop.sh <login|char|map> - stop a uAthena server gracefully.
#
# SIGTERM lets the server run do_final() (flush buffered SQL logs, save online
# chars, close inter-server links). SIGKILL only if it does not exit in time.
#
# map is multi-instance: ua-start.sh runs a SUPERVISOR that owns the N map
# children. We must signal the SUPERVISOR (it then stops its children and does
# NOT restart them) - killing the children directly would race the supervisor's
# restart logic. If no supervisor is running (children started by hand), we fall
# back to signalling the children directly.

SERVER="${1:-}"
if [ -z "$SERVER" ]; then
	echo "usage: $0 <login|char|map>" >&2
	exit 2
fi

BIN_DIR="${UA_BIN_DIR:-/opt/uathena/bin}"
GRACE="${UA_STOP_GRACE:-120}"   # seconds to wait for graceful exit (do_final)

# map child processes still alive? (match the binary comm exactly so the check
# never false-matches a shell/script that merely mentions "map-server")
map_children_alive() {
	pgrep -x map-server_sql >/dev/null 2>&1 || pgrep -x map-server >/dev/null 2>&1
}
# The running supervisor's pid, authoritatively from its PID file (the supervisor
# writes PID-map.pid = its own pid and removes it on clean exit). Validated against
# /proc to survive pid-reuse, and WITHOUT a cmdline pgrep (which would false-match
# any shell/script whose arguments happen to contain "ua-start.sh map").
map_supervisor_pid() {
	local f="${BIN_DIR}/PID-map.pid" p
	[ -r "$f" ] || return
	p=$(cat "$f" 2>/dev/null)
	[ -n "$p" ] && kill -0 "$p" 2>/dev/null || return
	tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q 'ua-start' && echo "$p"
}
sup_alive() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }

if [ "$SERVER" = "map" ]; then
	SUP=$(map_supervisor_pid)
	if [ -n "$SUP" ]; then
		echo "ua-stop: signalling map supervisor (pid $SUP) -> it stops its children"
		kill -TERM "$SUP" 2>/dev/null
	else
		CH=$( { pgrep -x map-server_sql; pgrep -x map-server; } 2>/dev/null )
		if [ -n "$CH" ]; then
			echo "ua-stop: no supervisor; SIGTERM map-server children directly"
			kill -TERM $CH 2>/dev/null
		fi
	fi

	# wait for the supervisor AND all children to be gone
	for _ in $(seq 1 "$GRACE"); do
		sup_alive "$SUP" && { sleep 1; continue; }
		map_children_alive || break
		sleep 1
	done

	if sup_alive "$SUP" || map_children_alive; then
		echo "ua-stop: map did not exit within ${GRACE}s, sending SIGKILL"
		sup_alive "$SUP" && kill -KILL "$SUP" 2>/dev/null
		kill -KILL $(pgrep -x map-server_sql) $(pgrep -x map-server) 2>/dev/null
	fi

	rm -f "${BIN_DIR}"/PID-map*.pid "${BIN_DIR}/.ua-map.lock"
	echo "ua-stop: map stopped."
	exit 0
fi

# ---- login / char (single server) ---------------------------------------
PIDS=$(pgrep -f "${SERVER}-server")
if [ -n "$PIDS" ]; then
	kill -TERM $PIDS
	for _ in $(seq 1 60); do
		pgrep -f "${SERVER}-server" >/dev/null || break
		sleep 1
	done
	PIDS=$(pgrep -f "${SERVER}-server")
	if [ -n "$PIDS" ]; then
		echo "${SERVER}-server did not exit within 60s, sending SIGKILL"
		kill -KILL $PIDS
	fi
fi

rm -f "${BIN_DIR}/PID-${SERVER}.pid"
