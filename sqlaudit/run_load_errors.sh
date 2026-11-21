#!/bin/bash
# run_load_errors.sh <run-dir> <scenario> - one load_errors_e2e.py scenario on a freshly started stand.
# "registry" runs the char-server as the restricted DB user charaudit (no SELECT on global_reg_value values).
SP=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit
RUN="$1"; SCEN="$2"
IMPORT="$RUN/conf/import/inter_conf.txt"
"$SP/srv.sh" stop "$RUN" >/dev/null
if [ "$SCEN" = registry ]; then
	printf 'char_server_id: charaudit\nchar_server_pw: charaudit\n' >> "$IMPORT"
fi
"$SP/srv.sh" start "$RUN" >/dev/null
cd "$SP" && timeout 300 python3 -I load_errors_e2e.py "$RUN" "$SCEN"; rc=$?
"$SP/srv.sh" stop "$RUN" >/dev/null
sed -i '/^char_server_id: charaudit$/d; /^char_server_pw: charaudit$/d' "$IMPORT"
exit $rc
