#!/bin/bash
# run_one.sh <run-dir> <name> <command...>: one suite test (the one() of run_suite64.sh) with GM 99, then GM 0.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
eval "$(sed -n '/^RUN=/,/^}/p' "$E/run_suite64.sh")"
RUN="$1"; shift
gm 99
one "$@"
gm 0
