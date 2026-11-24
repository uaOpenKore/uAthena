#!/bin/bash
#
# ua-start.sh - launch a uAthena server with automatic crash capture and
#               optional CPU profiling.
#
# login / char : a single server, supervised with crash capture + perf.
# map          : a MULTI-map supervisor. It asks ua-mapcount.sh how many
#                map-servers to run (from CPU thread count + confN dirs) and
#                launches each one pinned to its own CPU pair, with its OWN
#                config dir (confN), its OWN console log (uAmapN.log), its OWN
#                PID/perf/crash-report, and restarts any that die (back-off
#                guarded). One SIGTERM stops them all gracefully (do_final).
#
# The servers leave SIGSEGV/SIGFPE/... at SIG_DFL (src/common/core.c) so the
# kernel writes a core on a crash; this wrapper decodes it into a backtrace
# report under $UA_LOG_DIR/crash/ and (UA_PERF=1) records a perf profile.
#
# Log rotation (S. 2026-11-19): every launch of a server starts a new piece of
# its console log and a new perf dump, and so does every UA_ROTATE_HOURS of
# uptime - the server keeps running. The live log keeps its name (uAmap1.log,
# uAchar.log ...); a closed piece is <name>-<start>.log, with the stamp its
# perf dump carries too: uAmap1-20261119-030123.log next to
# map1-20261119-030123-pid<pid>.perf.data/.txt. The map supervisor does the
# same with its own uAmap.log and the monitor's uamon.log. Old pieces go with
# clean_logs.sh.
#
# Usage:  ua-start.sh <login|char|map> [sql]
#
# Tunables (env):
#   UA_LOG_DIR        log root              (default /opt/uathena/log)
#   UA_BIN_DIR        dir of the binaries   (default .  -> WorkingDirectory);
#                     also where conf/ and confN/ live
#   UA_PERF=1         enable perf profiling (default on; for map it profiles
#                     EVERY instance - heavy with many servers, set 0 in prod)
#   UA_PERF_FREQ      perf sample Hz        (default 99)
#   UA_CORE_KEEP      cores to keep after decoding (default 0)
#   UA_PERF_KEEP      newest perf.data keep (default 10)
#   UA_SET_COREPATTERN=0  do not touch kernel.core_pattern
#   UA_FORCE_THREADS  override CPU thread count (caps map-server count)
#   UA_DRYRUN=1       (map) print the launch plan and exit, launch nothing
#   UA_ROTATE_HOURS   new log piece + perf dump after this many hours of uptime
#                     (default 24; 0 = no rotation at all, the logs just grow)
#   UA_ROTATE_SECS    the same in seconds, overrides UA_ROTATE_HOURS (tests)
#   UA_ROTATE_TICK    seconds between the uptime checks (default 60)

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

CORE_DIR="$LOG_DIR/core"
CRASH_DIR="$LOG_DIR/crash"
PERF_DIR="$LOG_DIR/perf"
CRASH_INDEX="$CRASH_DIR/crash-history.log"

UA_PERF="${UA_PERF:-1}"
UA_PERF_FREQ="${UA_PERF_FREQ:-99}"
UA_CORE_KEEP="${UA_CORE_KEEP:-0}"
UA_PERF_KEEP="${UA_PERF_KEEP:-10}"
UA_SET_COREPATTERN="${UA_SET_COREPATTERN:-1}"
UA_DRYRUN="${UA_DRYRUN:-0}"
UA_ROTATE_HOURS="${UA_ROTATE_HOURS:-24}"
UA_ROTATE_TICK="${UA_ROTATE_TICK:-60}"
case "$UA_ROTATE_HOURS" in
	''|*[!0-9]*) echo "ua-start: WARN UA_ROTATE_HOURS='$UA_ROTATE_HOURS' is not whole hours - using 24" >&2
	             UA_ROTATE_HOURS=24 ;;
esac
ROTATE_SECS="${UA_ROTATE_SECS:-$((UA_ROTATE_HOURS * 3600))}"
case "$ROTATE_SECS" in ''|*[!0-9]*) ROTATE_SECS=$((UA_ROTATE_HOURS * 3600)) ;; esac
case "$UA_ROTATE_TICK" in ''|0|*[!0-9]*) UA_ROTATE_TICK=60 ;; esac

