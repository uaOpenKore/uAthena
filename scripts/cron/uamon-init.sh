#!/bin/bash
# uamon-init.sh - create the MongoDB collections + indexes. Run ONCE after
# installing (idempotent: re-running is a safe no-op). Every queryable field is
# indexed, per the requirement.
set -u
. "$(cd "$(dirname "$0")" && pwd)/uamon-lib.sh"
uamon_load_conf

mongo_eval '
function idx(coll, fields){ fields.forEach(f => db[coll].createIndex(Object.fromEntries([[f,1]]))); }
// raw per-minute
idx("'"$COLL_MIN"'",   ["ts","server","type","map","cpu","ram_mb","players"]);
db["'"$COLL_MIN"'"].createIndex({ts:1,type:1,server:1});
// 10-minute + hourly aggregates (avg + peak)
["'"$COLL_10MIN"'","'"$COLL_HOUR"'"].forEach(c => {
  idx(c, ["ts","server","type","map","cpu_avg","cpu_max","ram_avg","ram_max","players_avg","players_max","samples"]);
  db[c].createIndex({ts:1,type:1,server:1});
});
print("uamon: indexes ensured on '"$COLL_MIN"', '"$COLL_10MIN"', '"$COLL_HOUR"'");
' || uamon_die "mongosh failed (is MongoDB up and mongosh installed?)"
