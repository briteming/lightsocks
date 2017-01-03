#!/bin/bash
ps ax | grep 'local.py.*lightsocks.*log' | grep -vw 'grep' | awk '{print $1}' | xargs kill -9
sleep 1
nohup /usr/local/bin/py local.py -l /tmp/lightsocks-local.log > /dev/null &
echo "Done."
