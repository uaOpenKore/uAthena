#!/bin/bash
# check_npc.sh : start the map-server alone in run-npc (npc/ -> tick64/npc), wait until it has loaded the NPCs,
# print every script error (file + line + failing line) and the "bad duplicate" lines, stop it.
R=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/run-npc
cd "$R" || exit 1
setsid nohup stdbuf -oL -eL ./map-server_sql > "$R/map.out" 2>&1 < /dev/null &
P=$!
for i in $(seq 1 120); do grep -q "Server is .ready.\|Connecting to [0-9]" "$R/map.out" 2>/dev/null && break; sleep 1; done
kill -9 $P 2>/dev/null
grep -a -A12 "script error on" "$R/map.out" | grep -a "script error on\|parse_\|^\*" | sed -E 's/^\*\s*[0-9]+ : /    > /'
echo "script errors: $(grep -ac 'script error on' "$R/map.out")  bad duplicates: $(grep -ac 'bad duplicate' "$R/map.out")"
