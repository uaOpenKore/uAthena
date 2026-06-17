#!/bin/bash

cd /GRF/data
git pull

cd /root/uAthena || exit 1
make clean
# Abort BEFORE touching the live server if the source/update or build fails — otherwise a failed
# build would fall through to stop+install and silently redeploy a stale/partial binary.
git pull || { echo "DEPLOY: 'git pull' failed (conflict/network) — aborting; server left untouched."; exit 1; }
make || { echo "DEPLOY: BUILD FAILED — aborting BEFORE stop/install; server keeps running the OLD binary."; exit 1; }
cd ./dumps
./dumps.sh update
cd ..
./stop.sh
make install
make update
./start.sh

