import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
import json
import threading as th

app = Flask(__name__)

qcd = cv2.QRCodeDetector()
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

ROIs = [(0,0,150,150),(350,0,150,150)]

global_frame = None
frame_lock = th.Lock()  # Dodajemy blokadę dla global_frame

def optical_procesing():
    global global_frame
    while True:
        # Pobierz klatkę z kamery
        ret, frame = cap.read()

        if ret:
            for idx, (x,y,w,h) in enumerate(ROIs):
                tmp_frame = frame[y:y+h,x:x+w]
                ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(tmp_frame)
                if ret_qr:
                    for s, p in zip(decoded_info, points):
                        if s:
                            color = (0, 255, 0)
                        else:
                            color = (0, 0, 255)
                        frame = cv2.polylines(frame, [p.astype(int) + np.array((x,y))], True, color, 5)
                        frame = cv2.putText(frame,s,p[0].astype(int) + np.array((x,y)),1,2,color,2)
        with frame_lock:
            global_frame = frame.copy()  # Kopiujemy klatkę do global_frame
            
def generate_frame_www():
    while True:
        with frame_lock:
            frame = global_frame.copy() 
            if global_frame is None: 
                np.zeros((480, 640, 3), dtype=np.uint8)
        for (x, y, w, h) in ROIs:
            cv2.rectangle(frame, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=2)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


            
@app.route('/')
def index():
    # Główna strona, która wyświetli podgląd z kamery
    return render_template('index.html')

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



