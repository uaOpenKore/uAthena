#!/bin/bash
#
# ua-mapcount.sh - single source of truth for the multi-map-server layout.
#
# Decides HOW MANY map-servers to run and WHICH CPU cores each is pinned to,
# from (a) the CPU thread count and (b) the number of confN/ directories.
# Sourced by ua-start.sh / ua-stop.sh and (the formula) mirrored in rc.local.
#
# Core layout (per the design):
#     CPU 0-1        -> map server #1
#     CPU 2-3        -> reserved for the system / NIC softirq / login+char
#     CPU 2N..2N+1   -> map server #N   (N >= 2)
# Max map-servers = min(30, floor(threads/2) - 1, #confN dirs). At least 1.
# (30 = MAX_MAP_SERVERS in src/char_sql/char.h - the char-server hard cap.)
#
# confN rule:
#   conf1, conf2, ... must be CONSECUTIVE. The run count is capped at the number
#   present (conf3 missing -> never more than 2). If conf1 is absent we run a
#   single map-server on the default conf/ directory.
#
# Usage (also works when sourced - then the ua_* functions are available):
#   ua-mapcount.sh            -> prints K (number of map-servers to launch)
#   ua-mapcount.sh threads    -> CPU thread count
#   ua-mapcount.sh cpu_max    -> max servers the CPU allows
#   ua-mapcount.sh conf_max   -> # of consecutive confN dirs (0 = none -> conf/)
#   ua-mapcount.sh cores N    -> "a,b" cores for instance N ("" if <4 threads)
#   ua-mapcount.sh confdir N  -> conf dir for instance N (confN, or conf for #1)
#   ua-mapcount.sh appcpus    -> space list of every core used by map servers
#   ua-mapcount.sh info       -> human-readable summary
#
# Base dir holding conf/ and confN/ is $UA_BIN_DIR (default: current dir).

UA_MAP_MAX=30   # char-server hard cap (MAX_MAP_SERVERS)

ua_threads() {
	local n
	# UA_FORCE_THREADS overrides autodetection (testing / manual capping).
	if [ -n "${UA_FORCE_THREADS:-}" ] && [ "$UA_FORCE_THREADS" -ge 1 ] 2>/dev/null; then
		echo "$UA_FORCE_THREADS"; return
	fi
	n=$(nproc 2>/dev/null) || n=$(grep -c '^processor' /proc/cpuinfo 2>/dev/null)
	[ -n "$n" ] && [ "$n" -ge 1 ] 2>/dev/null && { echo "$n"; return; }
	echo 1
}

# Max map-servers the CPU allows: <4 threads -> 1 (no pinning); else floor(T/2)-1.
ua_cpu_max() {
	local t; t=$(ua_threads)
	if [ "$t" -lt 4 ]; then echo 1; else echo $(( t / 2 - 1 )); fi
}

# Number of consecutive confN directories (conf1..confN). 0 if conf1 is absent.
ua_conf_max() {
	local base="${UA_BIN_DIR:-.}" n=0
	while [ "$n" -lt "$UA_MAP_MAX" ] && [ -d "$base/conf$((n + 1))" ]; do
		n=$((n + 1))
	done
	echo "$n"
}

# Final number of map-servers to launch.
ua_map_count() {
	local cpu conf k
	cpu=$(ua_cpu_max)
	conf=$(ua_conf_max)
	[ "$conf" -lt 1 ] && conf=1     # no confN -> single server on conf/
	k=$cpu
	[ "$conf" -lt "$k" ] && k=$conf
	[ "$k" -gt "$UA_MAP_MAX" ] && k="$UA_MAP_MAX"
	[ "$k" -lt 1 ] && k=1
	echo "$k"
}

# Cores for instance N: #1 -> 0,1 ; #N>=2 -> 2N,2N+1. Empty when <4 threads
# (then the instance is not pinned and may use every core).
ua_cores_for() {
	local n="$1" t; t=$(ua_threads)
	[ "$t" -lt 4 ] && { echo ""; return; }
	if [ "$n" -le 1 ]; then echo "0,1"; else echo "$((2 * n)),$((2 * n + 1))"; fi
}

# Conf directory for instance N: confN if it exists; for #1 fall back to conf/.
ua_confdir_for() {
	local n="$1" base="${UA_BIN_DIR:-.}"
	if [ -d "$base/conf$n" ]; then echo "conf$n"
	elif [ "$n" -le 1 ]; then echo "conf"
	else echo ""; fi
}

# Every core occupied by a map server (for rc.local APP_CPUS / XPS).
ua_appcpus() {
	local k i cores out=""
	k=$(ua_map_count)
	for i in $(seq 1 "$k"); do
		cores=$(ua_cores_for "$i")
		[ -n "$cores" ] && out="$out ${cores//,/ }"
	done
	echo "${out# }"
}

# Allow `source ua-mapcount.sh` without running anything.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
	case "${1:-count}" in
		count|"")  ua_map_count ;;
		threads)   ua_threads ;;
		cpu_max)   ua_cpu_max ;;
		conf_max)  ua_conf_max ;;
		cores)     ua_cores_for "${2:-1}" ;;
		confdir)   ua_confdir_for "${2:-1}" ;;
		appcpus)   ua_appcpus ;;
		info)
			t=$(ua_threads); k=$(ua_map_count)
			echo "threads=$t  cpu_max=$(ua_cpu_max)  conf_max=$(ua_conf_max)  -> launching $k map-server(s)"
			for i in $(seq 1 "$k"); do
				printf '  map#%-2d  cores=%-7s  conf=%s\n' "$i" "$(ua_cores_for "$i" | sed 's/^$/(all)/')" "$(ua_confdir_for "$i")"
			done
			;;
		*) echo "usage: $0 {count|threads|cpu_max|conf_max|cores N|confdir N|appcpus|info}" >&2; exit 2 ;;
	esac
fi
