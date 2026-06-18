#!/bin/bash

apt update
apt upgrade -y

cd /root/uAthena

./DEPLOY.sh
./stop.sh
./update_logs.sh
restart