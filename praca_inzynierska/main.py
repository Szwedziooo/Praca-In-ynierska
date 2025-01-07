import platform
import time
import cv2
import flask
import numpy as np
import threading as th
import datetime
import os
from ultralytics import YOLO
import torch

from flask import Flask, render_template, request, Response
from pyzbar.pyzbar import decode, ZBarSymbol
from detect_rq import *
from communication import *
from write_config import *
from read_conifg import *


app = Flask(__name__)
app.secret_key = "Inzynierka"

cap = cv2.VideoCapture
if platform.system() == "Linux":
    # dla linuxa
    cap = cv2.VideoCapture(0)
    #komenda wyłączająca tryb autofocusa
    os.system("v4l2-ctl --set-ctrl=focus_automatic_continuous=0")
elif platform.system() == "Windows":
    # dla windowsa
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)


cap.set(cv2.CAP_PROP_FPS, 20)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1920)

ROIs = [(10, 10, 155, 155)]
ROIs_temp = []

scanned_qr_zones_bools_final = [False] * 20
scanned_qr_zones_str_final = [''] * 20

global_frame = None
frame_lock = th.Lock()  # Dodajemy blokadę dla global_frame

config = {
    "global_detection_mode": 0,
    "global_grayscale_mode": 0,
    "global_debug_mode": 0,
    "global_margin": 10,
    "comm_mode": 1,
    "focus": 45,
    'masking': False,
    'ip': "192.168.10.10"
}


set_start_time = 1
start_time = datetime.datetime.now()

inspection = {
    "counter": 0,
    'on': False,
    'done': False,
    'lock': th.Lock(),
    'match': False
}

masking_box = {
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0,
}

model = YOLO("best_ncnn_model")
model_empty = YOLO("best_empty_ncnn_model")
model_init_flag = False

def optical_processing():
    global global_frame, ROIs, ROIs_temp, set_start_time, start_time, config, scanned_qr_zones_bools_final, scanned_qr_zones_str_final, inspection, model, model_empty, model_init_flag
    scanned_qr_zones_bools = [False] * 20
    scanned_qr_zones_str = [""] * 20

    while True:
        #Pobierz klatkę z kamery
        ret, frame = cap.read()
        if ret:
            cap.set(cv2.CAP_PROP_FOCUS, config["focus"])
            #Obrót klatki o 90 stopni
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            #Dodanie maskowania obszaru
            if config['masking']:
                frame = cv2.rectangle(frame, (masking_box['x'], masking_box['y']), (masking_box['x'] + masking_box['width'], masking_box['y'] + masking_box['height']), (0, 0, 0), -1)

            #Pierwszy tryb - załączenie detekcji (z użyciem ROI)
            if config["global_detection_mode"] == 0:

                #Pętla odpowiedzialna za detekcje i dekodowanie kodów w strefach
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

                #Obsługa załączenia detekcji kodów QR z poziomu komunikacji
                if inspection['on']:
                    #rezerwacja operacji dla inspekcji (wtedy komunikacja jest zawieszona)
                    with inspection['lock']:
                        print("Wlaczono inspekcje")
                        if inspection['counter'] == 0:
                            scanned_qr_zones_bools_final = [False] * 20
                            scanned_qr_zones_str_final = [''] * 20
                            scanned_qr_zones_bools = [False] * 20
                            scanned_qr_zones_str = [""] * 20

                        #Wykonanie inspekcji na 5 róznych klatkach w celu wyeliminowania pomyłki
                        if inspection['counter'] < 5:
                            for idx, q in enumerate(scanned_qr_zones_bools):
                                if q:
                                    scanned_qr_zones_bools_final[idx] = True

                            for idx, q in enumerate(scanned_qr_zones_str):
                                if q != "":
                                    scanned_qr_zones_str_final[idx] = q.decode('utf-8')
                            inspection['counter'] += 1

                        #Załączenie wykrywania pustego miejsca oraz sumowanie pustych miejsc z wykrytymi kodami QR (suma musi równać się liczbie ROI)
                        elif inspection['counter'] == 5:

                            xd = model_empty.predict(source=frame, conf=0.7, save=False)

                            print(len(xd[0].boxes) + sum(scanned_qr_zones_bools_final))
                            print(len(ROIs))

                            if len(xd[0].boxes) + sum(scanned_qr_zones_bools_final) == len(ROIs):
                                inspection['match'] = False
                            else:
                                inspection['match'] = True

                            inspection['counter'] += 1
                        else:
                            inspection['on'] = False
                            inspection['counter'] = 0
                            inspection['done'] = True

                #Zablokowanie zmiennej na czas kopiowania przetworzonej ramki
                with frame_lock:
                    global_frame = frame.copy()

            #Drugi Tryb - Wykrywanie ROI
            elif config["global_detection_mode"] == 1:
                if model_init_flag:
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


                        # Detekcja kodów QR za pomocą modelu NCNN
                        rois = detect_qr(img, model=model, margin=config["global_margin"])
                        ROIs_temp.append(rois)

                    else:
                        #Usuwanie wszytkich list poza tą która ma najwięcej wykrytych kodów
                        MaxQRDetected = 0
                        for idx, x in enumerate(ROIs_temp):
                            if len(x) > MaxQRDetected:
                                MaxQRDetected = len(x)
                            else:
                                ROIs_temp.remove(x)

                        ROIs = ROIs_temp.pop()
                        #Zapis ROI do pliku
                        write_config("configs/rois.json",ROIs)
                        set_start_time = 1
                        config["global_detection_mode"] = 0
                else:
                    print("Model nie zostal jeszcze zainicjalizowany")
                    config["global_detection_mode"] = 0

            #Trzeci Tryb - Podgląd działania modelu wykrywania kodów QR
            elif config["global_detection_mode"] == 2:
                if model_init_flag:
                    #resized_frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
                    res = model.track(frame, stream=True)

                    frame = model_preview(res, frame)

                    with frame_lock:
                        global_frame = frame.copy()
                else:
                    print("Model nie zostal jeszcze zainicjalizowany")


