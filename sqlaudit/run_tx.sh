#!/bin/bash
# run_tx.sh <run-dir> <scenario> - one tx_e2e.py scenario on a freshly started stand.
SP=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit
"$SP/srv.sh" stop "$1" >/dev/null; "$SP/srv.sh" start "$1" >/dev/null
cd "$SP" && timeout 400 python3 -I tx_e2e.py "$1" "$2"; rc=$?
"$SP/srv.sh" stop "$1" >/dev/null
mysql --no-defaults -h127.0.0.1 -P13306 -uroot ragnarok -e "DROP TRIGGER IF EXISTS e2e_block_insert"
exit $rc
