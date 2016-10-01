#!/bin/bash

DIR="/Users/hugo/mitnk/lightsocks"
cd $DIR

ps_count=$(ps ax | grep -w 'local\.py.*lightsocks.*log' | wc -l)
if [ $ps_count -lt 1 ]; then
    echo "no local.py found, starting it ..."
    bash ./start_local.sh
else
    echo "found local.py"
fi
