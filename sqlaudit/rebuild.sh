#!/bin/bash
# rebuild.sh - apply /root/uAthena's uncommitted changes to the scratch worktree, `make sql` there and copy the
# three binaries into run-new. The worktree is reset to its HEAD first, so it always mirrors the main checkout.
SP=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit
set -e
git -C /root/uAthena diff > "$SP/current.diff"
HEAD_SHA=$(git -C /root/uAthena rev-parse HEAD)
cd "$SP/src"
git checkout -q -- . && git checkout -q --detach "$HEAD_SHA"
git apply "$SP/current.diff"
if make sql -j8 > "$SP/logs/rebuild.log" 2>&1; then echo "build ok"; else echo "BUILD FAILED"; grep -n 'error' "$SP/logs/rebuild.log" | head -20; exit 1; fi
grep -n 'warning' "$SP/logs/rebuild.log" | grep -E "$(git diff --name-only | xargs -n1 basename | paste -sd'|')" | grep -v 'pointer-to-int-cast\|int-to-pointer-cast' | head -20 || true
cp -p login-server_sql char-server_sql map-server_sql "$SP/run-new/"
md5sum "$SP/run-new/"*-server_sql | sed "s|$SP/||"
