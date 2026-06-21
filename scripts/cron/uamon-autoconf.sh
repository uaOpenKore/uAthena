#!/bin/bash
# uamon-autoconf.sh - rebalance the per-instance map lists (confN/maps_athena.conf)
# from monitoring data. Run monthly (the 02:00 restart then applies them).
#
# Algorithm (per the design):
#   * chunks N = launched map-server count = min(#confN, floor(threads/2)-1, 30)
#     (same as ua-mapcount.sh, so no map lands on a server that won't start).
#   * master = active `map:` entries in conf/maps_athena.conf.
#   * peaks  = per-map MAX(players_max) from stat_hour over the last 6 weeks.
#   * Phase 1: repeatedly take (highest-peak, lowest-peak) from the ranked maps
#     and put BOTH into the next chunk (round-robin), removing them from master.
#   * Phase 2: master maps never seen in the DB (0 visitors) are spread one-by-one
#     round-robin (continuing the rotation) so every map is placed evenly.
#   * Validate (each master map placed exactly once, no dup across chunks), back up,
#     then write atomically. The master conf/maps_athena.conf is only ever read.
#
# Env: AUTOCONF_ROOT (default /opt/uathena) - holds conf/ and confN/.
#      AUTOCONF_WEEKS (default 6).  AUTOCONF_DRYRUN=1 - print the plan, write nothing.
#      AUTOCONF_PEAKS_FILE - read "map peak" lines from a file instead of Mongo (testing).
set -u
SELF="$(cd "$(dirname "$0")" && pwd)"
. "$SELF/uamon-lib.sh"
uamon_load_conf
. "$SELF/../ua-mapcount.sh"   # ua_cpu_max / ua_threads (installed beside cron/ under bin/)

AUTOCONF_ROOT="${AUTOCONF_ROOT:-/opt/uathena}"
AUTOCONF_WEEKS="${AUTOCONF_WEEKS:-6}"
AUTOCONF_DRYRUN="${AUTOCONF_DRYRUN:-0}"
MASTER_FILE="$AUTOCONF_ROOT/conf/maps_athena.conf"
BACKUP_KEEP=6

[ -r "$MASTER_FILE" ] || uamon_die "master map list not found: $MASTER_FILE"

# ---- chunk count = actual launched servers -------------------------------
confN=0
while [ -d "$AUTOCONF_ROOT/conf$((confN + 1))" ]; do confN=$((confN + 1)); [ "$confN" -ge 30 ] && break; done
[ "$confN" -ge 1 ] || uamon_die "no confN dirs under $AUTOCONF_ROOT (single-server mode uses conf/ directly; nothing to balance)"
cpu_max=$(ua_cpu_max)
N=$confN; [ "$cpu_max" -lt "$N" ] && N=$cpu_max; [ "$N" -gt 30 ] && N=30
if [ "$confN" -gt "$N" ]; then
	uamon_log "WARNING: $confN confN dirs but only $N map-servers will launch (CPU cap); balancing across $N to avoid orphaned maps"
fi
uamon_log "autoconf: $N chunk(s), master=$MASTER_FILE, window=${AUTOCONF_WEEKS}w"

# ---- master list (active map: lines, unique, order preserved) ------------
declare -A INMASTER
mapfile -t MASTER < <(grep -E '^[[:space:]]*map:' "$MASTER_FILE" | sed -E 's/^[[:space:]]*map:[[:space:]]*//; s/\.gat//; s/[[:space:]].*//' | awk 'NF && !seen[$0]++')
for m in "${MASTER[@]}"; do INMASTER["$m"]=1; done
[ "${#MASTER[@]}" -ge 1 ] || uamon_die "master list empty"
uamon_log "master maps: ${#MASTER[@]}"

# ---- ranked peaks (desc), intersected with master ------------------------
SINCE=$(iso_utc $(( $(date +%s) - AUTOCONF_WEEKS * 7 * 86400 )))
read_peaks() {
	if [ -n "${AUTOCONF_PEAKS_FILE:-}" ]; then cat "$AUTOCONF_PEAKS_FILE"; return; fi
	"$MONGOSH" "$MONGO_URI/$MONGO_DB" --quiet --eval '
		var since=new Date("'"$SINCE"'");
		db["'"$COLL_HOUR"'"].aggregate([
			{$match:{type:"map",ts:{$gte:since}}},
			{$group:{_id:"$map",peak:{$max:"$players_max"}}},
			{$sort:{peak:-1}}
		]).forEach(function(d){print(d._id+" "+d.peak);});'
}
RANKED=()   # map names, highest peak first, only those present in master
while read -r mp pk; do
	[ -n "$mp" ] || continue
	[ -n "${INMASTER[$mp]:-}" ] && RANKED+=("$mp")
