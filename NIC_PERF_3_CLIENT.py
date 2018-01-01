#!/tmp/tools/env/tops/bin/python
# -*- coding:utf-8 -*-
###usage: sut_ctrl_ip sut_username sut_password sut_devicename_list client_devicename_list jumbo_max
import os
import sys
import re
import time
import paramiko
import subprocess


if len(sys.argv) != 7:
    print "Input length is incorrect!"
    print "Usage:%s sut_ctrl_ip sut_username sut_password sut_devicename_list client_devicename_list jumbo_max" % sys.argv[0]
    sys.exit(1)

sut_ctrl_ip = sys.argv[1]
sut_username = sys.argv[2]
sut_password = sys.argv[3]
sut_devicename_list = sys.argv[4]
client_devicename_list = sys.argv[5]
jumbo_max = sys.argv[6]

path = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir,os.pardir,'Lib_testcase'))
sys.path.append(path)
mtu_list = ["68", "128", "256", "512", "1500"]
if jumbo_max not in mtu_list:
    mtu_list.append(jumbo_max)

#get log path
with open("/tmp/tools/name", mode="r") as temp_file:
    log_dir_prefix = temp_file.readlines()[0].strip()

log_dir_prefix=log_dir_prefix + "/Stress/NIC_PERF_3"
if not os.path.isdir(log_dir_prefix):
    os.makedirs(log_dir_prefix)
#test input list length
if len(sut_devicename_list) != len(client_devicename_list):
    print "Input error! The length of sut_devicename_list need equal the length of client_devicename_list!"
    sys.exit(1)