# map supervisor: restart back-off (avoid a hot crash-loop)
MIN_UPTIME=10   # a child that dies < this many seconds after start is "flapping"
BACKOFF=5       # ... wait this long before restarting it

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

prune_keep() {
	local dir="$1" glob="$2" keep="$3" f
	ls -1t "$dir"/$glob 2>/dev/null | tail -n +$((keep + 1)) | while IFS= read -r f; do
		rm -f "$f"
	done
}

find_core() {
	local pid="$1" c
	c=$(ls -1t "$CORE_DIR"/core.*."$pid".* 2>/dev/null | head -1)
	[ -n "$c" ] && { echo "$c"; return; }
	for c in "$BIN_DIR/core.$pid" "$BIN_DIR/core" "core.$pid" "core"; do
		[ -f "$c" ] && { echo "$c"; return; }
	done
}

# capture_crash <sig> <pid> <tag> <console_log>
#   tag         : short id for the report file + header (e.g. login / map3)
#   console_log : that instance's console log to tail into the report
capture_crash() {
	local sig="$1" pid="$2" tag="$3" console="$4" name ts report core
	name=$(signame "$sig")
	ts=$(date +%Y%m%d-%H%M%S)
	report="$CRASH_DIR/${tag}-${ts}-pid${pid}-${name}.txt"

	{
		echo "==================================================================="
		echo " uAthena crash report"
		echo "   server : ${tag} (${SERVER}-server${uAtype})"
		echo "   binary : $BIN"
		echo "   pid    : $pid"
		echo "   signal : $name ($sig)   exit code $((128 + sig))"
		echo "   time   : $(date '+%F %T %z')"
		echo "   host   : $(uname -a)"
		echo "==================================================================="
	} > "$report"

	if [ -r "$console" ]; then
		{ echo; echo "========== LAST 60 LINES OF CONSOLE LOG ($console) =========="
		  tail -n 60 "$console"; } >> "$report"
	fi

	core=$(find_core "$pid")
	if [ -n "$core" ] && [ -r "$core" ]; then
		echo >> "$report"
		if "$SELF_DIR/ua-crashdump.sh" "$BIN" "$core" >> "$report" 2>&1 && command -v gdb >/dev/null 2>&1; then
			prune_keep "$CORE_DIR" "core.*" "$UA_CORE_KEEP"
		else
			# not decoded (no gdb, or gdb failed): keep the core -- with the binary it is the only way to the crash
			# later (S. 2026-11-24: map1's core was deleted undecoded, gdb was not installed). A copy of the binary
			# goes next to it, since the next deploy replaces the binary the core belongs to.
			cp -p "$BIN" "$core.bin" 2>/dev/null
			echo "!! core NOT decoded - kept with its binary: $core (+ .bin). Install gdb and run scripts/ua-crashdump.sh $core.bin $core" >> "$report"
		fi
		if [ -e "$core" ]; then
			echo "ua-start: CRASH $tag $name -> $report   [core kept: $core]" >&2
		else
			echo "ua-start: CRASH $tag $name -> $report   [backtrace saved, core deleted]" >&2
		fi
	elif command -v coredumpctl >/dev/null 2>&1; then
		echo >> "$report"
		echo "========== coredumpctl info ==========" >> "$report"
		coredumpctl info "$pid" >> "$report" 2>&1 || \
			echo "(coredumpctl had no record for pid $pid)" >> "$report"
		echo "ua-start: CRASH $tag $name -> $report   [via coredumpctl]" >&2
	else
		echo >> "$report"
		echo "!! No core file found - backtrace unavailable." >> "$report"
		echo "ua-start: CRASH $tag $name -> $report   [NO CORE]" >&2
	fi

	echo "$(date '+%F %T')  ${tag}  $name  pid=$pid  report=$report" >> "$CRASH_INDEX"
}

