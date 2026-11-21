#!/bin/bash
# run_batch.sh <run-dir> <grav-run-dir>: the e2e suite (run_suite64.sh) + the message/oob/timer/gravity tests.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; GRAV="$2"
bash "$E/run_suite64.sh" "$RUN"
for t in msgbuf smalloob timerstop; do
	r=$(bash "$E/run_msgbuf.sh" "$RUN" $t 2>&1 | tail -15)
	if echo "$r" | grep -q '^FAIL'; then echo "FAIL  $t $(echo "$r" | grep -m1 '^FAIL' | cut -c1-150)"; else echo "PASS  $t"; fi
done
r=$(bash "$E/run_msgbuf.sh" "$GRAV" gravity 2>&1 | tail -10)
if echo "$r" | grep -q '^FAIL'; then echo "FAIL  gravity $(echo "$r" | grep -m1 '^FAIL' | cut -c1-150)"; else echo "PASS  gravity"; fi
for t in sendbacklog haircolor; do
	r=$(bash "$E/run_msgbuf.sh" "$RUN" $t 2>&1 | tail -10)
	if echo "$r" | grep -q '^FAIL'; then echo "FAIL  $t $(echo "$r" | grep -m1 '^FAIL' | cut -c1-150)"; else echo "PASS  $t"; fi
done
bash "$E/srv.sh" start "$RUN" > /dev/null
r=$(cd "$E" && timeout 120 python3 -I preauth_e2e.py 5 2>&1 | tail -8)
bash "$E/srv.sh" stop "$RUN" > /dev/null
if echo "$r" | grep -q '^FAIL'; then echo "FAIL  preauth $(echo "$r" | grep -m1 '^FAIL' | cut -c1-150)"; else echo "PASS  preauth"; fi
