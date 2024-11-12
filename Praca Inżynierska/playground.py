import cv2
import numpy as np
# # from flask import flask, render_template, request, jsonify, response
# # import json
# import threading as th
# import time

img = cv2.imread("C:\\Users\\jacek\\Downloads\\three_qr_codes.png")
if img is None:
    print("Nie udalo sie zaladowac obrazu!")

qcd = cv2.QRCodeDetector()
cv2.imwrite("XD.png",img)

    
ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(img)

if ret_qr:
    print(points)





