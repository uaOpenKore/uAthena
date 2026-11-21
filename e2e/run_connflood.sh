#!/bin/bash
# run_connflood.sh <run> <port> <n> [per-ip limit]: n idle connections from 10.199.0.2 (netns s2stest) to <port> while
# a player logs in from this host; the server must keep at most <limit> of them and let the player in.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; PORT="$2"; N="$3"; LIMIT="${4:-0}"; rc=0
bash "$E/srv.sh" stop "$RUN" > /dev/null 2>&1; bash "$E/srv.sh" start "$RUN" 2>/dev/null | tail -1
P=""; for p in $(pgrep -f map-server_sql); do [ "$(readlink /proc/$p/cwd)" = "$(readlink -f "$RUN")" ] && P=$p; done
r0=$(awk '/VmRSS/{print int($2/1024)}' /proc/$P/status)
ip netns exec s2stest python3 -I "$E/connflood_hold.py" 10.199.0.1 "$PORT" "$N" 5 > "$E/connflood.out" 2>&1 &
FL=$!
sleep 4
r1=$(awk '/VmRSS/{print int($2/1024)}' /proc/$P/status)
(cd "$E" && timeout 60 python3 -I -c "
import sys; sys.path.insert(0,'.')
import rostub
from elemark_e2e import USER, PW
p=rostub.Session(USER,PW,log=lambda *a:None); p.login(timeout=10); _,r=p.char_enter(timeout=10); p.select_char(r[1][0][0]); st=p.map_enter(timeout=10)[0]
print('player map_enter', st); p.quit_game(wait=1); sys.exit(0 if st=='ok' else 1)") || { echo "FAIL  a player could not log in during the flood"; rc=1; }
wait $FL
cat "$E/connflood.out"
held=$(grep -o 'HELD [0-9]*' "$E/connflood.out" | grep -o '[0-9]*')
echo "map RSS $r0 -> $r1 MB during the flood (port $PORT)"
if [ "$LIMIT" -gt 0 ] && [ "${held:-0}" -gt "$LIMIT" ]; then echo "FAIL  $held idle connections from one address kept (limit $LIMIT)"; rc=1; fi
if [ "$LIMIT" -eq 0 ] && [ "${held:-0}" -ge $((N * 9 / 10)) ]; then echo "FAIL  one address keeps $held idle sessions"; rc=1; fi
bash "$E/srv.sh" stop "$RUN" > /dev/null 2>&1
[ $rc -eq 0 ] && echo "ok" && echo "ALL PASSED"
exit $rc
