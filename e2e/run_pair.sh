#!/bin/bash
# run_pair.sh <run-dir>: only the streak and the elemark e2e of run_suite64.sh (same one() with the inventory reset).
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
eval "$(sed -n '/^RUN=/,/^}/p' "$E/run_suite64.sh")"
RUN="$1"
gm 99
one streak python3 -I streak_e2e.py "$RUN" "$PT"
one elemark python3 -I elemark_e2e.py "$RUN" "$PT"
gm 0
