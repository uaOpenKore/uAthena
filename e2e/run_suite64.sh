#!/bin/bash
# run_suite64.sh <run-dir>: the e2e suite one test per fresh stand; prints PASS/FAIL per test.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; PT=/root/BornRok/src/net/PacketTable.cpp; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
gm() { $M -e "UPDATE login SET level=$1 WHERE account_id=2000006"; }
one() { # name, command...
	local name="$1"; shift
	bash "$E/srv.sh" stop "$RUN" > /dev/null
	# E2eTesterA (150003) collects items over the runs; overweight 90% made every skill fail (cause 9) -
	# each test starts with an empty inventory (the Emperium for the guild test stays).
	$M -e "DELETE FROM inventory WHERE char_id=150003 AND nameid<>714"
	# and from a calm spot: tests that warp (gravity: prt_fild08) leave it among field mobs
	$M -e "UPDATE \`char\` SET last_map='new_zone01', last_x=56, last_y=100 WHERE char_id=150003"
	bash "$E/srv.sh" start "$RUN" > /dev/null
	(cd "$E" && timeout 900 "$@" > "$RUN/suite_$name.log" 2>&1); local rc=$?
	bash "$E/srv.sh" stop "$RUN" > /dev/null
	if [ $rc -eq 0 ] && grep -q 'ALL PASSED\|ALL OK\|PASSED' "$RUN/suite_$name.log"; then echo "PASS  $name"; else echo "FAIL  $name (rc=$rc) $(grep -m2 'FAIL' "$RUN/suite_$name.log" | tr '\n' ' ' | cut -c1-200)"; fi
}
gm 99
one streak python3 -I streak_e2e.py "$RUN" "$PT"
one elemark python3 -I elemark_e2e.py "$RUN" "$PT"
one padmetric python3 -I padmetric_e2e.py "$RUN" "$PT"
gm 60
one whobot python3 -I whobot_e2e.py "$RUN" "$PT"
one whobot2 python3 -I whobot2_e2e.py "$RUN" "$PT"
gm 0
for t in npctimer fakenpc guildmaster storagefd0; do r=$(bash "$E/run_$t.sh" "$RUN" 2>&1 | tail -12); if echo "$r" | grep -q '^FAIL'; then echo "FAIL  $t $(echo "$r" | grep -m1 '^FAIL' | cut -c1-150)"; else echo "PASS  $t"; fi; done
one charload_race python3 -I charload_race_e2e.py
one charload_order python3 -I charload_race_e2e.py order
one charsel_latency python3 -I charsel_latency.py 5
gm 0
