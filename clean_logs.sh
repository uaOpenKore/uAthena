#!/bin/bash
# clean_logs.sh - delete server logs older than a day.
#
# usage: ./clean_logs.sh [-n] [-a HOURS] [DIR]
#   DIR       log folder (default /opt/uathena/bin/log; /opt/uathena/log links to it)
#   -n        dry run: only list what would be deleted
#   -a HOURS  age limit in hours (default 24)
#
# Deletes regular files, also in the subfolders (core/, crash/, perf/), last changed longer ago than the age
# limit. Never touches folders, symlinks, anything outside DIR, or a file a running process still has open:
# the supervisor's own log can go unwritten for a day while the server runs, and deleting it would lose
# everything written to it until the next restart. Logs a server keeps writing (uAmap1.log ...) stay fresh.
#
# cron, every hour:
#   0 * * * * /root/uAthena/clean_logs.sh >> /opt/uathena/bin/log/clean_logs.log 2>&1

DRY=0
HOURS=24
while getopts "na:" opt; do
	case "$opt" in
	n) DRY=1 ;;
	a) HOURS="$OPTARG" ;;
	*) echo "usage: $0 [-n] [-a HOURS] [DIR]" >&2; exit 2 ;;
	esac
done
shift $((OPTIND - 1))
DIR="${1:-/opt/uathena/bin/log}"

case "$HOURS" in
''|*[!0-9]*) echo "clean_logs: -a takes whole hours, got '$HOURS'" >&2; exit 2 ;;
esac
if [ "$HOURS" -lt 1 ]; then
	echo "clean_logs: -a must be at least 1 hour" >&2; exit 2
fi

REAL=$(realpath -e -- "$DIR" 2>/dev/null)
if [ -z "$REAL" ] || [ ! -d "$REAL" ]; then
	echo "clean_logs: no such folder: $DIR" >&2; exit 1
fi
# Only a log folder: a typo like /opt/uathena/bin must never wipe the binaries and configs.
case "$REAL/" in
*/log/*|*/logs/*) ;;
*) echo "clean_logs: refusing '$REAL' - the path must contain a 'log' or 'logs' folder" >&2; exit 1 ;;
esac

# Files some process still has open, by real path (/proc/<pid>/fd links point at the real path).
declare -A OPEN=()
while IFS= read -r -d '' f; do
	OPEN["$f"]=1
done < <(find /proc/[0-9]*/fd -maxdepth 1 -type l -lname "$REAL/*" -printf '%l\0' 2>/dev/null)

deleted=0
open=0
bytes=0
while IFS= read -r -d '' f; do
	if [ -n "${OPEN[$f]+x}" ]; then
		echo "keep (open): $f"
		open=$((open + 1))
		continue
	fi
	size=$(stat -c %s -- "$f" 2>/dev/null) || size=0
	if [ "$DRY" -eq 1 ]; then
		echo "would delete: $f"
	elif ! rm -f -- "$f"; then
		continue
	fi
	deleted=$((deleted + 1))
	bytes=$((bytes + size))
done < <(find "$REAL" -xdev -type f -mmin +$((HOURS * 60)) -print0)

mb=$(awk -v b="$bytes" 'BEGIN { printf "%.1f", b / 1048576 }')
if [ "$DRY" -eq 1 ]; then
	echo "$(date '+%F %T') clean_logs: dry run - would delete $deleted file(s), $mb MB, older than $HOURS h in $REAL; $open open file(s) kept"
else
	echo "$(date '+%F %T') clean_logs: deleted $deleted file(s), $mb MB, older than $HOURS h in $REAL; $open open file(s) kept"
fi
