#!/bin/bash

cd /GRF/data
git pull

cd /root/uAthena || exit 1
git reset --hard HEAD                 # discard local edits -> pristine tracked source
# NOTE: not using `git clean -fd` here — build artifacts (*.o, GNUmakefile, *-server_sql) are
# gitignored so `-fd` would SKIP them (needs -x), while `-fd` WOULD delete wanted untracked files
# (save/, eathena_mechanic_changes.md, .claude/). `make clean` below removes exactly the build output.

# Abort BEFORE touching the live server if the source/update or build fails — otherwise a failed
# build would fall through to stop+install and silently redeploy a stale/partial binary.
git pull || { echo "DEPLOY: 'git pull' failed (conflict/network) — aborting; server left untouched."; exit 1; }
make clean                            # surgically wipe ALL build artifacts (no stale .o can survive)
make || { echo "DEPLOY: BUILD FAILED — aborting BEFORE stop/install; server keeps running the OLD binary."; exit 1; }
./stop.sh
cd ./dumps
./dumps.sh update
cd ..
./update_logs.sh
make install
make update
./start.sh

