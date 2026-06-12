#!/bin/bash

SERVER="$1"

/opt/uathena/bin/ua-stop.sh "$SERVER"

sleep 1

/opt/uathena/bin/ua-start.sh "$1" "$2" &
