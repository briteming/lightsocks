#!/bin/bash
ps ax | grep 'local.py' | grep -vw 'grep' | awk '{print $1}' | xargs kill -9
sleep 1
nohup py local.py -l /tmp/lightsocks-local.log > /dev/null &
echo "Done."