#Funkcja rusująca boxy, pewności wykrycia oraz klase wykrytego obiektu dla modelu
def model_preview(results, frame):
    for result in results:
        classes_names = result.names

        for box in result.boxes:

            if box.conf[0] > 0.4:
                [x1, y1, x2, y2] = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (255,0,0), 2)

                cv2.putText(frame, f'{classes_names[int(box.cls[0])]} {box.conf[0]:.2f}', (x1, y1),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

    return frame


#Funkcja generująca obraz widziany na stronie www
def generate_frame_www():
    while True:
        #Sprawdzanie czy ramka nie jest nigdzie indziej przetwarzana
        with frame_lock:
            #Jeżeli ramka jest pusta zastąp ją pustą macierzą
            if global_frame is None:
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            else:
                frame = global_frame

        # skala szarości
        if config["global_grayscale_mode"]:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        #Rysowanie ROI dla pierwszego trybu
        if config["global_detection_mode"] == 0:
            for idx, (x, y, w, h) in enumerate(ROIs):
                cv2.rectangle(frame, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=2)
                cv2.putText(frame,f"strefa: {idx}",(x,y),1,2,(0,255,0),2,1,False)
        elif config["global_detection_mode"] == 2:
            pass

        #pokazanie zamaskowanego obszaru na klatce
        if config['masking']:
            frame = cv2.rectangle(frame, (masking_box['x'], masking_box['y']), (masking_box['x'] + masking_box['width'], masking_box['y'] + masking_box['height']), (0, 0, 0), -1)

        #kodowanie ramki do formatu .jpg
        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        #generowanie strumienia danych gotowego do przesłania do strony www
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

#funkcja komunikacji z PLC
def comm():
    global scanned_qr_zones_bools_final, scanned_qr_zones_str_final, inspection, config
    while True:
        #rezerwacja operacji podczas przesyłania danych (wtedy inspekcja jest zawieszona)
        with inspection['lock']:
            #Tryb Komunikacji - ModBus
            if config["comm_mode"] == 0:
                #Wysyłanie danych po zakończeniu inspekcji
                if not inspection['on'] and inspection['done']:
                    temp_list = []
                    for a in scanned_qr_zones_str_final:
                        if a == '':
                            temp_list.append(0)
                        else:
                            temp_list.append(int(a.replace('Box','')))

                    print(temp_list)
                    ret = modbus_TCP_send_holding_registers(config['ip'], 502, 101, temp_list)
                    ret = modbus_TCP_send_holding_registers(config['ip'],502,0, scanned_qr_zones_bools_final+[0,1,inspection['match']])
                    inspection['done'] = False
                #Nasłuchiwanie na rozpoczęcie inspekcji
                elif not inspection['on']:
                    ret, tmp = modbus_TCP_read_holding_registers(config['ip'],502,20,1)
                    print(tmp)
                    if ret:
                        if tmp[0]:
                            inspection['on'] = True
                            print(inspection['on'])

            #Tryb Komunikacji - Snap7
            elif config["comm_mode"] == 1:
                #Wysyłanie danych po zakończeniu inspekcji
                if not inspection['on'] and inspection['done']:
                    snap7_send_booleans(config['ip'],20,2, scanned_qr_zones_bools_final)
                    print(scanned_qr_zones_str_final)
                    snap7_send_strings(config['ip'],20, 4, scanned_qr_zones_str_final[0:12])
                    snap7_send_booleans(config['ip'], 20, 0, [1, 0, inspection['match']])
                    inspection['done'] = False
                #Nasłuchiwanie na rozpoczęcie inspekcji
                elif not inspection['on']:
                    # _, tmp = modbus_TCP_read_holding_registers("192.168.10.10",502,20,1)
                    ret, tmp = snap7_read_booleans(config['ip'], 20,0,2)
                    if ret:
                        if tmp[1]:
                            inspection['on'] = True
                            print(inspection['on'])
            else:
                print("Blad wyboru trybu komunikacji!")


        time.sleep(1)

#Fukcja, która inicjalizuje modele przy starcie programu
def init_model(model, model_empty):
    global model_init_flag

    model(torch.zeros((1, 3, 640, 480)))
    model_empty(torch.zeros((1, 3, 640, 480)))
    print("Koniec inicjalizacji modeli wykrywania QR oraz Pustego Miejsca")
    model_init_flag = True

#Funkcja, która odpowiada za wymiane informacji za pomocą Flaska między programem głównym a stroną www index.html
@app.route('/', methods=['GET', 'POST'])
def index():
    global config, model_init_flag, masking_box

    #Sprawdzanie czy zostały przesłane jakieś dane za pomocą formularza
    if request.method == 'POST':
        form = request.form.get('form')
        print(request.form)  # Zobacz wszystkie przesłane dane formularza

        #Odczyt wartści dla trybu detekcji
        if form == "tryby":
            config["global_detection_mode"] = int(request.form.get('tryby', default=0))
            if not model_init_flag and config["global_detection_mode"] == 1:
                flask.flash("Model nie został jeszcze zainicjalizowany.")

        #Odczyt wartości dla skali szarości
        elif form == "grayscale":
            config["global_grayscale_mode"] = int(request.form.get('grayscale', default=0))

        #Odczyt wartości marginesu dla kodów QR
        elif form == "margin":
            config["global_margin"] = int(request.form.get('margin', default=0))

        #Odczyt trybu komunikacji
        elif form == "comm":
            config["comm_mode"] = int(request.form.get('comm', default=0))

        #Odczyt wartości ustawnionego focusa
        elif form == "focus":
            config["focus"] = int(request.form.get('focus', default=0))
            print(config["focus"])

        #Odczyt parametrów maskowania
        elif form == "masking":
            config["masking"] = (request.form.get('active', default=0))
            masking_box['x'] = int(request.form.get('x', default=1))
            masking_box['y'] = int(request.form.get('y', default=1))
            masking_box['width'] = int(request.form.get('width', default=1))
            masking_box['height'] = int(request.form.get('height', default=1))

            print(config["masking"])
            print(masking_box)
            write_config("configs/masking_box.json", masking_box)
        #Odczyt ustawionego IP
        elif form == "ip":
            config["ip"] = request.form.get('ip', default="127.0.0.1")
            print(config['ip'])

    #Zapis bieżących parametrów w pliku konfiguracji
    write_config("configs/config.json", config)

    #Zwracanie kodu strony wraz z bieżącymi parametrami
    return render_template('index.html',**config, **masking_box)

#Funkcja odpowiedzialna a przesył strumienia wideo
@app.route('/video_feed')
def video_feed():
    # Endpoint do przesyłania strumienia wideo
    return Response(generate_frame_www(), mimetype='multipart/x-mixed-replace; boundary=frame')

#Główne wątki programu
threads = [
    th.Thread(target=optical_processing, daemon=True),
    th.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5001, 'threaded': True}, daemon=True),
    th.Thread(target=comm, daemon=True),
    th.Thread(target=init_model, kwargs={'model': model, 'model_empty':model_empty}, daemon=True)
]

if __name__ == "__main__":
    #Wczytanie konfiguracji
    if os.path.exists("configs/config.json"):
        config = read_config("configs/config.json")
        print(config)
    else:
        write_config("configs/config.json", config)

    cap.set(cv2.CAP_PROP_FOCUS, config["focus"])

    #Wczytanie zapisanych punktów ROI
    if os.path.exists("configs/rois.json"):
        ROIs = read_config("configs/rois.json")
    else:
        write_config("configs/rois.json", ROIs)

    # Wczytanie zapisanego rejonu maskowania
    if os.path.exists("configs/masking_box.json"):
        masking_box = read_config("configs/masking_box.json")
    else:
        write_config("configs/masking_box.json", masking_box)


    #Rozpoczęcie wątków
    for t in threads:
       t.start()

    for t in threads:
       t.join()