done < <(read_peaks)
uamon_log "ranked maps with stats (in master): ${#RANKED[@]}"

# ---- distribute ----------------------------------------------------------
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
for i in $(seq 1 "$N"); do : > "$TMP/chunk.$i"; done
declare -A PLACED
rr=0
assign() { local m="$1"; local c=$(( rr % N + 1 )); echo "$m" >> "$TMP/chunk.$c"; PLACED["$m"]=1; rr=$((rr + 1)); }

# Phase 1: (heaviest + lightest) pair per chunk, round-robin
lo=0; hi=$(( ${#RANKED[@]} - 1 ))
while [ "$lo" -le "$hi" ]; do
	if [ "$lo" -eq "$hi" ]; then
		assign "${RANKED[$lo]}"; lo=$((lo + 1))
	else
		big="${RANKED[$lo]}"; small="${RANKED[$hi]}"
		c=$(( rr % N + 1 ))
		echo "$big"   >> "$TMP/chunk.$c"; PLACED["$big"]=1
		echo "$small" >> "$TMP/chunk.$c"; PLACED["$small"]=1
		rr=$((rr + 1)); lo=$((lo + 1)); hi=$((hi - 1))
	fi
done

# Phase 2: master maps with no stats (never visited) - even round-robin
for m in "${MASTER[@]}"; do [ -z "${PLACED[$m]:-}" ] && assign "$m"; done

# ---- validate (eAthena invariant: each map exactly once, no dup) ---------
total=0; for i in $(seq 1 "$N"); do total=$(( total + $(wc -l < "$TMP/chunk.$i") )); done
dups=$(cat "$TMP"/chunk.* | sort | uniq -d)
if [ "$total" -ne "${#MASTER[@]}" ] || [ -n "$dups" ]; then
	uamon_die "VALIDATION FAILED (placed=$total master=${#MASTER[@]} dups=[$(echo "$dups" | tr '\n' ' ')]); NOT writing any config"
fi

# ---- report --------------------------------------------------------------
for i in $(seq 1 "$N"); do
	uamon_log "  chunk $i (conf$i): $(wc -l < "$TMP/chunk.$i") maps"
done

if [ "$AUTOCONF_DRYRUN" = "1" ]; then
	uamon_log "DRYRUN: validated OK, nothing written"
	for i in $(seq 1 "$N"); do echo "=== conf$i/maps_athena.conf ==="; sed 's/^/map: /' "$TMP/chunk.$i" | head -5; echo "  ... ($(wc -l < "$TMP/chunk.$i") total)"; done
	exit 0
fi

# ---- write atomically (+ timestamped backup) -----------------------------
TS=$(date +%Y%m%d-%H%M%S)
for i in $(seq 1 "$N"); do
	dst="$AUTOCONF_ROOT/conf$i/maps_athena.conf"
	[ -d "$AUTOCONF_ROOT/conf$i" ] || uamon_die "conf$i missing mid-run; aborting"
	{
		echo "// AUTO-GENERATED by uamon-autoconf.sh on $(date '+%F %T') - DO NOT EDIT"
		echo "// (regenerated monthly from monitoring peaks; edits are overwritten)"
		echo "// map-server #$i : $(wc -l < "$TMP/chunk.$i") maps"
		sed 's/^/map: /' "$TMP/chunk.$i"
	} > "$dst.tmp.$$"
	[ -f "$dst" ] && cp -p "$dst" "$dst.bak.$TS"
	mv -f "$dst.tmp.$$" "$dst"
	# keep only the newest $BACKUP_KEEP backups
	ls -1t "$AUTOCONF_ROOT/conf$i"/maps_athena.conf.bak.* 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | xargs -r rm -f
	# sanity: warn if this instance's map_athena.conf imports the MASTER list
	# instead of its own (that would make the instance load every map -> dup maps)
	if [ -r "$AUTOCONF_ROOT/conf$i/map_athena.conf" ] && \
	   grep -qE '^[[:space:]]*import:[[:space:]]*conf/maps_athena\.conf' "$AUTOCONF_ROOT/conf$i/map_athena.conf"; then
		uamon_log "WARNING: conf$i/map_athena.conf imports conf/maps_athena.conf (master) - it must import conf$i/maps_athena.conf, else this server loads ALL maps"
	fi
done
uamon_log "autoconf: wrote $N map list(s). Restart map-servers to apply (cron does this at 02:00)."
