#!/bin/bash
# regress.sh <run-dir> - every SQL-audit e2e against one stand, each on a freshly started stand.
SP=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit
RUN="$1"
M="mysql --no-defaults -h127.0.0.1 -P13306 -uroot ragnarok"
cd "$SP" || exit 2
pass=0; fail=0
one() { # one <label> <command...>  (stand must be up)
	local label="$1"; shift
	if out=$(timeout 400 "$@" 2>&1); then pass=$((pass+1)); echo "PASS  $label"; else fail=$((fail+1)); echo "FAIL  $label"; echo "$out" | grep -v '^  created' | tail -6 | sed 's/^/      /'; fi
}
fresh() { "$SP/srv.sh" stop "$RUN" >/dev/null; "$SP/srv.sh" start "$RUN" >/dev/null; }

$M -e "DELETE FROM ipbanlist; DELETE FROM mapreg WHERE varname='\$AUDIT_RELOAD'"
$M < "$SP/login_sql_e2e_setup.sql"
fresh; one "login: injection, registration, stalls" python3 -I login_sql_e2e.py "$RUN"
fresh; one "mapreg: @reloadscript keeps globals" python3 -I mapreg_reload_e2e.py "$RUN"
for s in party guild homun; do fresh; one "names: $s" python3 -I names_e2e.py "$RUN" "$s"; done
"$SP/srv.sh" stop "$RUN" >/dev/null
python3 -I expel_direct_e2e.py "$RUN" setup >/dev/null; : > "$RUN/char.out"
"$SP/srv.sh" start "$RUN" >/dev/null; one "names: expulsion reason" python3 -I expel_direct_e2e.py "$RUN" test
for extra in "$SP"/regress.d/*.sh; do [ -e "$extra" ] && . "$extra"; done
"$SP/srv.sh" stop "$RUN" >/dev/null
echo "== $pass passed, $fail failed"
[ "$fail" -eq 0 ]
