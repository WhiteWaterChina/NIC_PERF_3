#!/bin/bash
#check if the tools needed by iperf3 is installed!
which iperf3
if [ $? -ne 0 ]; then
	cd /tmp/tools/SKL/net
	tar -zxf iperf-3.3.tar.gz
	cd iperf-3.3
	chmod 777 *
	./configure &> /dev/null && make &> /dev/null && make install &> /dev/null || exit 1
fi
which ifconfig
if [ $? -ne 0 ]; then
    print "need ifconfig command!"
    exit 1
fi
which ip
if [ $? -ne 0 ]; then
    print "need ip command!"
    exit 1
fi
which ethtool
if [ $? -ne 0 ]; then
    print "need ethtool command!"
    exit 1
fi
which lspci
if [ $? -ne 0 ]; then
    print "need lspci command!"
    exit 1
fi
which dmesg
if [ $? -ne 0 ]; then
    print "need dmesg command!"
    exit 1
fi
which numactl
if [ $? -ne 0 ]; then
    print "need numactl command!"
    exit 1
fi
which killall
if [ $? -ne 0 ]; then
    print "need killall command!"
    exit 1
fi
exit 0