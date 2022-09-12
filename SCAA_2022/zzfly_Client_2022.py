import time
import subprocess

import socket
import struct

import os
import signal

import airsim
import numpy as np

from zz_Common import *


host_ip = "192.168.222.1"
# 差不多45s一次
# 一个小时80次
run_hour = 1
round_num = int(80*run_hour)
max_run_time = 45

# roswapper和直接运行的脚本
zzfly_env_path = ['./run_airsim_roswapper.bash', '-i', host_ip]
zzfly_run_path = './run_zzfly_2022.bash'
random_seed_path = "./random_seed.txt"


class ZZFlyClient():
    def __init__(self,tgt_ip='127.0.0.1',tgt_port=63000):
        '''
        ip 运行zzServer的IP，用于udp通信,和airsim的ip是一样的
        '''
        self.ip = tgt_ip


        self.client = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.client.connect((tgt_ip,tgt_port))
        self.client.setblocking(False)
        print(f"Try to connect Server {tgt_ip} on {tgt_port}")
    
    def connect(self):
        while True:
            message = b"Hello Server"
            self.client.sendall(message)
            time.sleep(1)
            try:
                data,address = self.client.recvfrom(BUFSIZE)
            except Exception as e:
                print("no connection")
                continue
            
            # 清空缓存区
            if data == b"Server Received":
                print("Server Received")
                break
    
    # 下面是流程控制的相关函数，发送给服务器进行相应的操作
    # ——————————————————————————————————————————
    def start_send(self,mode_id=CONTENT_STAGE1):
        self.contest_mode = mode_id
        msg_id = cmdD["start"]
        data_buff = struct.pack("!BBI",MSG_HEAD,msg_id,mode_id)
        # print(data_buff)
        self.client.sendall(data_buff)
    
    def stop_send(self,mode_id=CONTENT_STAGE1):
        self.contest_mode = mode_id
        msg_id = cmdD["stop"]
        data_buff = struct.pack("!BBI",MSG_HEAD,msg_id,mode_id)
        # print(data_buff)
        self.client.sendall(data_buff)
    
    def seed_send(self,seed=12):
        self.seed = seed
        msg_id = cmdD["setseed"]
        data_buff = struct.pack("!BBI",MSG_HEAD,msg_id,seed)
        self.client.sendall(data_buff)


def kill_task():
    os.system("ps -e | grep rfly | awk '{print $1}' | xargs kill -9")
    os.system("ps -e | grep airsim | awk '{print $1}' | xargs kill -9")
    os.system("ps -e | grep ros | awk '{print $1}' | xargs kill -9")


if __name__ == '__main__':

    # 可能没杀干净，重新杀一下
    kill_task()
    seedL = []
    if os.path.exists(random_seed_path):
        with open(random_seed_path,"r") as fp:
            seedL = [int(i) for i in fp.readlines()]
    seed_len = len(seedL)

    zzClient = ZZFlyClient(host_ip)
    zzClient.connect()
    # 开始流程控制
    for i in range(round_num):

        if seed_len == 0:
            seed = seedL[int(i%seed_len)]
        else:
            seed = np.random.randint(0xffff)

        zzClient.seed_send(seed)
        time.sleep(1)
        zzClient.start_send()
        print("satrt send")
        time.sleep(2)
        

        # 运行zzfly
        p2 = subprocess.Popen(zzfly_env_path)
        time.sleep(2)
        p1 = subprocess.Popen(zzfly_run_path)
        time.sleep(2)
        start_time = time.time()
        
        while True:
            time.sleep(1)
            # print(f"p1.poll():{p1.poll()}")

            # 超时或者任务跑完
            if time.time() - start_time > max_run_time or p1.poll() == 0:
                print(f"[{time.time()-start_time:.2f}] p1.poll() !!!!!!!")
                break

            
        os.kill(p2.pid, signal.SIGTERM)
        time.sleep(1)
        # os.kill(p1.pid, signal.SIGTERM)
        # os.killpg(os.getpgid(p2.pid), 9)
        kill_task()
        
        time.sleep(2)
        
        print("done")
        zzClient.stop_send()
        time.sleep(1)
