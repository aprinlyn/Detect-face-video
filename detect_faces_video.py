from imutils.video import FileVideoStream
import numpy as np
import argparse
import imutils
import time
import cv2
from datetime import date
import datetime
from os import walk
import os
import pymysql
# import numpy as np


ap = argparse.ArgumentParser()
ap.add_argument("-p", "--prototxt", required=True,
                help="direktori ke prototxt file")
ap.add_argument("-m", "--model", required=True,
                help="direktori ke caffe model")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
                help="mengatur minimal probalility deteksi wajah")
ap.add_argument("-t", "--afk_time", type=float, default=2.0,
                help="mengatur batas waktu afk untuk dicatat")
ap.add_argument("-k", "--run_hour", type=int, default=1,
                help="mengatur jam running")
ap.add_argument("-n", "--run_minute", type=int, default=1,
                help="mengatur menit running")
args = vars(ap.parse_args())

#============== CONNECT TO DB===========##
connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             db='phpmvc',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

cursordb = connection.cursor()


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


def push_to_db(uname, time, tag, count_head):
    username = uname[0:-4]
    time_start = convert(time[0])
    time_stop = convert(time[1])
    que = "INSERT INTO phpmvc.analysis (USERNAME, TIME_START, TIME_STOP, TAG, COUNT_HEAD) VALUES (%s,%s,%s,%s,%s)"
    value = (username, time_start, time_stop, tag, count_head)
    cursordb.execute(que, value)
    connection.commit()
# print("asd")
    info = "finish insert to database "
    return info


while True:

    countTemp = 0
    prevTemp = 0
    timediff = 0
    filesArr = []
    tempAbuse = []
    abuseArr = []
    tempAfk = []
    afkArr = []

    while True:
        now = datetime.datetime.now()
        print("running")
        if (now.hour == args["run_hour"]) and (now.minute == args["run_minute"]):
            entries = os.listdir("./"+str(date.today()))
            if len(entries) > 0:
                for files in entries:
                    filesArr.append(files)
                break

    print("[INFO] loading model...")
    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    print("[INFO] starting video stream...")

    for files in filesArr:
        vs = FileVideoStream("./"+str(date.today())+"/"+files).start()

        while vs.more():
            start = time.time()
            countTemp = 0
            frame = vs.read()
            if frame is None:
                break
            frame = imutils.resize(frame, width=400)
            (h, w) = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(
                frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))

            net.setInput(blob)
            detections = net.forward()

            for i in range(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                if confidence < args["confidence"]:
                    continue
                else:
                    countTemp = countTemp + 1

                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                text = "{:.2f}%".format(confidence * 100)
                y = startY - 10 if startY - 10 > 10 else startY + 10
                cv2.rectangle(frame, (startX, startY),
                              (endX, endY), (0, 0, 255), 2)
                cv2.putText(frame, text, (startX, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

            cv2.imshow("Frame", frame)
            key = cv2.waitKey(1) & 0xFF

            end = time.time()
            timediff = timediff + (end - start)

            if(prevTemp == 1 and countTemp >= 2):
                tempAbuse.append(round(timediff, 2))

            elif(prevTemp >= 2 and countTemp == 1):
                tempAbuse.append(round(timediff, 2))
                tag = "Abuse"
        # save to db
                push_to_db(files, tempAbuse, tag, prevTemp)
                abuseArr.append(tempAbuse)
                print(tag)
                print(tempAbuse)
                tempAbuse = []

            elif(prevTemp == 1 and countTemp == 0):
                tempAfk.append(round(timediff, 2))

            elif(prevTemp == 0 and countTemp == 1):
                tempAfk.append(round(timediff, 2))
                tag = "Afk"
                ppl = 1
                if((len(tempAfk) == 2) and (tempAfk[1]-tempAfk[0] > args["afk_time"])):
                    # save to db
                    push_to_db(files, tempAfk, tag, ppl)
                    afkArr.append(tempAfk)
                    print(tag)
                    print(tempAfk)
                tempAfk = []

            # print(countTemp)
            # print(" ")
            # print("arr Afk", afkArr)
            # print(" ")
            # print("arr Abuse", abuseArr)
            # print(" ")
            # print("nama", files)

            prevTemp = countTemp
    # print(countTemp)
    # print(" ")
    # print("arr Afk", afkArr)
    # print(" ")
    # print("arr Abuse", abuseArr)
    # print(" ")
    # print("nama", files)
# kirim server
