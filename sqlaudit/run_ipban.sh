#!/bin/bash
# run_ipban.sh <run-dir> - ipban_e2e.py with ipban + dynamic_pass_failure_ban switched back on for this run only
# (the audit run dirs keep them off so that the other tests' failed logins don't ban 127.0.0.*).
SP=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit
RUN="$1"
IMPORT="$RUN/conf/import/login_conf.txt"
"$SP/srv.sh" stop "$RUN" >/dev/null
printf 'ipban: yes\ndynamic_pass_failure_ban: yes\n' >> "$IMPORT"
"$SP/srv.sh" start "$RUN" >/dev/null
cd "$SP" && timeout 200 python3 -I ipban_e2e.py "$RUN"; rc=$?
"$SP/srv.sh" stop "$RUN" >/dev/null
# drop the two lines appended above (the last two of the file)
head -n -2 "$IMPORT" > "$IMPORT.tmp" && mv "$IMPORT.tmp" "$IMPORT"
exit $rc
