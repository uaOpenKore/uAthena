#!/bin/bash
# uamon-10min.sh - aggregate the last completed 10-minute window of per-minute
# data into COLL_10MIN (avg + peak per server and per map). Run at every :M0.
# ts is floored to the 10-minute interval (UTC).
set -u
. "$(cd "$(dirname "$0")" && pwd)/uamon-lib.sh"
uamon_load_conf

NOW=$(date +%s)
END=$(epoch_floor "$NOW" 600)     # current 10-min boundary
START=$(( END - 600 ))            # the window that just completed
uamon_aggregate "$COLL_MIN" "$COLL_10MIN" \
	"$(iso_utc "$START")" "$(iso_utc "$END")" "$(iso_utc "$START")" \
	|| uamon_die "10-min aggregation failed"
