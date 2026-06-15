#!/bin/bash

cd /GRF/data
git pull

cd /root/uAthena
make clean
git pull
make
cd ./dumps
./dumps.sh update
cd ..
./stop.sh
make install
make update
./start.sh

