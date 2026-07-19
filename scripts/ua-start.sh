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
		"$SELF_DIR/ua-crashdump.sh" "$BIN" "$core" >> "$report" 2>&1
		prune_keep "$CORE_DIR" "core.*" "$UA_CORE_KEEP"
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

start_perf() {  # start_perf <pid> <tag> ; echoes "perfpid|perfdata" or empty
	[ "$UA_PERF" = "1" ] || return 0
	command -v perf >/dev/null 2>&1 || { echo "ua-start: UA_PERF=1 but 'perf' not installed" >&2; return 0; }
	local pid="$1" tag="$2" para data ppid
	para=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo 3)
	[ "$para" -gt 1 ] 2>/dev/null && echo 1 > /proc/sys/kernel/perf_event_paranoid 2>/dev/null
	data="$PERF_DIR/${tag}-$(date +%Y%m%d-%H%M%S)-pid${pid}.perf.data"
	perf record -F "$UA_PERF_FREQ" -g --call-graph fp -o "$data" -p "$pid" >/dev/null 2>&1 &
	ppid=$!
	echo "${ppid}|${data}"
}

finalize_perf() {  # finalize_perf <perfpid> <perfdata>
	local ppid="$1" data="$2"
	[ -n "$ppid" ] || return 0
	kill -INT "$ppid" 2>/dev/null
	wait "$ppid" 2>/dev/null
	if [ -n "$data" ] && [ -s "$data" ]; then
		perf report --stdio -i "$data" > "${data%.data}.txt" 2>/dev/null && \
			echo "ua-start: perf report -> ${data%.data}.txt"
	fi
	prune_keep "$PERF_DIR" "*.perf.data" "$UA_PERF_KEEP"
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
	setup_core_pattern

	echo "ua-start: launching $BIN ($(date '+%F %T'))" | tee -a "$CONSOLE_LOG"
	# Redirect the binary's console straight to uAlogin.log / uAchar.log, exactly like the map
	# supervisor does for uAmapN.log. Previously login/char were launched bare ("$BIN" &) and relied
	# on systemd StandardOutput=append: -- which silently produces NO file on systemd < v240 (no
	# 'append:' support), so uAchar.log / uAlogin.log never appeared while uAmapN.log always did (the
	# map path redirects in-shell). This also makes capture_crash's `tail "$CONSOLE_LOG"` actually work.
	"$BIN" >> "$CONSOLE_LOG" 2>&1 &
	local SPID=$!
	echo "$SPID" > "$PID"

	local PERF_PID="" PERF_DATA="" pr
	pr=$(start_perf "$SPID" "$SERVER"); PERF_PID="${pr%%|*}"; PERF_DATA="${pr#*|}"
	[ "$pr" = "$PERF_PID" ] && PERF_DATA=""   # no '|' -> perf off
	[ -n "$PERF_DATA" ] && echo "ua-start: perf profiling -> $PERF_DATA (${UA_PERF_FREQ}Hz)"

	shutdown_fwd() { [ -n "$PERF_PID" ] && kill -INT "$PERF_PID" 2>/dev/null; kill -TERM "$SPID" 2>/dev/null; }
	trap shutdown_fwd TERM INT

	local rc
	wait "$SPID"; rc=$?
	while kill -0 "$SPID" 2>/dev/null; do wait "$SPID"; rc=$?; done
	trap - TERM INT

	finalize_perf "$PERF_PID" "$PERF_DATA"

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
		exec 9>"${BIN_DIR}/.ua-map.lock" 2>/dev/null && \
		if ! flock -n 9; then
			echo "ua-start: map supervisor already running (lock held)"
			exit 0
		fi
	fi

	# shellcheck source=ua-mapcount.sh
	. "$SELF_DIR/ua-mapcount.sh"

	local K; K=$(ua_map_count)
	echo "ua-start: multi-map supervisor: $K map-server(s) (threads=$(ua_threads), confN=$(ua_conf_max))"

	declare -A MAP_PID PID_INST START_AT PERF_PID PERF_DATA CONSOLE CONFDIR CORES

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

		echo "ua-start: map#$i launch (cores=${cores:-all} conf=$confdir) -> $console ($(date '+%F %T'))" \
			| tee -a "$console"
		"${PIN[@]}" "$BIN" "${CFG_ARGS[@]}" >> "$console" 2>&1 &
		local pid=$!
		MAP_PID[$i]=$pid; PID_INST[$pid]=$i; START_AT[$i]=$(date +%s)
		echo "$pid" > "${BIN_DIR}/PID-map${i}.pid"

		pr=$(start_perf "$pid" "map${i}")
		if [ -n "$pr" ] && [ "$pr" != "${pr%%|*}" ]; then
			PERF_PID[$i]="${pr%%|*}"; PERF_DATA[$i]="${pr#*|}"
			echo "ua-start: map#$i perf -> ${PERF_DATA[$i]}"
		fi
		return 0
	}

	# ---- dry run: print the plan and exit -------------------------------
	if [ "$UA_DRYRUN" = "1" ]; then
		local i
		for i in $(seq 1 "$K"); do launch_instance "$i"; done
		echo "ua-start: DRYRUN done (nothing launched)"
		exit 0
	fi

	setup_core_pattern
	echo $$ > "${BIN_DIR}/PID-map.pid"   # supervisor pid (for systemd)

	local shutting_down=0
	stop_all() {
		shutting_down=1
		echo "ua-start: stopping all map-servers (SIGTERM)..."
		local i
		for i in "${!MAP_PID[@]}"; do kill -TERM "${MAP_PID[$i]}" 2>/dev/null; done
		for i in "${!PERF_PID[@]}"; do kill -INT "${PERF_PID[$i]}" 2>/dev/null; done
	}
	trap stop_all TERM INT

	local i
	for i in $(seq 1 "$K"); do launch_instance "$i"; done

	# ---- supervise: restart any instance that dies ----------------------
	local dpid rc inst sig now up
	while [ "$shutting_down" -eq 0 ]; do
		dpid=""
		wait -n -p dpid; rc=$?
		[ "$shutting_down" -ne 0 ] && break
		[ -z "$dpid" ] && continue
		inst="${PID_INST[$dpid]:-}"
		[ -z "$inst" ] && continue          # a perf child (or unknown) exited - ignore
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
	echo "ua-start: waiting for map-servers to finish do_final()..."
	for i in "${!MAP_PID[@]}"; do wait "${MAP_PID[$i]}" 2>/dev/null; done
	for i in "${!PERF_PID[@]}"; do finalize_perf "${PERF_PID[$i]}" "${PERF_DATA[$i]:-}"; done
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
