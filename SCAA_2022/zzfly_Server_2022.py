import os
import time

import threading
import subprocess

import socket
import struct

from loguru import logger


import cv2

from zz_Common import *

import numpy as np
import win32gui
import win32process
import mss


import json
import websocket
import subprocess 
import time


'''
运行在WIN端，负责启动程序和记录视频&截图
'''


host_ip = "192.168.222.1"
sensor_type = "RGBD"
map_id = 1

sensorD = {
    "FPV":"./Settings/FPV.json",
    "RGBD":"./Settings/RGBD.json",
    "Stereo":"./Settings/Stereo.json",
}
json_path = sensorD[sensor_type]


time_prefix = time.strftime("%Y-%m-%d_%H-%M-%S")
out_dir = f"_video/{time_prefix}"

if not os.path.exists(out_dir):
    os.makedirs(out_dir)
    os.makedirs(f"{out_dir}/img_{time_prefix}")

class ZZFlyServer():
    def __init__(self,ip='0.0.0.0',port=63000):
        self.SAVING_RUN = None
        self.SAVING_DONE = None
        self.seed = 1
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind((ip,port))

                
        logger.info("Server Init Scuusee")

    def wait_client(self):
        logger.info("Wait for connecting")
        while True:
            data,address = self.server.recvfrom(BUFSIZE)
            if data == b"Hello Server":
                logger.info(f"Recv form {address[0]} on port {address[1]}")
                self.server.sendto(b'Server Received',address)
                break
        time.sleep(1)
    
    # 认为网络比较可靠
    def run(self):
        while True:
            data, _ = self.server.recvfrom(BUFSIZE)
            # print(f"len:{len(data)}",f"data:{bytearray(data).hex()}")
            head,msg_id,param1 = struct.unpack("!BBI",data)
            # print(msg_id)

            if  msg_id == cmdD["start"]:
                self.start_recv_cb()
            elif msg_id == cmdD["stop"]:
                self.stop_recv_cb()


            elif msg_id == cmdD["setseed"]:
                self.seed = str(param1)
                set_seed(self.seed)
                logger.info(f"set seed to {param1}")


            # elif msg_id == cmdD["setepoch"]:
            #     self.epoch = int(param1)
            
            # elif msg_id == cmdD["setcfg"]:
            #     self.cfg_int = int(param1)
            #     set_cfg(self.cfg_int)
            #     logger.info(f"set cfg_int to {self.cfg_int}")
            
    def start_recv_cb(self):
        logger.info("start!")
        self.save_th = threading.Thread(target=self.img_save_th)
        time.sleep(2)
        self.SAVING_RUN = True
        self.save_th.start()
        logger.info("start done!")


    
    def stop_recv_cb(self):
        self.SAVING_RUN = False
        # 等待img_save_th运行结束
        while not self.SAVING_DONE or self.save_th.is_alive():
            time.sleep(1)
        logger.info("stop!")

    def img_save_th(self):
        monitor = reset_env()

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = 24
        # width,height = 1280,720
        width,height = 640,360
        time_prefix = time.strftime("%Y-%m-%d_%H-%M-%S")
        video = cv2.VideoWriter(f"{out_dir}/{time_prefix}_seed={self.seed}.mp4", fourcc, fps, (width,height))
        self.SAVING_DONE = False


        time.sleep(1)
        
        lastTime = time.time()
        with mss.mss() as sct:
            lastTime = time.time()
            while self.SAVING_RUN:
                lastTime = lastTime + 1/fps
                sleepTime = lastTime - time.time()
                if sleepTime > 0:
                    time.sleep(sleepTime)
                else:
                    lastTime = time.time()

                img_rgba = np.array(sct.grab(monitor))
                img = cv2.cvtColor(img_rgba, cv2.COLOR_BGRA2BGR)
                last_img = img
                if (height,width) != img.shape[:2]:
                    img  = cv2.resize(img,(width,height),interpolation=cv2.INTER_CUBIC)
                video.write(img)

        video.release()
        cv2.imwrite(f"{out_dir}/img_{time_prefix}/{time_prefix}_seed={self.seed}.png",last_img)
        self.SAVING_DONE = True

def window_enumeration_handler(hwnd, window_hwnds): 
    class_name = window_hwnds[0]
    # print(hwnd,class_name==win32gui.GetWindowText(hwnd))
    # win32gui.GetClassName(hwnd) == "UnrealWindow"
    
    if class_name == None or win32gui.GetClassName(hwnd) == class_name:
        temp = {}
        temp["hwnd"] = hwnd
        temp["ClassName"] = win32gui.GetClassName(hwnd)
        temp["WindowText"] = win32gui.GetWindowText(hwnd)
        window_hwnds.append(temp)


def getWndHandls(class_name=None):
    window_hwnds = [class_name]
    # args = [class_name,window_hwnds]
    win32gui.EnumWindows(window_enumeration_handler, window_hwnds)
    window_hwnds.pop(0)
    # print(window_hwnds)
    return window_hwnds

def run_env_ue4():
    subprocess.Popen("run.bat", shell=True)

def kill_ue4():
    kill_cmd = "taskkill /f /pid {}"
    window_hwnds = getWndHandls("UnrealWindow")
    if len(window_hwnds) > 0:
        hwnd = window_hwnds[0]["hwnd"]
        for pid in win32process.GetWindowThreadProcessId(hwnd):
            os.system(kill_cmd.format(pid))

def reset_env():
    while True:
        try:
            ws_client = websocket.create_connection("ws://"+host_ip+":31245", timeout=3)
            break
        except Exception as e:
            print("connecting to {0}".format(host_ip))
            print(e)
            time.sleep(1)
        time.sleep(1)
    
    with open(json_path) as f:
        jdata = json.load(f)
        jdata['LocalHostIp'] = host_ip
        # jdata['Vehicles']["drone_1"].update(vehicle_dict)

    with open(json_path, "w") as f:
        json.dump(jdata,f, indent=4)

    
    ws_client.send(
        json.dumps({
            "command":"switch",
            "map":f"stage{map_id}",
            "sensor": sensor_type
        })
    )
    
    window_hwnds = getWndHandls("UnrealWindow")
    hwnd = window_hwnds[0]["hwnd"]
    # win32gui.SetForegroundWindow(hwnd)
    x1, y1, x2, y2 = win32gui.GetWindowRect(hwnd)
    monitor = {
        'left': x1+8,
        'top': y1+40,  
        'width': 1280, 
        'height': 720
    }
    return monitor
    
def set_seed(seed):
    with open("contest2/Content/seed.txt","w",encoding="utf-8") as f:
        f.write(str(seed))


def test_set_seed():
    run_env_ue4()
    for i in [1,10,100,1000,10000]:
        set_seed(i)
        reset_env()
        time.sleep(10)

if __name__ == '__main__':
    # 开启模拟器窗口
    kill_ue4()
    time.sleep(1)
    run_env_ue4()

    # 等待client循环运行
    zzServer = ZZFlyServer()
    zzServer.wait_client()
    zzServer.run()
    
    
    # for test and debug
    # ————————————————————————————————
    # time.sleep(5)
    # reset_env()

    # zzServer.start_recv_cb()
    # time.sleep(10)
    # zzServer.stop_recv_cb()
    # ————————————————————————————————