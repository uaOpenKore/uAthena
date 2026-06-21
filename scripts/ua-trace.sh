#!/bin/bash
#
# ua-trace.sh - snapshot a LIVE (e.g. hung or 100%-CPU) server for diagnosis.
#
# Crashes are caught automatically by ua-start.sh; this tool is for the other
# failure mode - a server that is stuck or spinning but has NOT died, so there
# is no core. It attaches gdb to grab an all-thread backtrace, and (if perf is
# available) records a short CPU profile so you can see where it is spinning.
# Both artifacts land in /opt/uathena/log and are timestamped, so repeated
# snapshots never overwrite each other.
#
# Usage:  ua-trace.sh <server> [perf-seconds]
#   <server>        login | char | map  (matches the "<server>-server" process)
#   [perf-seconds]  how long to sample with perf (default 5; 0 disables perf)
#
# gdb briefly stops the process while unwinding stacks (milliseconds); the perf
# sample is non-stop. Safe to run on a live server.

set -u

SERVER="${1:-}"
PERF_SECS="${2:-5}"
LOG_DIR="${UA_LOG_DIR:-/opt/uathena/log}"
TRACE_DIR="$LOG_DIR/trace"

if [ -z "$SERVER" ]; then
	echo "usage: $0 <login|char|map> [perf-seconds]" >&2
	exit 2
fi

PID=$(pgrep -f "${SERVER}-server" | head -1)
if [ -z "$PID" ]; then
	echo "ua-trace: no running '${SERVER}-server' process found" >&2
	exit 1
fi

mkdir -p "$TRACE_DIR"
# No Date.now() in scripts? This is a shell - use the real clock for filenames.
TS=$(date +%Y%m%d-%H%M%S)
BASE="$TRACE_DIR/${SERVER}-${TS}-pid${PID}"

echo "ua-trace: snapshotting ${SERVER}-server (pid $PID) -> $BASE.*"

# ---- gdb: all-thread backtrace of the live process -------------------------
if command -v gdb >/dev/null 2>&1; then
	gdb --batch --nx -p "$PID" \
		-ex "set pagination off" \
		-ex "set print pretty on" \
		-ex "echo \n========== ALL THREADS (live) ==========\n" \
		-ex "thread apply all bt full" \
		-ex "echo \n========== REGISTERS ==========\n" \
		-ex "info registers" \
		>"$BASE.gdb.txt" 2>&1
	echo "  gdb backtrace : $BASE.gdb.txt"
else
	echo "  gdb not installed - skipping backtrace" >&2
fi

# ---- perf: short CPU profile to see where it is spinning -------------------
if [ "$PERF_SECS" -gt 0 ] 2>/dev/null && command -v perf >/dev/null 2>&1; then
	# Frame-pointer call graphs are cheap and accurate because the server is
	# built with -fno-omit-frame-pointer.
	if perf record -F 99 -g --call-graph fp -o "$BASE.perf.data" -p "$PID" \
			-- sleep "$PERF_SECS" >/dev/null 2>&1; then
		perf report --stdio -i "$BASE.perf.data" >"$BASE.perf.txt" 2>/dev/null
		echo "  perf profile  : $BASE.perf.txt (raw: $BASE.perf.data)"
	else
		echo "  perf record failed (perf_event_paranoid? run as root) - skipping" >&2
	fi
fi

echo "ua-trace: done."
