#!/bin/bash

SERVER="$1"

if [ "$2" == "sql" ]; then
 uAtype="_sql"
fi

PID="./PID-${SERVER}.pid"

#cd /opt/uathena/bin/

if [ -f $PID ]; then
 fPID=$(cat $PID)
 nPID=$(ps ax|grep -v grep|grep "-server"|grep "${fPID}"|awk -e'{print $1}')
 pPID=$(ps ax|grep -v grep|grep "${SERVER}-server"|awk -e'{print $1}')
if [[ "${pPID}" > "0" || "${nPID}" == "${fPID}" ]] ; then
  echo "${SERVER}-server process exists"
  exit 0;
 fi
fi

echo "$$" >${PID}
./${SERVER}-server${uAtype}

