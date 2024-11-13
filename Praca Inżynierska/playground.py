import cv2
import numpy as np

img = cv2.imread("testqr1.png")
if img is None:
    print("Nie udalo sie zaladowac obrazu!")

def set_ROIs(img, margin = 10):
    func_qcd = cv2.QRCodeDetector()
    ret_qr, _, points, _ = func_qcd.detectAndDecodeMulti(img)
    func_ROIs = []

    if ret_qr:
        for a in points:
            #Obliczanie punktów ROI
            func_ROIs.append((int(a[0,0] - margin), int(a[0,1] - margin), int(a[1,0] - a[0,0] + 2*margin), int(a[3,1] - a[0,1] + 2*margin)))
            # print("X:", a[0,0]) #x
            # print("Y:", a[0,1]) #y
            # print("W:", a[1,0] - a[0,0]) #w
            # print("H:", a[3,1] - a[0,1]) #h

        func_ROIs.sort(key=lambda x: (-x[1], x[0]))
    
        for idx, a in enumerate(func_ROIs):
            #Rysowanie punktów ROI
            img = cv2.rectangle(img, 
                                (a[0], a[1]),
                                (a[0] + a[2], a[1] + a[3]),
                                color=(255,0,0), 
                                thickness=2)
            img = cv2.putText(img,f"strefa{idx}",(a[0],a[1]),1,2,(255,0,0),2)
    return func_ROIs, img


rois, img = set_ROIs(img=img)

cv2.imwrite("XD.png",img)
print(rois)
