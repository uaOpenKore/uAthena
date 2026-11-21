#!/bin/bash
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
$M -e "UPDATE login SET level=99 WHERE account_id=2000006"
bash "$E/srv.sh" stop "$RUN" > /dev/null; bash "$E/srv.sh" start "$RUN" | tail -1
P=""; for p in $(pgrep -f map-server_sql); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$(readlink -f "$RUN")" ] && P=$p; done
(cd "$E" && timeout 400 python3 -I memtrim_e2e.py "$P" "${2:-75}"); rc=$?
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
exit $rc
