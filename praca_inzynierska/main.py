import platform
import time
import cv2
import numpy as np
import threading as th
import datetime
import os
from ultralytics import YOLO
import torch

from flask import Flask, render_template, request, Response
from pyzbar.pyzbar import decode, ZBarSymbol
from detect_rq import detect_qr
from communication import modbus_TCP_read_holding_registers, modbus_TCP_send_holding_registers
from write_config import write_config
from read_conifg import read_config


app = Flask(__name__)


cap = cv2.VideoCapture
if platform.system() == "Linux":
    # dla linuxa
    cap = cv2.VideoCapture(0)
elif platform.system() == "Windows":
    # dla windowsa
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)


cap.set(cv2.CAP_PROP_FPS, 20)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1920)

ROIs = [(10, 10, 155, 155)]
ROIs_temp = []

scanned_qr_zones_bools_final = [False] * 20

global_frame = None
frame_lock = th.Lock()  # Dodajemy blokadę dla global_frame

config = {
    "global_detection_mode": 0,
    "global_grayscale_mode": 0,
    "global_debug_mode": 0,
    "global_margin": 10
}


set_start_time = 1
start_time = datetime.datetime.now()

inspection = {
    "counter": 0,
    'on': False,
    'done': False,
    'lock': th.Lock()
}


model = YOLO("best.pt")

def optical_processing():
    global global_frame, ROIs, ROIs_temp, set_start_time, start_time, config, scanned_qr_zones_bools_final, inspection
    scanned_qr_zones_bools = [False] * 20
    scanned_qr_zones_str = [""] * 20

    while True:
        # Pobierz klatkę z kamery
        ret, frame = cap.read()
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        if config["global_detection_mode"] == 0:
            if ret:
                for idx, (x,y,w,h) in enumerate(ROIs):
                    tmp_frame = frame[y:y+h,x:x+w]
                    detected = decode(tmp_frame, symbols=[ZBarSymbol.QRCODE])
                    if not detected:
                        scanned_qr_zones_bools[idx] = False
                        scanned_qr_zones_str[idx] = ""
                    else:
                        scanned_qr_zones_bools[idx] = True
                        scanned_qr_zones_str[idx] = detected[0].data
                        frame = cv2.polylines(frame, [np.array(detected[0].polygon, dtype=np.int32) + np.array((x,y))], True,(0, 255, 0), 5)
                        frame = cv2.putText(frame, str(detected[0].data), detected[0].polygon[0] + np.array((x,y)),1,2,(0, 0, 255),2)

            with inspection['lock']:
                if inspection['on']:
                    print("Wlaczono inspekcje")
                    if inspection['counter'] == 0:
                        scanned_qr_zones_bools_final = [False] * 20

                    if inspection['counter'] < 5:
                        for idx, q in enumerate(scanned_qr_zones_bools):
                            if q:
                                scanned_qr_zones_bools_final[idx] = True
                        inspection['counter'] += 1
                    else:
                        inspection['on'] = False
                        inspection['counter'] = 0
                        inspection['done'] = True


            with frame_lock:
                global_frame = frame.copy()

        elif config["global_detection_mode"] == 1:
            if set_start_time:
                start_time = datetime.datetime.now()
                set_start_time = 0
                ROIs_temp.clear()

            if (datetime.datetime.now() - start_time).seconds < 2:
                ret, img = cap.read()
                img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                if not ret:
                    print("Nie udało się odczytać obrazu z kamery.")
                    continue

                #skala szarości
                if config["global_grayscale_mode"]:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


                # Detekcja kodów QR za pomocą pyzbar
                rois = detect_qr(img, model=model, margin=config["global_margin"])
                ROIs_temp.append(rois)

            else:
                MaxQRDetected = 0
                for idx, x in enumerate(ROIs_temp):
                    if len(x) > MaxQRDetected:
                        MaxQRDetected = len(x)
                    else:
                        ROIs_temp.remove(x)

                ROIs = ROIs_temp.pop()
                write_config("configs/rois.json",ROIs)
                set_start_time = 1
                config["global_detection_mode"] = 0


def debuging():
    global ROIs
    while True:
        if config["global_debug_mode"]:
            time.sleep(1)
            print(ROIs)
            if platform.system() == "Linux":
                os.system("clear")
            elif platform.system() == "Windows":
                os.system("cls")


def generate_frame_www():
    while True:
        with frame_lock:
            if frame_lock is None: 
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            else:
                frame = global_frame

        # skala szarości
        if config["global_grayscale_mode"]:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        for idx, (x, y, w, h) in enumerate(ROIs):
            cv2.rectangle(frame, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=2)
            cv2.putText(frame,f"strefa: {idx}",(x,y),1,2,(0,255,0),2,1,False)

        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def comm():
    global scanned_qr_zones_bools_final, inspection
    while True:
        # communication_MODBUS_TCP(scanned_qr_zones_bools_final,"192.168.10.10","502")
        with inspection['lock']:
            if not inspection['on'] and inspection['done']:
                modbus_TCP_send_holding_registers("192.168.10.10",502,0,scanned_qr_zones_bools_final+[0,1])
                inspection['done'] = False
            elif not inspection['on']:
                _, tmp = modbus_TCP_read_holding_registers("192.168.10.10",502,20,1)
                if tmp == [1]:
                    inspection['on'] = True
                    print(inspection['on'])

        time.sleep(1)

def init_model(model):
    model(torch.zeros((1, 3, 640, 640)))
    print("Koniec inicjalizacji modelu wykrywania QR")
            
@app.route('/', methods=['POST', 'GET'])
def index():
    global config

    if request.method == 'POST':
        form = request.form.get('form')

        #Odczyt wartści dla trybu detekcji
        if form == "tryby":
            config["global_detection_mode"] = int(request.form.get('tryby', default=0))

        #Odczyt wartości dla skali szarości
        elif form == "grayscale":
            config["global_grayscale_mode"] = int(request.form.get('grayscale', default=0))

        #Odczyt wartości dla trybu debug
        elif form == "debug":
            config["global_debug_mode"] = int(request.form.get('debug', default=0))

        #Odczyt wartości marginesu dla kodów QR
        elif form == "margin":
            config["global_margin"] = int(request.form.get('margin', default=0))

    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    # Endpoint do przesyłania strumienia wideo
    return Response(generate_frame_www(), mimetype='multipart/x-mixed-replace; boundary=frame')


threads = [
    th.Thread(target=optical_processing, daemon=True),
    th.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5001, 'threaded': True}, daemon=True),
    th.Thread(target=debuging, daemon=True),
    th.Thread(target=comm, daemon=True),
    th.Thread(target=init_model, kwargs={'model': model}, daemon=True)
]

if __name__ == "__main__":
    #Wczytanie konfiguracji
    if os.path.exists("configs/config.json"):
        config = read_config("configs/config.json")
        print(config)
    else:
        write_config("configs/config.json", config)

    #Wczytanie zapisanych punktów ROI
    if os.path.exists("configs/rois.json"):
        ROIs = read_config("configs/rois.json")
    else:
        write_config("configs/rois.json", ROIs)


    #Rozpoczęcie wątków
    for t in threads:
       t.start()

    for t in threads:
       t.join()
