#!/bin/bash

SERVER="$1"

PID=$(ps x|grep "$1"|grep "-server"|awk -e'{print $1}')
if (( "$PID" > "0")); then
 kill -9 $PID
fi

rm -f /opt/uathena/bin/PID-${1}.pid


