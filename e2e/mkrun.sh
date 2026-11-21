#!/bin/bash
# mkrun.sh <run-dir> <binary-source-dir>
# Builds an isolated server run dir: own binaries + own conf copy (localhost, Discord OFF) + log dir,
# db/ and npc/ linked read-only from the main tree.
set -e
RUN="$1"; BIN="$2"; SRC=/root/uAthena
rm -rf "$RUN"; mkdir -p "$RUN/log"
cp -p "$BIN/login-server_sql" "$BIN/char-server_sql" "$BIN/map-server_sql" "$RUN/"
cp -rp "$SRC/conf" "$RUN/conf"
ln -s "$SRC/db" "$RUN/db"
ln -s "$SRC/npc" "$RUN/npc"
# NEVER post to the real Discord channel from a test run.
cat > "$RUN/conf/discord.conf" <<'EOF'
discord_announce: no
discord_errors: no
discord_webhook:
EOF
: > "$RUN/conf/import/discord_conf.txt"
# everything on localhost
cat >> "$RUN/conf/import/char_conf.txt" <<'EOF'
login_ip: 127.0.0.1
char_ip: 127.0.0.1
EOF
cat >> "$RUN/conf/import/map_conf.txt" <<'EOF'
char_ip: 127.0.0.1
map_ip: 127.0.0.1
EOF
grep -q "discord_announce: no" "$RUN/conf/discord.conf" && echo "run dir ready: $RUN (discord off)"
