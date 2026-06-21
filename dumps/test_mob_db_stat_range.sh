#!/bin/bash
# Regression test for the mob_db stat-column width bug.
#
# Bug: GvG treasure boxes / Emperium-room crystals in db/mob_db2.txt carry
# DEX=999 (TREASURE_BOX41-49=1938-1946, CRYSTAL_6-9=1951-1954,
# TREASURE_BOX_I=1955). The SQL `mob_db` schema declared the six base-stat
# columns (STR/AGI/VIT/INT/DEX/LUK) as `tinyint(4) unsigned` (max 255), so
# importing those rows produced "Out of range value for column 'DEX'" and the
# value was truncated to 255. The server stores these stats as `unsigned short`
# (src/map/map.h: struct status_data), i.e. 0..65535, so the column must be at
# least `smallint(6) unsigned`.
#
# This test builds a throwaway database from the REAL committed schema
# (dumps/migrations/1-mob_db.sql), inserts the REAL TREASURE_BOX41 row taken
# from dumps/migrations/A-mob_db.sql, and asserts the stored DEX is exactly 999.
#
# Run from the repo root or from dumps/.  Requires a local MariaDB/MySQL with a
# root login that can CREATE/DROP DATABASE (matches the dev box).
#
# Exit 0 = PASS, non-zero = FAIL.

set -u

# locate repo files regardless of CWD
HERE="$(cd "$(dirname "$0")" && pwd)"
SCHEMA="$HERE/migrations/1-mob_db.sql"
DATA="$HERE/migrations/A-mob_db.sql"

MYSQL=(mysql -uroot)
DB="ua_dextest_$$"

fail() { echo "FAIL: $*"; exit 1; }

[ -f "$SCHEMA" ] || fail "schema not found: $SCHEMA"
[ -f "$DATA" ]   || fail "data not found: $DATA"

# always clean up the scratch DB
cleanup() { "${MYSQL[@]}" -e "DROP DATABASE IF EXISTS \`$DB\`" 2>/dev/null; }
trap cleanup EXIT

"${MYSQL[@]}" -e "DROP DATABASE IF EXISTS \`$DB\`; CREATE DATABASE \`$DB\`" \
	|| fail "cannot create scratch database (root login / privileges?)"

# build the mob_db table straight from the committed migration schema
"${MYSQL[@]}" "$DB" < "$SCHEMA" || fail "schema load failed"

# pull the real TREASURE_BOX41 (id 1938, DEX=999) insert and apply it,
# capturing any warnings (truncation shows up here)
INSERT="$(/bin/grep -E '\( 1938, "TREASURE_BOX41"' "$DATA" | head -1)"
[ -n "$INSERT" ] || fail "could not find TREASURE_BOX41 (1938) insert in $DATA"

WARN="$(printf '%s\n' "$INSERT" | "${MYSQL[@]}" --show-warnings "$DB" 2>&1)"
[ -n "$WARN" ] && echo "  [sql warnings] $WARN"

GOT="$("${MYSQL[@]}" "$DB" -sN -e "SELECT DEX FROM mob_db WHERE ID=1938")"
echo "  TREASURE_BOX41 (1938) stored DEX = ${GOT:-<none>} (expected 999)"

[ "$GOT" = "999" ] || fail "DEX truncated to '$GOT' — mob_db stat columns too narrow"

echo "PASS: mob_db schema preserves DEX=999"
exit 0
