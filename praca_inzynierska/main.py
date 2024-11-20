import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
import threading as th
from enum import Enum
from playground import detect_qr
import datetime


app = Flask(__name__)


qcd = cv2.QRCodeDetector()
#dla linuxa
cap = cv2.VideoCapture(0)
#dla windowsa
#cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FPS, 10)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)


ROIs = [(1026, 599, 155, 155), (714, 557, 196, 193), (1083, 346, 137, 133), (779, 309, 178, 170), (841, 76, 159, 148)]
ROIs_temp = []
scaned_qr_zones_bools = [False] * 30
scaned_qr_zones_str = [""] * 30


global_frame = None
frame_lock = th.Lock()  # Dodajemy blokadę dla global_frame


global_detection_mode = 0

set_start_time = 1
start_time = datetime.datetime.now()



def optical_procesing():
    global global_frame, global_detection_mode, ROIs, ROIs_temp, set_start_time, start_time
    while True:
        # Pobierz klatkę z kamery
        ret, frame = cap.read()     
       
        if global_detection_mode == 0:
            if ret:
                for idx, (x,y,w,h) in enumerate(ROIs):
                    tmp_frame = frame[y:y+h,x:x+w]
                    ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(tmp_frame)
                    if ret_qr:
                        scaned_qr_zones_bools[idx] = True
                        scaned_qr_zones_str[idx] = decoded_info
                        for s, p in zip(decoded_info, points):
                            if s:
                                color = (0, 255, 0)
                            else:
                                color = (0, 0, 255)
                            frame = cv2.polylines(frame, [p.astype(int) + np.array((x,y))], True, color, 5)
                            frame = cv2.putText(frame,s,p[0].astype(int) + np.array((x,y)),1,2,color,2)
                    else:
                        scaned_qr_zones_bools[idx] = False
                        scaned_qr_zones_str[idx] = ""
                print(scaned_qr_zones_bools)
                print(scaned_qr_zones_str)
            with frame_lock:
                global_frame = frame.copy()  # Kopiujemy klatkę do global_frame

        elif global_detection_mode == 1:
            print("XD DEBUG")
            if set_start_time:
                start_time = datetime.datetime.now()
                set_start_time = 0
                ROIs_temp.clear()
                print((datetime.datetime.now() - start_time).seconds)

            if (datetime.datetime.now() - start_time).seconds < 5:
                ret, img = cap.read()
                if not ret:
                    print("Nie udało się odczytać obrazu z kamery.")
                    continue

                # Detekcja kodów QR za pomocą pyzbar
                rois = detect_qr(img, margin=10)
                ROIs_temp.append(rois)
           
            else:
                print("detect", ROIs_temp)
                MaxQRDetected = 0
                for idx, x in enumerate(ROIs_temp):
                    if len(x) > MaxQRDetected:
                        MaxQRDetected = len(x)
                    else:
                        ROIs_temp.remove(x)

                
                ROIs = ROIs_temp.pop()

                set_start_time = 1
                global_detection_mode = 0

            
def generate_frame_www():
    while True:
        with frame_lock:
            if frame_lock is None: 
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            else:
                frame = global_frame.copy() 


        print("www",ROIs)
        for idx, (x, y, w, h) in enumerate(ROIs):
            cv2.rectangle(frame, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=2)
            cv2.putText(frame,f"strefa: {idx}",(x,y),1,2,(0,255,0),2,1,False)

        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


            
@app.route('/', methods=['GET', 'POST'])
def index():
    global global_detection_mode
    # Główna strona, która wyświetli podgląd z kamery

    response_message = ""
    if request.method == 'POST':
        # Odczytanie wartości z <select>
        selected_value = request.form.get('tryby')
        response_message = f"Wybrano opcję: {selected_value}"
        print(response_message)
        global_detection_mode = int(selected_value)


    return render_template('index.html', response_message=response_message)


@app.route('/video_feed')
def video_feed():
    # Endpoint do przesyłania strumienia wideo
    return Response(generate_frame_www(), mimetype='multipart/x-mixed-replace; boundary=frame')



threads = [
    th.Thread(target=optical_procesing, daemon=True),
    th.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5001, 'threaded': True}, daemon=True)
]

if __name__ == "__main__":
   for t in threads:
       t.start()

   for t in threads:
       t.join()



