#!/bin/bash
# uamon-cleanup.sh - drop stats older than the retention window. Run monthly.
#   per-minute  : RET_MIN_DAYS   (~2 months)
#   10-minute   : RET_10MIN_DAYS (~6 months)
#   hourly      : RET_HOUR_DAYS  (~2 years)
set -u
. "$(cd "$(dirname "$0")" && pwd)/uamon-lib.sh"
uamon_load_conf

NOW=$(date +%s)
CUT_MIN=$(iso_utc $(( NOW - RET_MIN_DAYS   * 86400 )))
CUT_10=$( iso_utc $(( NOW - RET_10MIN_DAYS * 86400 )))
CUT_HR=$( iso_utc $(( NOW - RET_HOUR_DAYS  * 86400 )))

mongo_eval '
var r1=db["'"$COLL_MIN"'"].deleteMany({ts:{$lt:new Date("'"$CUT_MIN"'")}}).deletedCount;
var r2=db["'"$COLL_10MIN"'"].deleteMany({ts:{$lt:new Date("'"$CUT_10"'")}}).deletedCount;
var r3=db["'"$COLL_HOUR"'"].deleteMany({ts:{$lt:new Date("'"$CUT_HR"'")}}).deletedCount;
print("uamon cleanup: removed min="+r1+" 10min="+r2+" hour="+r3);
' || uamon_die "cleanup failed"
