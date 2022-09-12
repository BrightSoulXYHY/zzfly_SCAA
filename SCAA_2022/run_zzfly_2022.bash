#!/bin/bash
cd ~/zzfly_Dev/zzfly_2022
source ./devel/setup.bash
rosrun rfly_stage1 rfly_stage1.py & PID1=$!
wait
