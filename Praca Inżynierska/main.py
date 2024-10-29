import array
import os
import cv2
import streamlit as st
import numpy as np


#streamlit layout
st.title('Widok z kamery')
placeholder = st.empty()

qcd = cv2.QRCodeDetector()
cap = cv2.VideoCapture(1)

ROIs = [(0,0,150,150),(350,0,150,150)]

while True:
    ret, frame = cap.read()
    for (x,y,w,h) in ROIs:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color=(255, 0, 0), thickness=2)

    for idx, (x,y,w,h) in enumerate(ROIs):
        if ret:
            tmp_frame = frame[y:y+h,x:x+w]
            tmp_frame = cv2.cvtColor(tmp_frame, cv2.COLOR_BGR2RGB)
            ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(tmp_frame)
            if ret_qr:
                for s, p in zip(decoded_info, points):
                    if s:
                        color = (0, 255, 0)
                        print('XD')
                    else:
                        color = (0, 0, 255)
                    frame = cv2.polylines(frame, [p.astype(int) + np.array((x,y))], True, color, 5)
                    frame = cv2.putText(frame,s,p[0].astype(int) + np.array((x,y)),1,2,color,2)

    placeholder.image(frame,channels="RGB")

