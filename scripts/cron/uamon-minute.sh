#!/bin/bash
# uamon-minute.sh - per-minute snapshot of each running map-server:
#   * CPU of its BUSIEST thread (delta of two samples -> current %CPU, 0-100 of
#     one core; the game-loop saturation), per instance.
#   * RSS in whole MB, per instance.
#   * players per map (>0 only) from SQL, attributed to the owning instance.
# One document PER record into COLL_MIN (type "server" and type "map"); ts floored
# to the minute (UTC).
set -u
. "$(cd "$(dirname "$0")" && pwd)/uamon-lib.sh"
uamon_load_conf

NOW=$(date +%s)
TS=$(iso_utc "$(epoch_floor "$NOW" 60)")

# ---- enumerate instances + take CPU sample #0 ----------------------------
declare -A INST J0
while read -r n pid; do
	[ -n "$n" ] || continue
	INST["$n"]="$pid"
	for tid in $(pid_threads "$pid"); do
		J0["$pid:$tid"]=$(thread_jiffies "$pid" "$tid")
	done
done < <(running_instances)

[ "${#INST[@]}" -eq 0 ] && { uamon_log "no running map-servers; nothing to log"; exit 0; }

# ---- wait the delta window, then take sample #1 + RSS ---------------------
SECS=$CPU_SAMPLE_SECS; [ "$SECS" -ge 1 ] 2>/dev/null || SECS=1
sleep "$SECS"
HZ=$(getconf CLK_TCK 2>/dev/null || echo 100); WIN=$(( SECS * HZ ))

declare -A CPU RAM
for n in "${!INST[@]}"; do
	pid="${INST[$n]}"; max=0
	for tid in $(pid_threads "$pid"); do
		j1=$(thread_jiffies "$pid" "$tid") || continue
		j0="${J0["$pid:$tid"]:-$j1}"
		d=$(( j1 - j0 )); [ "$d" -lt 0 ] && d=0
		[ "$d" -gt "$max" ] && max="$d"
	done
	CPU["$n"]=$(( (max * 100 + WIN / 2) / WIN ))   # rounded %CPU of busiest thread
	RAM["$n"]=$(pid_rss_mb "$pid")
done

# ---- players per map (SQL) + attribute to owning instance ----------------
declare -A MAP2SRV
build_map_server_table MAP2SRV
mapfile -t INSTLIST < <(printf '%s\n' "${!INST[@]}")
SINGLE=""; [ "${#INSTLIST[@]}" -eq 1 ] && SINGLE="${INSTLIST[0]}"

# ---- build the documents -------------------------------------------------
DOCS=""
for n in "${!INST[@]}"; do
	DOCS+="{ts:new Date(\"$TS\"),server:$n,type:\"server\",cpu:${CPU[$n]},ram_mb:${RAM[$n]}},"
done
while IFS=$'\t' read -r mapname cnt; do
	[ -n "$mapname" ] || continue
	[ "$cnt" -gt 0 ] 2>/dev/null || continue
	srv="${MAP2SRV[$mapname]:-${SINGLE:-0}}"
	# escape any stray quote/backslash in the map name (defensive)
	safe=${mapname//\\/\\\\}; safe=${safe//\"/\\\"}
	DOCS+="{ts:new Date(\"$TS\"),server:$srv,type:\"map\",map:\"$safe\",players:$cnt},"
done < <(online_map_counts)

mongo_eval "var d=[${DOCS}]; if(d.length) db.${COLL_MIN}.insertMany(d);" \
	&& uamon_log "logged minute $TS: ${#INST[@]} server(s)" \
	|| uamon_die "mongosh insert failed"
