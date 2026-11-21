#!/bin/bash
# run_s2sauth.sh <run> : the s2s login test from a "remote" host (network namespace s2stest, 10.199.0.2 -> 10.199.0.1)
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; rc=0
bash "$E/srv.sh" stop "$RUN" > /dev/null; bash "$E/srv.sh" start "$RUN" | tail -1
(cd "$E" && ip netns exec s2stest timeout 60 python3 -I s2sauth_e2e.py 10.199.0.1) || rc=1
P=""; for p in $(pgrep -f char-server_sql); do [ "$(readlink /proc/$p/cwd)" = "$(readlink -f "$RUN")" ] && P=$p; done
kill -9 "$P"; sleep 2
(cd "$E" && ip netns exec s2stest timeout 60 python3 -I s2sauth_e2e.py 10.199.0.1 login) || rc=1
(cd "$E" && timeout 60 python3 -I s2sauth_e2e.py 127.0.0.1 login | grep '^3') # this host still can (char is down)
bash "$E/srv.sh" stop "$RUN" > /dev/null
grep -a 'refused from' "$RUN/char.out" "$RUN/login.out" | cut -c1-140
exit $rc
