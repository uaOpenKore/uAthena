#!/bin/bash
# run_msgbuf.sh <run-dir> [msgbuf|smalloob [parts]|timerstop|gravity]: load the MsgTest NPCs, run msgbuf_e2e.py (or smalloob_e2e.py)
# with a level-99 GM, stop, check map.out for a crash.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
mkdir -p "$RUN/e2e_npc"
printf '%s\n' \
'new_zone01,57,100,4	script	Funny Gatekeeper'"'"'s Friend#lv20	71,{' \
'	end;' \
'OnInit:' \
'	initnpctimer;' \
'	end;' \
'OnTimer1000:' \
'	npctalk "hello";' \
'	initnpctimer;' \
'	end;' \
'}' \
'new_zone01,59,100,4	script	LongTalk#t	71,{' \
'	end;' \
'OnSay:' \
'	set .@s$, "";' \
'	set .@i, 0;' \
'L_More:' \
'	set .@s$, .@s$ + "0123456789";' \
'	set .@i, .@i + 1;' \
'	if (.@i < 25) goto L_More;' \
'	npctalk .@s$;' \
'	end;' \
'}' \
'-	script	StopTest	-1,{' \
'	end;' \
'OnWhisperGlobal:' \
'	if (@whispervar0$ == "init") { set $@f1, 0; set $@f5, 0; initnpctimer; }' \
'	if (@whispervar0$ == "stop") stopnpctimer;' \
'	if (@whispervar0$ == "start") startnpctimer;' \
'	dispbottom "tmr " + getnpctimer(0) + " " + $@f1 + " " + $@f5;' \
'	end;' \
'OnTimer1000:' \
'	set $@f1, $@f1 + 1;' \
'	end;' \
'OnTimer5000:' \
'	set $@f5, $@f5 + 1;' \
'	end;' \
'OnTimer8000:' \
'	end;' \
'}' \
'-	script	GravTest	-1,{' \
'	end;' \
'OnWhisperGlobal:' \
'	getmapxy(.@m$, .@x, .@y, 0);' \
'	if (@whispervar0$ == "grav") unitskillusepos getcharid(3), 484, 5, .@x + 6, .@y;' \
'	if (@whispervar0$ == "pupa") monster .@m$, .@x + 9, .@y, "GravPupa", 1008, 1;' \
'	if (@whispervar0$ == "lp") unitskillusepos atoi(@whispervar1$), 288, 5, .@x + 9, .@y;' \
'	if (@whispervar0$ == "gb") unitskillusepos atoi(@whispervar1$), 483, 1, .@x + atoi(@whispervar2$), .@y + atoi(@whispervar3$);' \
'	if (@whispervar0$ == "fb") unitskilluseid atoi(@whispervar1$), 19, 1, getcharid(3);' \
'	dispbottom "grav " + @whispervar0$ + " at " + .@x + "," + .@y;' \
'	end;' \
'}' \
'-	script	MsgTest	-1,{' \
'	end;' \
'OnWhisperGlobal:' \
'	if (@whispervar0$ == "long") donpcevent "LongTalk#t::OnSay";' \
'	if (@whispervar0$ == "unit") {' \
'		set .@s$, "";' \
'		set .@i, 0;' \
'		L_U:' \
'		set .@s$, .@s$ + "abcdefghij";' \
'		set .@i, .@i + 1;' \
'		if (.@i < 25) goto L_U;' \
'		unittalk getcharid(3), .@s$;' \
'	}' \
'	if (@whispervar0$ == "self") dispbottom "self " + @whispervar1$;' \
'	if (@whispervar0$ == "away") {' \
'		set .@s$, "";' \
'		set .@i, 0;' \
'		L_A:' \
'		set .@s$, .@s$ + "xxxxxxxx";' \
'		set .@i, .@i + 1;' \
'		if (.@i < 16) goto L_A;' \
'		atcommand "@away " + .@s$;' \
'		dispbottom "away set " + getstrlen(.@s$);' \
'	}' \
'	if (@whispervar0$ == "awayoff") atcommand "@away";' \
'	if (@whispervar0$ == "flood") {' \
'		set .@i, 0;' \
'		L_F:' \
'		dispbottom "flood 0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890";' \
'		set .@i, .@i + 1;' \
'		if (.@i < 300) goto L_F;' \
'	}' \
'	if (@whispervar0$ == "hair") { setlook 6, atoi(@whispervar1$); dispbottom "hair " + getlook(6); }' \
'	if (@whispervar0$ == "ping") dispbottom "pong";' \
'	end;' \
'}' > "$RUN/e2e_npc/msgtest.txt"
grep -q 'e2e_npc/msgtest.txt' "$RUN/conf/import/map_conf.txt" || echo 'npc: e2e_npc/msgtest.txt' >> "$RUN/conf/import/map_conf.txt"
$M -e "UPDATE login SET level=99 WHERE account_id=2000006"
$M -e "DELETE FROM inventory WHERE char_id=150003 AND nameid<>714"
guild_cleanup() { # the smalloob notice check makes E2eTesterA master of "OobNotice": drop it (servers stopped)
	for g in $($M -N -e "SELECT guild_id FROM guild WHERE name='OobNotice'"); do
		$M -e "DELETE FROM guild_member WHERE guild_id=$g; DELETE FROM guild_position WHERE guild_id=$g; DELETE FROM guild_skill WHERE guild_id=$g; DELETE FROM guild WHERE guild_id=$g"
	done
	$M -e "UPDATE \`char\` SET guild_id=0 WHERE char_id=150003 AND guild_id NOT IN (SELECT guild_id FROM guild)"
}
bash "$E/srv.sh" stop "$RUN" > /dev/null; bash "$E/srv.sh" start "$RUN" | tail -1
if [ "${2:-msgbuf}" != msgbuf ]; then # smalloob [parts] | timerstop
	cd "$E" && timeout 300 python3 -I "$2_e2e.py" /root/BornRok/src/net/PacketTable.cpp $3; rc=$?
	bash "$E/srv.sh" stop "$RUN" > /dev/null
	guild_cleanup
	$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
	bad=$(grep -a -c 'stack smashing\|Segmentation\|CRASH' "$RUN/map.out")
	if [ "$bad" -gt 0 ]; then echo "FAIL  map-server crashed: $(grep -a -m1 'stack smashing\|Segmentation\|CRASH' "$RUN/map.out")"; rc=1
	else echo "ok    no crash in map.out"; fi
	if [ "$2" = gravity ]; then
		g=$(grep -a -c 'skill_delunitgroup' "$RUN/map.out")
		if [ "$g" -gt 0 ]; then echo "FAIL  skill_delunitgroup errors in map.out: $(grep -a -m1 'skill_delunitgroup' "$RUN/map.out")"; rc=1
		else echo "ok    no skill_delunitgroup errors in map.out"; fi
	fi
	exit $rc
fi
cd "$E" && timeout 200 python3 -I msgbuf_e2e.py /root/BornRok/src/net/PacketTable.cpp npc; rc=$?
bash "$E/srv.sh" stop "$RUN" > /dev/null
crash1=$(grep -a -c 'stack smashing\|Segmentation\|CRASH' "$RUN/map.out")
bash "$E/srv.sh" start "$RUN" | tail -1
cd "$E" && timeout 200 python3 -I msgbuf_e2e.py /root/BornRok/src/net/PacketTable.cpp unit; rc2=$?
[ $rc2 -ne 0 ] && rc=$rc2
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "UPDATE login SET level=0 WHERE account_id=2000006"
bad=$(( crash1 + $(grep -a -c 'stack smashing\|Segmentation\|CRASH' "$RUN/map.out") ))
if [ "$bad" -gt 0 ]; then echo "FAIL  map-server crashed: $(grep -a -m1 'stack smashing\|Segmentation\|CRASH' "$RUN/map.out")"; rc=1
else echo "ok    no crash in map.out"; fi
exit $rc
