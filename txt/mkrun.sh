#!/bin/bash
# mkrun.sh <run-dir> <worktree>
# Isolated TXT stand: the worktree's three TXT binaries + a copy of conf/ and save/, db/ and npc/ linked
# to the worktree. Discord OFF, everything on 127.0.0.1, NON-default ports (login 16900, char 16121,
# map 15121) so it never collides with another local stand. A run-dir-local test NPC (C1Test) is loaded.
set -e
RUN="$1"; WT="$2"
[ -n "$RUN" ] && [ -n "$WT" ] || { echo "usage: $0 <run-dir> <worktree>"; exit 2; }
rm -rf "$RUN"; mkdir -p "$RUN/log" "$RUN/e2e_npc"
cp -p "$WT/login-server" "$WT/char-server" "$WT/map-server" "$RUN/"
cp -rpL "$WT/conf" "$RUN/conf"
cp -rpL "$WT/save" "$RUN/save"
ln -s "$WT/db" "$RUN/db"
ln -s "$WT/npc" "$RUN/npc"

# NEVER post to the real Discord channel from a test run.
printf 'discord_announce: no\ndiscord_errors: no\ndiscord_webhook:\n' > "$RUN/conf/discord.conf"
: > "$RUN/conf/import/discord_conf.txt"

cat >> "$RUN/conf/import/login_conf.txt" <<'EOF'
login_port: 16900
EOF
cat >> "$RUN/conf/import/char_conf.txt" <<'EOF'
login_ip: 127.0.0.1
char_ip: 127.0.0.1
login_port: 16900
char_port: 16121
EOF
cat >> "$RUN/conf/import/map_conf.txt" <<'EOF'
char_ip: 127.0.0.1
map_ip: 127.0.0.1
char_port: 16121
map_port: 15121
npc: e2e_npc/c1test.txt
EOF

# Test helper NPC, driven by whispers to "npc:C1Test" ("<cmd>#<arg1>#<arg2>").
cat > "$RUN/e2e_npc/c1test.txt" <<'EOF'
-	script	C1Test	-1,{
OnWhisperGlobal:
	if (@whispervar0$ == "setquest") {
		setquest atoi(@whispervar1$);
		dispbottom "c1test: setquest " + @whispervar1$ + " -> " + checkquest(atoi(@whispervar1$));
		end;
	}
	if (@whispervar0$ == "completequest") {
		completequest atoi(@whispervar1$);
		dispbottom "c1test: completequest " + @whispervar1$ + " -> " + checkquest(atoi(@whispervar1$));
		end;
	}
	if (@whispervar0$ == "checkquest") {
		dispbottom "c1test: checkquest " + @whispervar1$ + " -> " + checkquest(atoi(@whispervar1$));
		end;
	}
	if (@whispervar0$ == "merc") {
		mercenary_create atoi(@whispervar1$), atoi(@whispervar2$);
		dispbottom "c1test: merc requested";
		end;
	}
	dispbottom "c1test: unknown command " + @whispervar0$;
	end;
}
EOF

if grep -rq "discord.com/api/webhooks" "$RUN/conf"; then
	echo "ABORT: a Discord webhook is still present in $RUN/conf"; exit 1
fi
echo "run dir ready: $RUN (discord off, ports 16900/16121/15121)"
