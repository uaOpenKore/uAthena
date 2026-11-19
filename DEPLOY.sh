#!/bin/bash
# DEPLOY.sh [--force | --check] - update the server from git, only when there is something new (S. 2026-11-19).
#
#   (no option)  git fetch the server source and the GRF data, then deploy (pull, build, stop, migrate,
#                install, start) only if one of them has commits the server does not run yet. Otherwise
#                nothing is built or stopped: the server keeps running.
#   --force      deploy even without new commits (e.g. after editing confs on the server)
#   --check      only report: exit 0 = there are new commits, 1 = none, 2 = cannot tell (fetch failed)
#
# What the server runs = the commits the last successful deploy wrote to /opt/uathena/bin/.ua-deployed. A deploy
# that fails (build, install, start) leaves that file as it was, so the next run tries again instead of finding
# the already pulled checkout "up to date". Without the file (the first run) the checked-out commits count.
#
# The map-server reads its maps from a map cache (conf/map_athena.conf read_map_from_cache / map_cache_file) that
# it builds from the GRF's .gat/.rsw on the first start; after that it never looks at those files again. So a
# deploy whose GRF commits touch .gat/.rsw (or one that can't tell what the server runs) removes the cache, and
# the map-server rebuilds it on this start.
#
# Paths (env, the tests point them elsewhere): UA_SRC_DIR (/root/uAthena), UA_GRF_DIR (/GRF/data),
# UA_DEPLOYED_FILE (/opt/uathena/bin/.ua-deployed), UA_MAPCACHE_FILE (/opt/uathena/bin/db/mapinfo.txt).

SRC_DIR="${UA_SRC_DIR:-/root/uAthena}"
GRF_DIR="${UA_GRF_DIR:-/GRF/data}"
DEPLOYED="${UA_DEPLOYED_FILE:-/opt/uathena/bin/.ua-deployed}"
MAPCACHE="${UA_MAPCACHE_FILE:-/opt/uathena/bin/db/mapinfo.txt}"

MODE=deploy
case "${1:-}" in
	"") ;;
	--force) MODE=force ;;
	--check) MODE=check ;;
	*) echo "usage: $0 [--force | --check]" >&2; exit 2 ;;
esac

# news <repo dir> <name>: fetch; print "<name> <deployed> -> <remote>" and succeed when the remote branch has
# commits the deployed one lacks. Status 1 = nothing new, 2 = could not fetch.
news() {
	local dir="$1" name="$2" up have
	git -C "$dir" fetch -q || return 2
	up=$(git -C "$dir" rev-parse -q --verify '@{u}') || return 2
	have=$([ -r "$DEPLOYED" ] && awk -v n="$name" '$1 == n { print $2 }' "$DEPLOYED")
	[ -n "$have" ] || have=$(git -C "$dir" rev-parse HEAD)
	# a deployed commit that already contains the remote one (e.g. a local commit on top) is up to date
	git -C "$dir" merge-base --is-ancestor "$up" "$have" 2>/dev/null && return 1
	echo "$name ${have:0:8} -> ${up:0:8}"
}

# grf_maps_changed: succeed when the checked-out GRF differs from the deployed one in a .gat/.rsw, or when that
# can't be told (no record, unknown commit) - the map cache may then be stale.
grf_maps_changed() {
	local have new files
	have=$([ -r "$DEPLOYED" ] && awk '$1 == "GRF" { print $2 }' "$DEPLOYED")
	[ -n "$have" ] || return 0
	new=$(git -C "$GRF_DIR" rev-parse HEAD 2>/dev/null) || return 0
	[ "$have" = "$new" ] && return 1
	files=$(git -C "$GRF_DIR" diff --name-only "$have" "$new" 2>/dev/null) || return 0
	grep -qiE '\.(gat|rsw)$' <<< "$files"
}

if [ "$MODE" != "force" ]; then
	found=""
	line=$(news "$SRC_DIR" uAthena); rc=$?
	if [ "$rc" -eq 2 ]; then
		echo "DEPLOY: cannot fetch $SRC_DIR - nothing deployed, the server keeps running."
		exit 2
	fi
	[ "$rc" -eq 0 ] && found="$line"
	line=$(news "$GRF_DIR" GRF); rc=$?
	[ "$rc" -eq 2 ] && echo "DEPLOY: WARN cannot fetch $GRF_DIR - deciding on uAthena alone."
	[ "$rc" -eq 0 ] && found="${found:+$found, }$line"
	if [ -z "$found" ]; then
		echo "DEPLOY: no new commits - nothing built or stopped, the server keeps running."
		[ "$MODE" = "check" ] && exit 1
		exit 0
	fi
	echo "DEPLOY: new commits: $found"
	[ "$MODE" = "check" ] && exit 0
fi

git -C "$GRF_DIR" pull

cd "$SRC_DIR" || exit 1
git reset --hard HEAD                 # discard local edits -> pristine tracked source
# NOTE: not using `git clean -fd` here — build artifacts (*.o, GNUmakefile, *-server_sql) are
# gitignored so `-fd` would SKIP them (needs -x), while `-fd` WOULD delete wanted untracked files
# (save/, eathena_mechanic_changes.md, .claude/). `make clean` below removes exactly the build output.

# Abort BEFORE touching the live server if the source/update or build fails — otherwise a failed
# build would fall through to stop+install and silently redeploy a stale/partial binary.
git pull || { echo "DEPLOY: 'git pull' failed (conflict/network) — aborting; server left untouched."; exit 1; }
make clean                            # surgically wipe ALL build artifacts (no stale .o can survive)
make || { echo "DEPLOY: BUILD FAILED — aborting BEFORE stop/install; server keeps running the OLD binary."; exit 1; }

# Keep the systemd units in sync BEFORE stop/start. `systemctl restart|stop uAthena.target`
# only controls all three servers when each service is PartOf=uAthena.target; a stale unit
# installed before that was added left the login/char servers running while only the map
# cycled (S.: "restart/stop должны перезапускать/останавливать ВСЕ процессы"). Reinstall the
# tracked units + daemon-reload + (re)enable so the target propagation is always current.
install -m644 scripts/uAlogin.service scripts/uAchar.service scripts/uAmap.service \
             scripts/uAthena.target /etc/systemd/system/
systemctl daemon-reload
systemctl enable uAlogin.service uAchar.service uAmap.service uAthena.target

./stop.sh
cd ./dumps
./dumps.sh update
cd ..
#./update_logs.sh
make install; installed=$?
make update; updated=$?
if [ -e "$MAPCACHE" ] && grf_maps_changed; then
	rm -f "$MAPCACHE" && echo "DEPLOY: map cache $MAPCACHE removed (GRF maps changed or unknown) - the map-server rebuilds it on this start."
fi
./start.sh; started=$?
if [ "$installed" -ne 0 ] || [ "$updated" -ne 0 ] || [ "$started" -ne 0 ]; then
	echo "DEPLOY: make install / make update / start.sh failed - not recorded as deployed, the next run tries again."
	exit 1
fi
# What the server runs now: the next DEPLOY compares the remotes with this, not with the checkout.
printf 'uAthena %s\nGRF %s\n' "$(git rev-parse HEAD)" "$(git -C "$GRF_DIR" rev-parse HEAD 2>/dev/null)" > "$DEPLOYED"
echo "DEPLOY: done, running uAthena $(git rev-parse --short HEAD), GRF $(git -C "$GRF_DIR" rev-parse --short HEAD 2>/dev/null)"