start_perf() {  # start_perf <pid> <tag> [stamp] ; echoes "perfpid|perfdata" or empty
	[ "$UA_PERF" = "1" ] || return 0
	command -v perf >/dev/null 2>&1 || { echo "ua-start: UA_PERF=1 but 'perf' not installed" >&2; return 0; }
	local pid="$1" tag="$2" para data ppid
	para=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo 3)
	[ "$para" -gt 1 ] 2>/dev/null && echo 1 > /proc/sys/kernel/perf_event_paranoid 2>/dev/null
	data="$PERF_DIR/${tag}-${3:-$(date +%Y%m%d-%H%M%S)}-pid${pid}.perf.data"
	perf record -F "$UA_PERF_FREQ" -g --call-graph fp -o "$data" -p "$pid" >/dev/null 2>&1 &
	ppid=$!
	echo "${ppid}|${data}"
}

alive() {  # alive <pid>: running, not a zombie waiting to be reaped
	local st
	st=$(ps -o stat= -p "$1" 2>/dev/null) && [ -n "$st" ] && [ "${st#Z}" = "$st" ]
}

finalize_perf() {  # finalize_perf <perfpid> <perfdata> [bg] ; bg = write the report in the background, niced
	local ppid="$1" data="$2" n=0
	[ -n "$ppid" ] || return 0
	kill -INT "$ppid" 2>/dev/null
	# start_perf runs inside $(...), so the recorder is not this shell's child and `wait` returns at once:
	# wait until it has finished its file (bounded), or the report reads a half-written perf.data.
	while alive "$ppid" && [ "$n" -lt 600 ]; do sleep 0.1; n=$((n + 1)); done
	if [ -n "$data" ] && [ -s "$data" ]; then
		if [ "${3:-}" = "bg" ]; then
			{ nice -n 19 perf report --stdio -i "$data" > "${data%.data}.txt" 2>/dev/null && \
				echo "ua-start: perf report -> ${data%.data}.txt"; } &
		else
			perf report --stdio -i "$data" > "${data%.data}.txt" 2>/dev/null && \
				echo "ua-start: perf report -> ${data%.data}.txt"
		fi
	fi
	prune_keep "$PERF_DIR" "*.perf.data" "$UA_PERF_KEEP"
}

# --------------------------------------------------------------------------
# log rotation (see the header). A piece of console log runs from a launch or a
# cut to the next one.
# --------------------------------------------------------------------------
STAMP_RE='[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}'

