#!/bin/bash

cd /root/uAthena
./stop.sh
tar -czf /root/uAthena/logs/log.tar.gz -C /opt/uathena/bin/log .
git add .
git commit -m "update logs"
git push

rm -rf /opt/uathena/bin/log

