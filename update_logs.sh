#!/bin/bash

cd /root/uAthena
./stop.sh
tar -czf /root/uAthena/logs/log.tar.gz -C /opt/uathena/bin/log .
git add logs/log.tar.gz
git commit -m "update logs"
git push

