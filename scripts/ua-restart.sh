#!/bin/bash

SERVER="$1"

if [ "$2" == "sql" ]; then
 SQL="sql"
else
 SQL=""
fi

PID=$(ps x|grep "$1"|grep "-server"|awk -e'{print $1}')
if (( "$PID" > "0")); then
 kill -9 $PID
fi

rm -f /opt/uathena/bin/PID-${1}.pid

sleep 1

/opt/uathena/bin/ua-start.sh $1 $2 &
