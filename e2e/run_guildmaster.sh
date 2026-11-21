#!/bin/bash
# run_guildmaster.sh <run-dir>: set up guilds 996/997 in the local DB, run guildmaster_e2e.py, clean up.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
cleanup() {
	for t in guild guild_member guild_position guild_skill guild_alliance guild_expulsion; do $M -e "DELETE FROM $t WHERE guild_id IN (996,997)"; done
	$M -e "UPDATE \`char\` SET guild_id=0 WHERE char_id IN (150003,150004)"
}
bash "$E/srv.sh" stop "$RUN" > /dev/null
cleanup
$M -e "INSERT INTO guild (guild_id,name,char_id,master,guild_lv,connect_member,max_member,average_lv,exp,next_exp,skill_point,mes1,mes2,emblem_len,emblem_id) VALUES
 (996,'BreakMe',150004,'E2eTesterV',1,0,16,1,0,100,0,'','',0,0),
 (997,'Target',150003,'E2eTesterA',1,0,16,1,0,100,0,'orig','orig',0,0);
INSERT INTO guild_member (guild_id,account_id,char_id,hair,hair_color,gender,class,lv,exp,exp_payper,online,position,rsv1,rsv2,name) VALUES
 (996,2000007,150004,1,1,0,0,1,0,0,0,0,0,0,'E2eTesterV'),
 (997,2000006,150003,1,1,0,0,1,0,0,0,0,0,0,'E2eTesterA');
INSERT INTO guild_position (guild_id,position,name,mode,exp_mode) VALUES (996,0,'GM',17,0),(996,1,'Member',0,0),(997,0,'GM',17,0),(997,1,'Member',0,0);
UPDATE \`char\` SET guild_id=996 WHERE char_id=150004; UPDATE \`char\` SET guild_id=997 WHERE char_id=150003;"
bash "$E/srv.sh" start "$RUN" | tail -1
cd "$E" && timeout 200 python3 -I guildmaster_e2e.py /root/BornRok/src/net/PacketTable.cpp; rc=$?
bash "$E/srv.sh" stop "$RUN" > /dev/null
cleanup
tail -1 "$RUN/map.out" | sed 's/^/    map last line: /'
exit $rc
