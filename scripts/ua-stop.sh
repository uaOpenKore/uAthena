#!/bin/bash

SERVER="$1"

PIDS=$(pgrep -f "${SERVER}-server")
if [ -n "$PIDS" ]; then
 # SIGTERM lets the server run do_final(): flush buffered SQL logs,
 # save online chars, close inter-server links. SIGKILL only if it hangs.
 kill -TERM $PIDS
 for i in $(seq 1 60); do
  pgrep -f "${SERVER}-server" >/dev/null || break
  sleep 1
 done
 PIDS=$(pgrep -f "${SERVER}-server")
 if [ -n "$PIDS" ]; then
  echo "${SERVER}-server did not exit within 60s, sending SIGKILL"
  kill -KILL $PIDS
 fi
fi

rm -f /opt/uathena/bin/PID-${SERVER}.pid