# piece_stamp <log>: YYYYMMDD-HHMMSS the piece in <log> started at. That is the
# time in its first "ua-start: ... (DATE)" line (every launch and every cut
# writes one) or in its first "DATE ..." line (uamon.log); else its last write.
piece_stamp() {
	local t
	t=$(head -n 200 -- "$1" 2>/dev/null | grep -a -m1 -E "^ua-start: .*\($STAMP_RE\)|^$STAMP_RE " | \
		grep -oE "$STAMP_RE" | head -n 1)
	if [ -n "$t" ]; then
		t=${t//-/}; t=${t//:/}; echo "${t/ /-}"
	else
		date -r "$1" +%Y%m%d-%H%M%S
	fi
}

# cut_log <log> [stamp]: close the piece in <log> as <log minus .log>-<stamp>.log
# (stamp: piece_stamp) and empty <log>; echoes the new file. The writers keep
# the file open and go on at its start: they all append (>>, systemd append:).
# A line written in the instant between the last copy and the truncate is
# lost. A missing or empty log is left alone; so is the log if the copy fails.
cut_log() {
	local log="$1" stamp="${2:-}" dst n=1 fd mt
	[ -s "$log" ] || return 0
	[ -n "$stamp" ] || stamp=$(piece_stamp "$log")
	dst="${log%.log}-${stamp}.log"
	while [ -e "$dst" ]; do n=$((n + 1)); dst="${log%.log}-${stamp}-${n}.log"; done
	exec {fd}<"$log" || return 1
	# the bulk, then what was written meanwhile, then empty the log at once
	if ! { cat <&"$fd" > "$dst" && mt=$(stat -c %Y -- "$log") && cat <&"$fd" >> "$dst"; }; then
		exec {fd}<&-
		rm -f -- "$dst"
		echo "ua-start: WARN could not copy $log to $dst - the log goes on unrotated" >&2
		return 1
	fi
	: > "$log"
	exec {fd}<&-
	touch -d "@$mt" -- "$dst"   # the piece's own last write: clean_logs.sh ages it by that
	echo "$dst"
}

# Block until MariaDB/MySQL accepts connections, so a boot or restart that races
# ahead of the DB does not fail with "Can't connect to server (115)" (which, mid
# do_final, silently loses char saves). Only for the _sql build. Best-effort and
# strictly bounded: after UA_DB_WAIT_SECS we launch anyway (Restart=always retries).
#   UA_WAIT_DB=0        disable this wait
#   UA_DB_HOST/PORT     where to probe   (default 127.0.0.1:3306 - matches conf)
#   UA_DB_WAIT_SECS     max seconds      (default 60)
wait_for_db() {
	[ "$uAtype" = "_sql" ] || return 0
	[ "${UA_WAIT_DB:-1}" = "1" ] || return 0
	command -v mysqladmin >/dev/null 2>&1 || { echo "ua-start: mysqladmin not found - skipping DB wait" >&2; return 0; }
	local host="${UA_DB_HOST:-127.0.0.1}" port="${UA_DB_PORT:-3306}"
	local timeout="${UA_DB_WAIT_SECS:-60}" waited=0 out
	while [ "$waited" -lt "$timeout" ]; do
		# "mysqld is alive" = up; "Access denied" = up too (auth != reachability).
		out=$(mysqladmin --protocol=tcp -h "$host" -P "$port" --connect-timeout=2 ping 2>&1)
		if echo "$out" | grep -qiE "alive|denied"; then
			[ "$waited" -gt 0 ] && echo "ua-start: MariaDB reachable after ${waited}s"
			return 0
		fi
		sleep 2; waited=$((waited + 2))
	done
	echo "ua-start: WARN MariaDB not reachable after ${timeout}s - launching anyway" >&2
}

setup_core_pattern() {
	ulimit -c unlimited 2>/dev/null
	[ "$UA_SET_COREPATTERN" = "1" ] || return 0
	local cur_pat
	cur_pat=$(cat /proc/sys/kernel/core_pattern 2>/dev/null || echo "")
	case "$cur_pat" in
		'|'*) : ;;
		"$CORE_DIR/core."*) : ;;
		*)
			printf '%s' "$CORE_DIR/core.%e.%p.%t.sig%s" > /proc/sys/kernel/core_pattern 2>/dev/null || \
				echo "ua-start: WARN cannot set kernel.core_pattern (need root); using '$cur_pat'" >&2
			;;
	esac
}

# --------------------------------------------------------------------------
# binary check (double-start guards are per-path below: pgrep for login/char,
# flock for the map supervisor - a cmdline pgrep would false-match anything that
# merely mentions "map-server", e.g. a shell or this script's own arguments)
# --------------------------------------------------------------------------
if [ ! -x "$BIN" ]; then
	echo "ua-start: binary not found or not executable: $BIN" >&2
	exit 127
fi

