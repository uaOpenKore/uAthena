#!/bin/bash
# run_le2.sh <run-dir> <scenario> - one loaderr2_e2e.py scenario on a freshly started stand.
SP=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit
M="mysql --no-defaults -h127.0.0.1 -P13306 -uroot ragnarok"
"$SP/srv.sh" stop "$1" >/dev/null; "$SP/srv.sh" start "$1" >/dev/null
cd "$SP" && timeout 300 python3 -I loaderr2_e2e.py "$1" "$2"; rc=$?
"$SP/srv.sh" stop "$1" >/dev/null
for t in pet mercenary guild party quest achievement; do # a crashed run must not leave a table hidden
	[ -n "$($M -N -e "SHOW TABLES LIKE '${t}_e2e_hidden'")" ] && $M -e "RENAME TABLE \`${t}_e2e_hidden\` TO \`$t\`"
done
exit $rc
