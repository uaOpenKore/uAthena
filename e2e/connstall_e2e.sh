#!/bin/bash
# connstall_e2e.sh <bin-dir>: a map-server whose char-server answers no SYN (a listener with a full accept
# queue: the kernel drops further SYNs) must not stop its main loop for the kernel's whole SYN retry (~2 min).
# The map-server runs alone from run-conn (copy of run-t64, char_port 6999); [LOOPMETRIC] slow_loop shows the stall.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
SPR=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad
R=$SPR/e2e/run-conn; BIN="$1"
rm -rf "${R:?}" && cp -a "$SPR/e2e/run-t64" "$R" && rm -f "${R:?}"/*.out "${R:?}"/*.pid
sed -i -e "s/^char_port: .*/char_port: 6999/" -e "s/^map_port: .*/map_port: 5199/" "$R/conf/map_athena.conf"
cp -p "$BIN/map-server_sql" "$R/"
python3 -I - <<'PY' &
import socket, time
l = socket.socket(); l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
l.bind(("127.0.0.1", 6999)); l.listen(0)
fill = []
for i in range(4):                       # fill the accept queue: later SYNs are dropped
    c = socket.socket(); c.setblocking(False)
    try: c.connect(("127.0.0.1", 6999))
    except BlockingIOError: pass
    fill.append(c)
time.sleep(150)
PY
FAKE=$!
sleep 1
( cd "$R" && setsid nohup stdbuf -oL -eL ./map-server_sql > "$R/map.out" 2>&1 < /dev/null & )
sleep 100
for p in $(pgrep -f map-server_sql); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$R" ] && kill -9 "$p"; done
kill $FAKE 2>/dev/null
n=$(grep -ac 'Connecting to 127.0.0.1:6999' "$R/map.out")
after=$(awk '/Connecting to 127.0.0.1:6999/{f=1} f && /\[LOOPMETRIC\] map-server/{c++} END{print c+0}' "$R/map.out")
m=$(grep -ao 'slow_loop ms=[0-9]*' "$R/map.out" | grep -o '[0-9]*$' | sort -n | tail -1)
echo "connect attempts: $n; minute summaries after the first attempt: $after; longest round: ${m:-0} ms"
grep -a 'slow_loop\|connect failed\|connect timed out' "$R/map.out" | cut -c1-150 | head -4
if [ "$after" -ge 1 ] && [ "$n" -ge 3 ] && [ "${m:-0}" -le 5000 ]; then echo "ok    the main loop runs on and retries while the char-server does not answer"
else echo "FAIL  the main loop stood on the connect (summaries after it: $after, attempts: $n, longest round ${m:-0} ms)"; fi