for mtu_current in mtu_list:
    for index_sut_devicename, sut_devicename in enumerate(sut_devicename_list):
        client_devicename = client_devicename_list[index_sut_devicename]
        SutDevicePath = log_dir_prefix + '/Sut' + sut_devicename
        if not os.path.isdir(SutDevicePath):
            os.makedirs(SutDevicePath)
        ClientDevicePath = log_dir_prefix + '/Client' + client_devicename
        if not os.path.isdir(ClientDevicePath):
            os.makedirs(ClientDevicePath)
        logname_result_iperf_client = ClientDevicePath + "/" + "result_iperf_client_mtu_%s.txt" % mtu_current
        logname_result_iperf_sut = SutDevicePath + "/" + "result_iperf_sut_mtu_%s.txt" % mtu_current

        #set mtu client
        change_mtu_client = subprocess.Popen("ifconfig %s mtu %s" % (client_devicename, mtu_current), shell=True, stdout=subprocess.PIPE)
        check_mtu_client = subprocess.Popen("ip addr show|grep %s|grep mtu|awk '{match($0,/mtu\s*([0-9]*)/,a);print a[1]}'" % client_devicename, shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()

        if check_mtu_client != mtu_current:
            print "Client MTU for %s set failed! Please check! Need %s,but now %s" % (client_devicename, mtu_current, check_mtu_client)
            sys.exit(1)
        print "Client MTU for %s set %s successfully!" %(client_devicename, mtu_current)

        #login to sut to set mtu
        ssh_to_sut = paramiko.SSHClient()
        ssh_to_sut.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_to_sut.connect(sut_ctrl_ip, 22, username=sut_username, password=sut_password)
        ssh_to_sut.exec_command("ifconfig %s mtu %s" % (sut_devicename, mtu_current))
        time.sleep(2)
        stdin_checkmtu, stdout_checkmtu, stderr_checkmtu = ssh_to_sut.exec_command("ip addr show|grep %s|grep mtu|awk '{match($0,/mtu\s*([0-9]*)/,a);print a[1]}'" % sut_devicename)
        check_mtu_sut = stdout_checkmtu.readlines()[0].strip()
        ssh_to_sut.close()
        if check_mtu_sut != mtu_current:
            print "Sut MTU for %s set failed! Please check! Need %s,but now %s" % (sut_devicename, mtu_current, check_mtu_sut)
            sys.exit(1)
        print "Sut MTU for %s set %s successfully!" %(sut_devicename, mtu_current)

        #get sut test ip
        ssh_to_sut.connect(sut_ctrl_ip, 22, username=sut_username, password=sut_password)
        stdin_getip, stdout_getip, stderr_getip = ssh_to_sut.exec_command("ip addr show|grep %s|grep inet|awk '{match($s,/([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/,a);print a[1]}'" % sut_devicename)
        sut_test_ip = stdout_getip.readlines()[0].strip()
        ssh_to_sut.close()

        #start  iperf3
        # start iperf3 server in client
        subprocess.Popen("numactl --cpunodebind=netdev:%s --membind=netdev:%s iperf3 -s -i 5 --forceflush 5|grep -i sum &" % (sut_devicename, sut_devicename), shell=True, stdout=subprocess.PIPE)

        #login to sut to start server
        ssh_to_sut.connect(sut_ctrl_ip, 22, username=sut_username, password=sut_password)
        ssh_to_sut.exec_command(command='numactl --cpunodebind=netdev:%s --membind=netdev:%s iperf3 -s -i 5 --forceflush 5|grep -i sum &' % (sut_devicename, sut_devicename))
        ssh_to_sut.close()

        #client iperf
        #calculate N
        speed_now_list = subprocess.Popen(["ethtool", "%s" % client_devicename],stdout=subprocess.PIPE).stdout.readlines()
        pattern_speed = re.compile(r"Speed:\s*(\d*)Mb/s")
        N = 1
        for item_speed in speed_now_list:
            speed_temp = re.search(pattern=pattern_speed, string=item_speed)
            if speed_temp is not None:
                speed_now = speed_temp.groups()[0]
        if speed_now == "10000":
            N = 2
        elif speed_now == "25000":
            N = 3
        elif speed_now == "40000":
            N = 5
        elif speed_now == "100000":
            N = 11
        else:
            pass

        # get client test ip
        client_test_ip = subprocess.Popen("ip addr show|grep %s|grep inet|awk '{match($s,/([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/,a);print a[1]}'" % client_devicename, shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()
        # iperf -c in sut remotely
        ssh_to_sut.connect(sut_ctrl_ip, 22, username=sut_username, password=sut_password)
        ssh_to_sut.exec_command(command='numactl --cpunodebind=netdev:%s --membind=netdev:%s iperf3 -c %s -t 100 -i 5 --forceflush 5 -P %s |grep -i sum >> %s &' % (sut_devicename, sut_devicename, client_test_ip, N, logname_result_iperf_sut))
        ssh_to_sut.close()
        # iperf -c in client localy
        log_iperf = open(logname_result_iperf_client, mode="w")
        iperf_test_sut = subprocess.Popen("numactl --cpunodebind=netdev:%s --membind=netdev:%s iperf3 -c %s -t 100 -i 5 --forceflush 5 -P %s | grep -i sum" % (client_devicename, client_devicename, sut_test_ip, N) ,shell=True, stdout=log_iperf)
        iperf_test_sut.wait()
        log_iperf.close()
        #close iperf3 remotely
        # test if iperf3 ended in sut
        while 1 != 2:
            ssh_to_sut.connect(sut_ctrl_ip, 22, username=sut_username, password=sut_password)
            stdin, stdout_iperf3, stderr = ssh_to_sut.exec_command(command=' ps -aux|grep iperf3|grep -v grep')
            if len(stdout_iperf3) == 0:
                ssh_to_sut.close()
                break
            else:
                ssh_to_sut.close()
                time.sleep(10)
        ssh_to_sut.connect(sut_ctrl_ip, 22, username=sut_username, password=sut_password)
        ssh_to_sut.exec_command(command='killall -9 iperf3')
        ssh_to_sut.close()
        #close iperf3 -s client
        kill_iperf3_client = subprocess.Popen("killall -9 iperf3", shell=True, stdout=subprocess.PIPE)
sys.exit(0)