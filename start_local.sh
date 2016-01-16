#!/bin/bash
ps ax | grep 1080 | sort -n | head -n1 | awk '{print $1}' | xargs kill -9
sleep 1
nohup python2.7 local.py -p 1080 > /dev/null &
echo "Done."
