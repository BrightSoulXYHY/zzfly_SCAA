import cv2
import numpy as np
import pytesseract

import os
from loguru import logger


import time
import multiprocessing


num_th = 16

'''
算一个要300ms太慢了，直接开16个线程拉满
然后一个线程专门进行写入
'''



# time_prefix = "2022-09-03_00-20-33"
time_prefix = "2022-09-12_07-13-13"
img_dir = f"_video/img_{time_prefix}"


config = '--oem 3 --psm 6 outputbase digits'

def get_red(img):
    hsv_image = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lowMat = cv2.inRange(hsv_image, np.array([0, 200, 200]), np.array([0, 255, 255]))
    return lowMat


def get_time_score(img):
    time_gray = get_red(img[90:125, 1040:1180])
    score_gray = get_red(img[40:75, 1040:1180])

    mav_time_str = pytesseract.image_to_string(time_gray,config=config)
    score_str = pytesseract.image_to_string(score_gray,config=config)
    return mav_time_str.strip(),score_str.strip()


def write_proc(queue):
    fp = open(f"{time_prefix}.csv","w",encoding="utf-8")
    out_text = "date_str,time_str,seed_str,mav_time_str,score_str\n"
    fp.write(out_text)

    empty_cnt = 0
    while True:
        if queue.empty():
            empty_cnt += 1
            time.sleep(1)
            if empty_cnt > 3:
                logger.info(f"empty_cnt:{empty_cnt} !!!!")

        while not queue.empty():
            out_text = queue.get()
            fp.write(out_text)
            empty_cnt = 0

        if empty_cnt > 5:
            break
        
def img2csv_proc(img_nameL,queue,proc_name):
    start_time = time.time()
    for img_name in img_nameL:
        img = cv2.imread(f"{img_dir}/{img_name}")
        mav_time_str,score_str = get_time_score(img)
        date_str,time_str,seed_str = img_name.split(".")[0].split("_")
        seed_str = seed_str.split("=")[1]
        if mav_time_str == "":
            mav_time_str = "error"
        elif float(mav_time_str) > 60:
            mav_time_str = f"{float(mav_time_str)/10:.1f}"
        out_text = f"{date_str},{time_str},{seed_str},{mav_time_str},{score_str}\n"
        queue.put(out_text)
    logger.info(f"{proc_name} done with len={len(img_nameL)} time={time.time()-start_time:.2f}")




if __name__=="__main__":
    out_str_queue = multiprocessing.Queue()
    img_nameL = os.listdir(img_dir)
    uint_num = int(np.ceil(len(img_nameL)/num_th))
    logger.info(f"start with len={len(img_nameL)} unit={uint_num}")


    for i in range(num_th):
        start = i*uint_num
        end = np.min([i*uint_num+uint_num,len(img_nameL)-1])
        multiprocessing.Process(target=img2csv_proc,args=(img_nameL[start:end],out_str_queue,f"proc:{start}~{end}",)).start()

    write_proc(out_str_queue)


