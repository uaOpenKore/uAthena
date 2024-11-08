#!/bin/bash

SERVER="char"
uAtype="_sql"
CONFS="./conf/char_athena.conf ./conf/inter_athena.conf"


DaTi=$(date +"%Y%m%d-%H%M%S%u")
PID="./PID-${SERVER}.pid"

#cd /opt/uathena/bin/

if [ ! -f $CONFS ]; then
 echo "Check for files: $CONFS"
 exit 2;
fi

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
echo "START - ${DaTi}" >> ./log/${SERVER}.log
./${SERVER}-server${uAtype} 2>&1 2>./log/${SERVER}${uAtype}-${DaTi}
mv ./log/${SERVER} /log/${SERVER}${uAtype}-${DaTi}.log

