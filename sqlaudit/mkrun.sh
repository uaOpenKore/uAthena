#!/bin/bash
# mkrun.sh <run-dir> <worktree>
# Isolated SQL stand for the SQL audit: the worktree's three *_sql binaries + a copy of conf/, db/ and npc/
# linked to the worktree. Discord OFF, servers on 127.0.0.1 with NON-default ports (login 16900, char 16121,
# map 15121); every DB connection goes to the isolated audit MariaDB on 127.0.0.1:13306 (never the system one).
set -e
RUN="$1"; WT="$2"
[ -n "$RUN" ] && [ -n "$WT" ] || { echo "usage: $0 <run-dir> <worktree>"; exit 2; }
rm -rf "$RUN"; mkdir -p "$RUN/log"
cp -p "$WT/login-server_sql" "$WT/char-server_sql" "$WT/map-server_sql" "$RUN/"
cp -rpL "$WT/conf" "$RUN/conf"
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
EOF
cat >> "$RUN/conf/import/inter_conf.txt" <<'EOF'
login_server_ip: 127.0.0.1
login_server_port: 13306
char_server_ip: 127.0.0.1
char_server_port: 13306
map_server_ip: 127.0.0.1
map_server_port: 13306
log_db_ip: 127.0.0.1
log_db_port: 13306
mail_server_ip: 127.0.0.1
mail_server_port: 13306
EOF

if grep -rq "discord.com/api/webhooks" "$RUN/conf"; then
	echo "ABORT: a Discord webhook is still present in $RUN/conf"; exit 1
fi
if grep -rhE '^[a-z_]+_port: *3306' "$RUN/conf/inter_athena.conf" "$RUN/conf/import/inter_conf.txt" | grep -q .; then
	# inter_athena.conf keeps its 3306 lines; the import (read after it) must override every one of them.
	for k in login_server_port char_server_port map_server_port log_db_port mail_server_port; do
		grep -q "^$k: 13306" "$RUN/conf/import/inter_conf.txt" || { echo "ABORT: $k not overridden"; exit 1; }
	done
fi
echo "run dir ready: $RUN (discord off, ports 16900/16121/15121, DB 127.0.0.1:13306)"