# ==========================================================================
# single-server path (login / char) - unchanged behaviour
# ==========================================================================
run_single() {
	if pgrep -f "${SERVER}-server${uAtype}" >/dev/null 2>&1; then
		echo "${SERVER}-server process exists"
		exit 0
	fi
	local PID="${BIN_DIR}/PID-${SERVER}.pid"
	local CONSOLE_LOG="$LOG_DIR/uA${SERVER}.log"
	# a new piece of console log for every launch: close what the previous run left in it
	if [ "$ROTATE_SECS" -gt 0 ]; then
		local prev
		prev=$(cut_log "$CONSOLE_LOG")
		[ -n "$prev" ] && echo "ua-start: previous log piece -> $prev" >> "$CONSOLE_LOG"
	fi
	setup_core_pattern
	wait_for_db

	local PIECE_AT PIECE_TS
	PIECE_AT=$(date +%s); PIECE_TS=$(date -d "@$PIECE_AT" +%Y%m%d-%H%M%S)
	echo "ua-start: launching $BIN ($(date -d "@$PIECE_AT" '+%F %T'))" | tee -a "$CONSOLE_LOG"
	# Redirect the binary's console straight to uAlogin.log / uAchar.log, exactly like the map
	# supervisor does for uAmapN.log. Previously login/char were launched bare ("$BIN" &) and relied
	# on systemd StandardOutput=append: -- which silently produces NO file on systemd < v240 (no
	# 'append:' support), so uAchar.log / uAlogin.log never appeared while uAmapN.log always did (the
	# map path redirects in-shell). This also makes capture_crash's `tail "$CONSOLE_LOG"` actually work.
	"$BIN" >> "$CONSOLE_LOG" 2>&1 &
	local SPID=$!
	echo "$SPID" > "$PID"

	local PERF_PID="" PERF_DATA="" pr
	pr=$(start_perf "$SPID" "$SERVER" "$PIECE_TS"); PERF_PID="${pr%%|*}"; PERF_DATA="${pr#*|}"
	[ "$pr" = "$PERF_PID" ] && PERF_DATA=""   # no '|' -> perf off
	[ -n "$PERF_DATA" ] && echo "ua-start: perf profiling -> $PERF_DATA (${UA_PERF_FREQ}Hz)"

	# cut_piece <now>: new log piece + perf dump after ROTATE_SECS of uptime; the server keeps running
	cut_piece() {
		local now="$1" stamp prev pr oldp="$PERF_PID" oldd="$PERF_DATA"
		stamp=$(date -d "@$now" +%Y%m%d-%H%M%S)
		# the new recording starts before the old one stops: no hole in the profile
		pr=$(start_perf "$SPID" "$SERVER" "$stamp"); PERF_PID="${pr%%|*}"; PERF_DATA="${pr#*|}"
		[ "$pr" = "$PERF_PID" ] && PERF_DATA=""
		prev=$(cut_log "$CONSOLE_LOG" "$PIECE_TS")
		echo "ua-start: ${SERVER} new log piece ($(date -d "@$now" '+%F %T')), previous piece -> ${prev:-(empty)}" \
			>> "$CONSOLE_LOG"
		[ -n "$PERF_DATA" ] && echo "ua-start: perf profiling -> $PERF_DATA (${UA_PERF_FREQ}Hz)"
		PIECE_AT=$now; PIECE_TS=$stamp
		finalize_perf "$oldp" "$oldd" bg
	}

	local STOPPING=0 TICK_PID=""
	shutdown_fwd() {
		STOPPING=1
		[ -n "$TICK_PID" ] && kill "$TICK_PID" 2>/dev/null
		[ -n "$PERF_PID" ] && kill -INT "$PERF_PID" 2>/dev/null
		kill -TERM "$SPID" 2>/dev/null
	}
	trap shutdown_fwd TERM INT

	# Wait for the server. A ticker child wakes us every UA_ROTATE_TICK s for the uptime check; a background
	# perf report finishing wakes us too.
	local rc dpid now
	[ "$ROTATE_SECS" -gt 0 ] && { sleep "$UA_ROTATE_TICK" & TICK_PID=$!; }
	while :; do
		dpid=""
		wait -n -p dpid; rc=$?
		dpid=${dpid:-}   # wait unsets it when a signal (the TERM trap) cut the wait short
		[ "$dpid" = "$SPID" ] && break
		if [ -n "$dpid" ] && [ "$dpid" = "$TICK_PID" ]; then
			TICK_PID=""
			[ "$STOPPING" -eq 1 ] && continue
			now=$(date +%s)
			[ $((now - PIECE_AT)) -ge "$ROTATE_SECS" ] && cut_piece "$now"
			sleep "$UA_ROTATE_TICK" & TICK_PID=$!
			continue
		fi
		[ -z "$dpid" ] && [ "$rc" -eq 127 ] && break   # no child left (cannot happen while the server runs)
	done
	trap - TERM INT
	[ -n "$TICK_PID" ] && kill "$TICK_PID" 2>/dev/null

	finalize_perf "$PERF_PID" "$PERF_DATA"
	wait   # reports of earlier pieces still being written

	if [ "$rc" -gt 128 ]; then
		local sig=$((rc - 128))
		case "$sig" in
			3|4|5|6|7|8|11|31) capture_crash "$sig" "$SPID" "$SERVER" "$CONSOLE_LOG" ;;
			15) echo "ua-start: ${SERVER} stopped by SIGTERM (graceful)" ;;
			9)  echo "ua-start: ${SERVER} KILLED (SIGKILL/OOM) - check dmesg" >&2
			    echo "$(date '+%F %T')  ${SERVER}  SIGKILL/OOM?  pid=$SPID" >> "$CRASH_INDEX" ;;
			*)  echo "ua-start: ${SERVER} exited via signal $sig (rc=$rc)" >&2 ;;
		esac
	elif [ "$rc" -ne 0 ]; then
		echo "ua-start: ${SERVER} exited with code $rc" >&2
	fi
	rm -f "$PID"
	exit "$rc"
}

