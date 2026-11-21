#!/bin/bash
# run_npctimer.sh <run-dir>: load the TimerTest NPC, run npctimer_e2e.py with a level-99 GM, stop.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
mkdir -p "$RUN/e2e_npc"
cat > "$RUN/e2e_npc/timertest.txt" <<'NPC'
-	script	TimerTest	-1,{
	end;
OnWhisperGlobal:
	if (@whispervar0$ == "start") {
		attachnpctimer;
		initnpctimer;
		dispbottom "timertest started";
	}
	if (@whispervar0$ == "wed_old") {
		sc_start SC_Wedding,3600000000,1;
		dispbottom "wedding set (old 3600000000)";
	}
	if (@whispervar0$ == "wed_new") {
		sc_start SC_Wedding,3600000,1;
		dispbottom "wedding set (new 3600000)";
	}
	if (@whispervar0$ == "wedcheck") {
		dispbottom "wedding on=" + checkoption(0x1000);
		sc_end SC_Wedding;
	}
	if (@whispervar0$ == "gexp") {
		getexp 20000,20000;
		dispbottom "expnow " + BaseLevel + " " + BaseExp + " " + JobLevel + " " + JobExp;
	}
	if (@whispervar0$ == "exp") {
		dispbottom "expnow " + BaseLevel + " " + BaseExp + " " + JobLevel + " " + JobExp;
	}
	if (@whispervar0$ == "fake") {
		dispbottom "fakeprobe " + getnpctimer(1,"FAKE_NPC");
	}
	if (@whispervar0$ == "start2") {
		attachnpctimer;
		startnpctimer;
		dispbottom "timertest started2";
	}
	end;
OnTimer3000:
	dispbottom "timertest fired";
	stopnpctimer;
	end;
}
NPC
sed -i 's/^\(-\)\x20*script\x20*TimerTest\x20*-1,{/-\tscript\tTimerTest\t-1,{/' "$RUN/e2e_npc/timertest.txt"
grep -q 'e2e_npc/timertest.txt' "$RUN/conf/import/map_conf.txt" || echo 'npc: e2e_npc/timertest.txt' >> "$RUN/conf/import/map_conf.txt"
$M -e "UPDATE login SET level=99 WHERE account_id=2000006"
bash "$E/srv.sh" stop "$RUN" > /dev/null; bash "$E/srv.sh" start "$RUN" | tail -1
cd "$E" && timeout 200 python3 -I npctimer_e2e.py "$RUN" /root/BornRok/src/net/PacketTable.cpp; rc=$?
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
# the stale timer id is used again at the latest when the server shuts down: check the whole output
bad=$(grep -a -c 'delete_timer error\|ers::destroy' "$RUN/map.out")
if [ "$bad" -gt 0 ]; then echo "FAIL  timer bookkeeping errors in map.out: $bad"; grep -a 'delete_timer error\|ers::destroy' "$RUN/map.out" | head -3 | sed 's/^/    /'; rc=1
else echo "ok    no timer bookkeeping errors in map.out (incl. shutdown)"; fi
tail -1 "$RUN/map.out" | sed 's/^/    map last line: /'
exit $rc
