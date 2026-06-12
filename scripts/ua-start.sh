#!/bin/bash
#
# ua-start.sh - launch a uAthena server with automatic crash capture and
#               optional CPU profiling.
#
# The servers leave SIGSEGV/SIGFPE/SIGILL/SIGBUS at SIG_DFL on purpose (see
# src/common/core.c) so the kernel writes a core on a crash. This wrapper
# makes that reliable and useful:
#
#   * forces  ulimit -c unlimited  and routes cores to $UA_LOG_DIR/core/ with a
#     unique per-crash name (pid+time+signal) so crashes never overwrite;
#   * on a crash, decodes the fresh core with gdb into a small, human-readable
#     backtrace report under $UA_LOG_DIR/crash/ (kept forever) and appends a
#     line to crash-history.log;
#   * optional: continuous perf profiling to $UA_LOG_DIR/perf/ (UA_PERF=1).
#
# Everything lands under $UA_LOG_DIR (default /opt/uathena/log, persistent
# disk), is timestamped, and survives restarts and segfaults. systemd's
# Restart=always brings the server back up after a captured crash.
#
# Usage:  ua-start.sh <login|char|map> [sql]
#
# Tunables (env):
#   UA_LOG_DIR        log root              (default /opt/uathena/log)
#   UA_BIN_DIR        dir of the binaries   (default .  -> WorkingDirectory)
#   UA_PERF=1         enable perf profiling (default off)
#   UA_PERF_FREQ      perf sample Hz        (default 99)
#   UA_CORE_KEEP      newest cores to keep  (default 10; reports never pruned)
#   UA_PERF_KEEP      newest perf.data keep (default 10)
#   UA_SET_COREPATTERN=0  do not touch kernel.core_pattern

set -u

SERVER="${1:-}"
if [ -z "$SERVER" ]; then
	echo "usage: $0 <login|char|map> [sql]" >&2
	exit 2
fi
uAtype=""
if [ "${2:-}" = "sql" ]; then
	uAtype="_sql"
fi

BIN_DIR="${UA_BIN_DIR:-.}"
LOG_DIR="${UA_LOG_DIR:-/opt/uathena/log}"
BIN="${BIN_DIR}/${SERVER}-server${uAtype}"
PID="${BIN_DIR}/PID-${SERVER}.pid"

CORE_DIR="$LOG_DIR/core"
CRASH_DIR="$LOG_DIR/crash"
PERF_DIR="$LOG_DIR/perf"
CRASH_INDEX="$CRASH_DIR/crash-history.log"
CONSOLE_LOG="$LOG_DIR/uA${SERVER}.log"

UA_PERF="${UA_PERF:-0}"
UA_PERF_FREQ="${UA_PERF_FREQ:-99}"
UA_CORE_KEEP="${UA_CORE_KEEP:-10}"
UA_PERF_KEEP="${UA_PERF_KEEP:-10}"
UA_SET_COREPATTERN="${UA_SET_COREPATTERN:-1}"

# Directory this script lives in, so we can find ua-crashdump.sh beside it.
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$CORE_DIR" "$CRASH_DIR" "$PERF_DIR"

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
signame() {
	case "$1" in
		3) echo SIGQUIT;; 4) echo SIGILL;;  5) echo SIGTRAP;; 6) echo SIGABRT;;
		7) echo SIGBUS;;  8) echo SIGFPE;; 11) echo SIGSEGV;; 31) echo SIGSYS;;
		*) echo "SIG$1";;
	esac
}

# Keep only the newest $3 files matching glob $2 in dir $1.
prune_keep() {
	local dir="$1" glob="$2" keep="$3" f
	ls -1t "$dir"/$glob 2>/dev/null | tail -n +$((keep + 1)) | while IFS= read -r f; do
		rm -f "$f"
	done
}

# Find the freshest core for pid $1 (our pattern embeds the pid; fall back to
# the cwd default 'core'/'core.<pid>' in case core_pattern could not be set).
find_core() {
	local pid="$1" c
	c=$(ls -1t "$CORE_DIR"/core.*."$pid".* 2>/dev/null | head -1)
	[ -n "$c" ] && { echo "$c"; return; }
	for c in "$BIN_DIR/core.$pid" "$BIN_DIR/core" "core.$pid" "core"; do
		[ -f "$c" ] && { echo "$c"; return; }
	done
}

capture_crash() {
	local sig="$1" pid="$2" name ts report core
	name=$(signame "$sig")
	ts=$(date +%Y%m%d-%H%M%S)
	report="$CRASH_DIR/${SERVER}-${ts}-pid${pid}-${name}.txt"

	{
		echo "==================================================================="
		echo " uAthena crash report"
		echo "   server : ${SERVER}-server${uAtype}"
		echo "   binary : $BIN"
		echo "   pid    : $pid"
		echo "   signal : $name ($sig)   exit code $((128 + sig))"
		echo "   time   : $(date '+%F %T %z')"
		echo "   host   : $(uname -a)"
		echo "==================================================================="
	} > "$report"

	# What the server printed right before dying.
	if [ -r "$CONSOLE_LOG" ]; then
		{ echo; echo "========== LAST 60 LINES OF CONSOLE LOG =========="
		  tail -n 60 "$CONSOLE_LOG"; } >> "$report"
	fi

	core=$(find_core "$pid")
	if [ -n "$core" ] && [ -r "$core" ]; then
		echo >> "$report"
		"$SELF_DIR/ua-crashdump.sh" "$BIN" "$core" >> "$report" 2>&1
		echo "ua-start: CRASH $name -> $report   [core: $core]" >&2
		prune_keep "$CORE_DIR" "core.*" "$UA_CORE_KEEP"
	elif command -v coredumpctl >/dev/null 2>&1; then
		# systemd-coredump owns the core (core_pattern is a pipe).
		echo >> "$report"
		echo "========== coredumpctl info ==========" >> "$report"
		coredumpctl info "$pid" >> "$report" 2>&1 || \
			echo "(coredumpctl had no record for pid $pid; try: coredumpctl gdb ${SERVER}-server${uAtype})" >> "$report"
		echo "ua-start: CRASH $name -> $report   [via coredumpctl]" >&2
	else
		echo >> "$report"
		echo "!! No core file found - backtrace unavailable." >> "$report"
		echo "!! Need 'ulimit -c unlimited' + a writable kernel.core_pattern (run as root)." >> "$report"
		echo "ua-start: CRASH $name -> $report   [NO CORE]" >&2
	fi

	echo "$(date '+%F %T')  ${SERVER}  $name  pid=$pid  report=$report" >> "$CRASH_INDEX"
}