# ==========================================================================
# multi-map supervisor path
# ==========================================================================
run_map_supervisor() {
	# Single-supervisor guard via an exclusive lock (robust: does not depend on
	# matching a command line). systemd already prevents a double ExecStart; this
	# covers manual invocation. Skipped in dry-run.
	if [ "$UA_DRYRUN" != "1" ] && command -v flock >/dev/null 2>&1; then
		# The braces matter: a bare `exec 9>lock 2>/dev/null` makes BOTH redirections permanent, and the
		# supervisor's stderr - CRASH reports, flapping, restarting map#N - went to /dev/null.
		{ exec 9>"${BIN_DIR}/.ua-map.lock"; } 2>/dev/null && \
		if ! flock -n 9; then
			echo "ua-start: map supervisor already running (lock held)"
			exit 0
		fi
	fi

	# shellcheck source=ua-mapcount.sh
	. "$SELF_DIR/ua-mapcount.sh"

	local K; K=$(ua_map_count)
	# This supervisor's own log (systemd StandardOutput) and the load monitor's (cron, scripts/cron) get new
	# pieces with the supervisor: at its start and every ROTATE_SECS.
	local SUP_LOG="$LOG_DIR/uAmap.log" MON_LOG="$LOG_DIR/uamon.log" SUP_AT SUP_TS
	SUP_AT=$(date +%s); SUP_TS=$(date -d "@$SUP_AT" +%Y%m%d-%H%M%S)
	if [ "$ROTATE_SECS" -gt 0 ] && [ "$UA_DRYRUN" != "1" ]; then
		cut_log "$SUP_LOG" > /dev/null
		cut_log "$MON_LOG" > /dev/null
	fi
	echo "ua-start: multi-map supervisor: $K map-server(s) (threads=$(ua_threads), confN=$(ua_conf_max))" \
		"($(date -d "@$SUP_AT" '+%F %T'))"

	declare -A MAP_PID PID_INST START_AT PERF_PID PERF_DATA CONSOLE CONFDIR CORES PIECE_AT PIECE_TS

	build_cfg_args() {  # build_cfg_args <confdir> ; sets global CFG_ARGS array
		local d="$1"
		CFG_ARGS=( --map_config "$d/map_athena.conf" )
		local f
		for f in battle_config:battle_athena.conf atcommand_config:atcommand_athena.conf \
		         charcommand_config:charcommand_athena.conf script_config:script_athena.conf \
		         msg_config:msg_athena.conf grf_path_file:grf-files.txt; do
			local flag="${f%%:*}" file="${f#*:}"
			[ -f "$BIN_DIR/$d/$file" ] && CFG_ARGS+=( "--$flag" "$d/$file" )
		done
	}

	launch_instance() {  # launch_instance <i>
		local i="$1" cores confdir console pr
		cores=$(ua_cores_for "$i")
		confdir=$(ua_confdir_for "$i")
		console="$LOG_DIR/uAmap${i}.log"
		CORES[$i]="$cores"; CONFDIR[$i]="$confdir"; CONSOLE[$i]="$console"
		if [ -z "$confdir" ] || [ ! -f "$BIN_DIR/$confdir/map_athena.conf" ]; then
			echo "ua-start: map#$i: no $confdir/map_athena.conf - skipping" >&2
			return 1
		fi
		build_cfg_args "$confdir"

		local -a PIN=()
		[ -n "$cores" ] && PIN=( taskset -c "$cores" )

		if [ "$UA_DRYRUN" = "1" ]; then
			echo "DRYRUN map#$i: ${PIN[*]} $BIN ${CFG_ARGS[*]}  >> $console  (cores=${cores:-all})"
			return 0
		fi

		# a new piece of console log for every launch: close what the previous run (or crash) left in it
		local now stamp prev
		now=$(date +%s); stamp=$(date -d "@$now" +%Y%m%d-%H%M%S)
		if [ "$ROTATE_SECS" -gt 0 ]; then
			prev=$(cut_log "$console" "${PIECE_TS[$i]:-}")
			[ -n "$prev" ] && echo "ua-start: map#$i previous log piece -> $prev"
		fi
		echo "ua-start: map#$i launch (cores=${cores:-all} conf=$confdir) -> $console ($(date -d "@$now" '+%F %T'))" \
			| tee -a "$console"
		# UA_MAP_INSTANCE: the map-server writes its abnormal packets to log/attack-map<N>.log
		UA_MAP_INSTANCE="$i" "${PIN[@]}" "$BIN" "${CFG_ARGS[@]}" >> "$console" 2>&1 &
		local pid=$!
		MAP_PID[$i]=$pid; PID_INST[$pid]=$i; START_AT[$i]=$now; PIECE_AT[$i]=$now; PIECE_TS[$i]=$stamp
		echo "$pid" > "${BIN_DIR}/PID-map${i}.pid"

		pr=$(start_perf "$pid" "map${i}" "$stamp")
		if [ -n "$pr" ] && [ "$pr" != "${pr%%|*}" ]; then
			PERF_PID[$i]="${pr%%|*}"; PERF_DATA[$i]="${pr#*|}"
			echo "ua-start: map#$i perf -> ${PERF_DATA[$i]}"
		fi
		return 0
	}

	cut_instance() {  # cut_instance <i> <now>: new log piece + perf dump for map#i; the server keeps running
		local i="$1" now="$2" stamp prev pr oldp="${PERF_PID[$1]:-}" oldd="${PERF_DATA[$1]:-}"
		stamp=$(date -d "@$now" +%Y%m%d-%H%M%S)
		unset 'PERF_PID[$i]' 'PERF_DATA[$i]'
		# the new recording starts before the old one stops: no hole in the profile
		pr=$(start_perf "${MAP_PID[$i]}" "map${i}" "$stamp")
		if [ -n "$pr" ] && [ "$pr" != "${pr%%|*}" ]; then
			PERF_PID[$i]="${pr%%|*}"; PERF_DATA[$i]="${pr#*|}"
			echo "ua-start: map#$i perf -> ${PERF_DATA[$i]}"
		fi
		prev=$(cut_log "${CONSOLE[$i]}" "${PIECE_TS[$i]}")
		echo "ua-start: map#$i new log piece ($(date -d "@$now" '+%F %T')), previous piece -> ${prev:-(empty)}" \
			| tee -a "${CONSOLE[$i]}"
		PIECE_AT[$i]=$now; PIECE_TS[$i]=$stamp
		finalize_perf "$oldp" "$oldd" bg
	}

	cut_supervisor() {  # cut_supervisor <now>: the same for this supervisor's own log and uamon.log
		local now="$1" prev
		prev=$(cut_log "$SUP_LOG" "$SUP_TS")
		cut_log "$MON_LOG" "$SUP_TS" > /dev/null
		SUP_AT=$now; SUP_TS=$(date -d "@$now" +%Y%m%d-%H%M%S)
		echo "ua-start: map supervisor new log piece ($(date -d "@$now" '+%F %T')), previous piece -> ${prev:-(empty)}"
	}

	cut_due() {  # the uptime check: cut whatever has run ROTATE_SECS since its launch or its last cut
		local now i
		now=$(date +%s)
		[ $((now - SUP_AT)) -ge "$ROTATE_SECS" ] && cut_supervisor "$now"
		for i in "${!MAP_PID[@]}"; do
			[ "$shutting_down" -eq 0 ] || return 0   # a stop came in: the shutdown takes it from here
			[ $((now - ${PIECE_AT[$i]:-$now})) -ge "$ROTATE_SECS" ] && cut_instance "$i" "$now"
		done
	}

	# ---- dry run: print the plan and exit -------------------------------
	if [ "$UA_DRYRUN" = "1" ]; then
		local i
		for i in $(seq 1 "$K"); do launch_instance "$i"; done
		echo "ua-start: DRYRUN done (nothing launched)"
		exit 0
	fi

	setup_core_pattern
	wait_for_db
	echo $$ > "${BIN_DIR}/PID-map.pid"   # supervisor pid (for systemd)

	local shutting_down=0 TICK_PID=""
	stop_all() {
		shutting_down=1
		echo "ua-start: stopping all map-servers (SIGTERM)..."
		local i
		[ -n "$TICK_PID" ] && kill "$TICK_PID" 2>/dev/null
		for i in "${!MAP_PID[@]}"; do kill -TERM "${MAP_PID[$i]}" 2>/dev/null; done
		for i in "${!PERF_PID[@]}"; do kill -INT "${PERF_PID[$i]}" 2>/dev/null; done
	}
	trap stop_all TERM INT

	local i
	for i in $(seq 1 "$K"); do launch_instance "$i"; done
	# a ticker child wakes the loop below every UA_ROTATE_TICK s for the uptime check
	[ "$ROTATE_SECS" -gt 0 ] && { sleep "$UA_ROTATE_TICK" & TICK_PID=$!; }

	# ---- supervise: restart any instance that dies ----------------------
	local dpid rc inst sig now up
	while [ "$shutting_down" -eq 0 ]; do
		dpid=""
		wait -n -p dpid; rc=$?
		dpid=${dpid:-}   # wait unsets it when a signal cut the wait short
		[ "$shutting_down" -ne 0 ] && break
		[ -z "$dpid" ] && continue
		if [ "$dpid" = "$TICK_PID" ]; then
			TICK_PID=""
			cut_due
			[ "$shutting_down" -ne 0 ] && break
			sleep "$UA_ROTATE_TICK" & TICK_PID=$!
			continue
		fi
		inst="${PID_INST[$dpid]:-}"
		[ -z "$inst" ] && continue          # a background perf report (or unknown) exited - ignore
		unset 'PID_INST[$dpid]'
		unset 'MAP_PID[$inst]'

		if [ "$rc" -gt 128 ]; then
			sig=$((rc - 128))
			case "$sig" in
				3|4|5|6|7|8|11|31) capture_crash "$sig" "$dpid" "map${inst}" "${CONSOLE[$inst]}" ;;
				9) echo "ua-start: map#$inst KILLED (SIGKILL/OOM) - check dmesg" >&2
				   echo "$(date '+%F %T')  map${inst}  SIGKILL/OOM?  pid=$dpid" >> "$CRASH_INDEX" ;;
				*) echo "ua-start: map#$inst exited via signal $sig" >&2 ;;
			esac
		else
			echo "ua-start: map#$inst exited (rc=$rc)" >&2
		fi
		# stop its perf recorder (a new one starts with the restart)
		[ -n "${PERF_PID[$inst]:-}" ] && { kill -INT "${PERF_PID[$inst]}" 2>/dev/null; unset 'PERF_PID[$inst]'; }

		[ "$shutting_down" -ne 0 ] && break
		now=$(date +%s); up=$(( now - ${START_AT[$inst]:-now} ))
		if [ "$up" -lt "$MIN_UPTIME" ]; then
			echo "ua-start: map#$inst flapping (up ${up}s); back-off ${BACKOFF}s" >&2
			sleep "$BACKOFF"
			[ "$shutting_down" -ne 0 ] && break
		fi
		echo "ua-start: restarting map#$inst" >&2
		launch_instance "$inst"
	done

	# ---- graceful shutdown ---------------------------------------------
	trap - TERM INT
	[ -n "$TICK_PID" ] && kill "$TICK_PID" 2>/dev/null   # a ticker started just after stop_all ran
	echo "ua-start: waiting for map-servers to finish do_final()..."
	for i in "${!MAP_PID[@]}"; do wait "${MAP_PID[$i]}" 2>/dev/null; done
	for i in "${!PERF_PID[@]}"; do finalize_perf "${PERF_PID[$i]}" "${PERF_DATA[$i]:-}"; done
	wait   # reports of earlier pieces still being written
	rm -f "${BIN_DIR}"/PID-map*.pid
	echo "ua-start: all map-servers stopped."
	exit 0
}

# --------------------------------------------------------------------------
if [ "$SERVER" = "map" ]; then
	run_map_supervisor
else
	run_single
fi
