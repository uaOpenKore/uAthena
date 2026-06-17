#!/bin/bash
# uamon-hour.sh - aggregate the last completed hour of per-minute data into
# COLL_HOUR (avg + peak per server and per map). Run at every :00.
# ts is floored to the hour (UTC, minutes dropped).
set -u
. "$(cd "$(dirname "$0")" && pwd)/uamon-lib.sh"
uamon_load_conf

NOW=$(date +%s)
END=$(epoch_floor "$NOW" 3600)    # current hour boundary
START=$(( END - 3600 ))           # the hour that just completed
uamon_aggregate "$COLL_MIN" "$COLL_HOUR" \
	"$(iso_utc "$START")" "$(iso_utc "$END")" "$(iso_utc "$START")" \
	|| uamon_die "hourly aggregation failed"
