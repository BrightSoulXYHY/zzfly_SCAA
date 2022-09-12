#!/bin/bash

IP="127.0.0.1"

while getopts "i:" opt; do
	case $opt in
		i)
			IP="$OPTARG"
			;;
		\?)
			echo "Invalid option: -$OPTARG" >&2
			exit 1
			;;
	esac
done
echo "\$IP: "$IP

cd ~/zzfly_Dev/simulator/roswrapper/simulator_ros
source ./devel/setup.bash
roslaunch airsim_ros_pkgs airsim_node.launch  host_ip:=${IP} & PID0=$!
wait
kill -9 $PID1
