#!/bin/bash
# uamon-lib.sh - shared helpers for the map-server load monitor. Sourced by the
# uamon-*.sh cron scripts; not run directly.

uamon_self_dir() { cd "$(dirname "${BASH_SOURCE[0]}")" && pwd; }

uamon_load_conf() {
	local d; d="$(uamon_self_dir)"
	# shellcheck source=uamon.conf
	. "$d/uamon.conf"
}

uamon_log() { echo "$(date '+%F %T') uamon: $*"; }
uamon_die() { echo "$(date '+%F %T') uamon ERROR: $*" >&2; exit 1; }

# --- time -----------------------------------------------------------------
# floor epoch to a bucket size (60 / 600 / 3600)
epoch_floor() { local e="$1" s="$2"; echo $(( e - e % s )); }
# epoch -> Mongo ISO (UTC, no fractional). Stored time is always UTC.
iso_utc() { date -u -d "@$1" '+%Y-%m-%dT%H:%M:%SZ'; }

# --- MongoDB --------------------------------------------------------------
# Run a JS snippet against $MONGO_DB. Returns mongosh's exit status.
# UAMON_DRYRUN=1 prints the JS instead of running it (testing / no mongosh).
mongo_eval() {
	if [ "${UAMON_DRYRUN:-0}" = "1" ]; then printf '%s\n' "--- mongo_eval JS ---" "$1"; return 0; fi
	"$MONGOSH" "$MONGO_URI/$MONGO_DB" --quiet --eval "$1"
}
# Run a JS file (for larger scripts).
mongo_file() { "$MONGOSH" "$MONGO_URI/$MONGO_DB" --quiet --file "$1"; }

# --- running map-server instances ----------------------------------------
# Echo "N pid" per live instance, from PID-mapN.pid (written by the supervisor).
# The supervisor's own PID-map.pid (no digit) is intentionally skipped.
running_instances() {
	local f n pid
	for f in "$UA_BIN_DIR"/PID-map[0-9]*.pid; do
		[ -e "$f" ] || continue
		n="${f##*/PID-map}"; n="${n%.pid}"
		case "$n" in (*[!0-9]*|'') continue;; esac   # digits only
		pid="$(cat "$f" 2>/dev/null)"
		[ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && echo "$n $pid"
	done
}

# --- aggregation (10-minute / hourly) ------------------------------------
# Aggregate raw per-minute docs in [t0,t1) from <src> into <dst>, labelled <tl>.
# Per param + per (server,map): avg (approximation) and max (peak). The map avg
# is AVERAGE CONCURRENT over the window = sum(players) / (that server's minute
# snapshot count in the window) so minutes where a map had 0 players (and were
# therefore not logged) correctly drag the average down. Peaks are exact maxima.
uamon_aggregate() { # uamon_aggregate <src> <dst> <iso_t0> <iso_t1> <iso_label>
	local src="$1" dst="$2" t0="$3" t1="$4" tl="$5"
	mongo_eval '
		var t0=new Date("'"$t0"'"), t1=new Date("'"$t1"'"), tl=new Date("'"$tl"'");
		var src=db["'"$src"'"], dst=db["'"$dst"'"];
		var servers=src.aggregate([
			{$match:{ts:{$gte:t0,$lt:t1},type:"server"}},
			{$group:{_id:"$server",cpu_avg:{$avg:"$cpu"},cpu_max:{$max:"$cpu"},
			         ram_avg:{$avg:"$ram_mb"},ram_max:{$max:"$ram_mb"},samples:{$sum:1}}}
		]).toArray();
		var snap={}; servers.forEach(function(s){snap[s._id]=s.samples;});
		var maps=src.aggregate([
			{$match:{ts:{$gte:t0,$lt:t1},type:"map"}},
			{$group:{_id:{server:"$server",map:"$map"},
			         players_sum:{$sum:"$players"},players_max:{$max:"$players"}}}
		]).toArray();
		var d=[];
		servers.forEach(function(s){ d.push({ts:tl,server:s._id,type:"server",
			cpu_avg:Math.round(s.cpu_avg),cpu_max:s.cpu_max,
			ram_avg:Math.round(s.ram_avg),ram_max:s.ram_max,samples:s.samples}); });
		maps.forEach(function(m){ var n=snap[m._id.server]||0;
			d.push({ts:tl,server:m._id.server,type:"map",map:m._id.map,
				players_avg:(n?Math.round(m.players_sum/n):0),players_max:m.players_max}); });
		if(d.length) dst.insertMany(d);
		print("uamon: "+d.length+" docs -> '"$dst"' @ "+tl.toISOString());
	'
}

# conf dir for instance N: confN if present, else conf (for #1).
uamon_confdir() {
	local n="$1"
	if [ -d "$UA_BIN_DIR/conf$n" ]; then echo "conf$n"
	elif [ "$n" = "1" ]; then echo "conf"
	else echo ""; fi
}

# --- per-thread CPU (delta sampling) -------------------------------------
# utime+stime (clock ticks) of one thread, from /proc (same data ps reads, but
# at clock-tick resolution so a short delta window is accurate).
thread_jiffies() {
	local line rest
	line=$(cat "/proc/$1/task/$2/stat" 2>/dev/null) || return 1
	rest=${line#*) }            # drop "pid (comm) " (comm may contain spaces)
	set -- $rest                # field 3 (state) is now $1 ; utime=field14=$12, stime=field15=$13
	echo $(( ${12:-0} + ${13:-0} ))
}
pid_threads() { local t; for t in /proc/"$1"/task/*; do [ -d "$t" ] && echo "${t##*/}"; done; }

# RSS of a process in whole MB (process-wide; includes all its threads).
pid_rss_mb() {
	local kb; kb=$(ps -o rss= -p "$1" 2>/dev/null | tr -d ' ')
	[ -n "$kb" ] && echo $(( kb / 1024 )) || echo 0
}

# --- online players per map (SQL) ----------------------------------------
# Echo "mapname<TAB>count" for maps with >0 online players (.gat stripped),
# from char.online + char.last_map. NOTE: last_map is only as fresh as the
# char autosave, so this lags by the autosave interval (per the design choice).
online_map_counts() {
	"$SQL_CLIENT" -h"$SQL_HOST" -P"$SQL_PORT" -u"$SQL_USER" -p"$SQL_PASS" "$SQL_DB" \
		-N -B -e "SELECT REPLACE(last_map,'.gat',''), COUNT(*) FROM \`$CHAR_TABLE\` WHERE online=1 GROUP BY last_map;" 2>/dev/null
}

# --- map -> instance attribution -----------------------------------------
# Fills the assoc array named in $1 with map=>instanceN, from each running
# instance's confN map list (the `map:` lines in confN/*.conf, or conf/maps_*).
build_map_server_table() {
	local -n _t="$1"; local n pid confdir m
	while read -r n pid; do
		[ -n "$n" ] || continue
		confdir="$(uamon_confdir "$n")"; [ -n "$confdir" ] || continue
		while read -r m; do
			[ -n "$m" ] && _t["$m"]="$n"
		done < <(grep -rhE '^[[:space:]]*map:' "$UA_BIN_DIR/$confdir"/*.conf 2>/dev/null | sed -E 's/^[[:space:]]*map:[[:space:]]*//; s/\.gat//; s/[[:space:]].*//')
	done < <(running_instances)
}
