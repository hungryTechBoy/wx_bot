#!/bin/bash
CURDIR=$(cd $(dirname $0); pwd)
mkdir -p $CURDIR/logs
ps aux | grep wx_wechaty.py |grep python| awk  '{print $2}' | xargs kill -15
cd ${CURDIR}
nohup python3  wx_wechaty.py &
echo "$(date -R) :restart wx_bot" >> logs/reboot.log