# --------------------------------------------------------------------------
# double-start guard (same intent as before, via pgrep like ua-stop.sh)
# --------------------------------------------------------------------------
if pgrep -f "${SERVER}-server" >/dev/null 2>&1; then
	echo "${SERVER}-server process exists"
	exit 0
fi

if [ ! -x "$BIN" ]; then
	echo "ua-start: binary not found or not executable: $BIN" >&2
	exit 127
fi

# --------------------------------------------------------------------------
# make sure crashes produce a uniquely-named core in our log dir
# --------------------------------------------------------------------------
ulimit -c unlimited 2>/dev/null

if [ "$UA_SET_COREPATTERN" = "1" ]; then
	cur_pat=$(cat /proc/sys/kernel/core_pattern 2>/dev/null || echo "")
	case "$cur_pat" in
		'|'*)
			# A pipe handler (systemd-coredump/apport) owns cores - respect it;
			# capture_crash() will fall back to coredumpctl.
			: ;;
		"$CORE_DIR/core."*) : ;;   # already ours
		*)
			if ! printf '%s' "$CORE_DIR/core.%e.%p.%t.sig%s" \
					> /proc/sys/kernel/core_pattern 2>/dev/null; then
				echo "ua-start: WARN cannot set kernel.core_pattern (need root); using system default '$cur_pat'" >&2
			fi
			;;
	esac
fi

# --------------------------------------------------------------------------
# launch the server, capture its pid and exit status
# --------------------------------------------------------------------------
echo "ua-start: launching $BIN ($(date '+%F %T'))"
"$BIN" &
SPID=$!
echo "$SPID" > "$PID"

PERF_PID=""
PERF_DATA=""
shutdown_fwd() {
	[ -n "$PERF_PID" ] && kill -INT  "$PERF_PID" 2>/dev/null
	kill -TERM "$SPID" 2>/dev/null
}
trap shutdown_fwd TERM INT

# optional perf profiling (opt-in)
if [ "$UA_PERF" = "1" ]; then
	if command -v perf >/dev/null 2>&1; then
		para=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo 3)
		[ "$para" -gt 1 ] 2>/dev/null && echo 1 > /proc/sys/kernel/perf_event_paranoid 2>/dev/null
		PERF_DATA="$PERF_DIR/${SERVER}-$(date +%Y%m%d-%H%M%S)-pid${SPID}.perf.data"
		# Frame-pointer call graphs: cheap + accurate (-fno-omit-frame-pointer build).
		perf record -F "$UA_PERF_FREQ" -g --call-graph fp -o "$PERF_DATA" -p "$SPID" \
			>/dev/null 2>&1 &
		PERF_PID=$!
		echo "ua-start: perf profiling -> $PERF_DATA (${UA_PERF_FREQ}Hz)"
	else
		echo "ua-start: UA_PERF=1 but 'perf' not installed - skipping profiling" >&2
	fi
fi

# wait for the server; the trap may interrupt wait, so loop until it is gone.
wait "$SPID"; rc=$?
while kill -0 "$SPID" 2>/dev/null; do wait "$SPID"; rc=$?; done
trap - TERM INT

# finalize perf
if [ -n "$PERF_PID" ]; then
	kill -INT "$PERF_PID" 2>/dev/null
	wait "$PERF_PID" 2>/dev/null
	if [ -n "$PERF_DATA" ] && [ -s "$PERF_DATA" ]; then
		perf report --stdio -i "$PERF_DATA" > "${PERF_DATA%.data}.txt" 2>/dev/null && \
			echo "ua-start: perf report -> ${PERF_DATA%.data}.txt"
	fi
	prune_keep "$PERF_DIR" "*.perf.data" "$UA_PERF_KEEP"
fi

# --------------------------------------------------------------------------
# crash detection
# --------------------------------------------------------------------------
if [ "$rc" -gt 128 ]; then
	sig=$((rc - 128))
	case "$sig" in
		3|4|5|6|7|8|11|31)
			capture_crash "$sig" "$SPID" ;;
		15)
			echo "ua-start: ${SERVER} stopped by SIGTERM (graceful)" ;;
		9)
			echo "ua-start: ${SERVER} KILLED by SIGKILL (rc=137) - likely OOM; check 'journalctl -k' / dmesg" >&2
			echo "$(date '+%F %T')  ${SERVER}  SIGKILL/OOM?  pid=$SPID  report=(no core - killed)" >> "$CRASH_INDEX" ;;
		*)
			echo "ua-start: ${SERVER} exited via signal $sig (rc=$rc)" >&2 ;;
	esac
elif [ "$rc" -ne 0 ]; then
	echo "ua-start: ${SERVER} exited with code $rc" >&2
fi

rm -f "$PID"
exit "$rc"
