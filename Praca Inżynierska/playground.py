import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
import pyzbar
import datetime

def detect_qr(img, margin=10):
    detections = decode(img, symbols=[ZBarSymbol.QRCODE])
    rois = []

    for detection in detections:
        # Współrzędne prostokąta otaczającego kod QR
        x, y, w, h = detection.rect

        # Dodanie marginesu
        x1 = max(x - margin, 0)
        y1 = max(y - margin, 0)
        x2 = min(x + w + margin, img.shape[1])
        y2 = min(y + h + margin, img.shape[0])
        
        rois.append((x1, y1, x2 - x1, y2 - y1))
       
    rois.sort(key=lambda x: (-x[1], x[0]))

    return rois


# Inicjalizacja kamery
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

while not cap.isOpened():
    print("czekam na otwarcie kamery")

start = datetime.datetime.now()
counter = 0
FinalDetectionROIs = []

while (datetime.datetime.now() - start).seconds < 5:
    ret, img = cap.read()
    if not ret:
        print("Nie udało się odczytać obrazu z kamery.")
        continue

    # Detekcja kodów QR za pomocą pyzbar
    rois = detect_qr(img, margin=10)
    FinalDetectionROIs.append(rois)
    counter += 1



MaxQRDetected = 0
for idx, x in enumerate(FinalDetectionROIs):
    if len(x) > MaxQRDetected:
        MaxQRDetected = len(x)
    else:
        FinalDetectionROIs.remove(x)

   
FinalDetectionROIs = FinalDetectionROIs.pop()

# Wyświetlenie wyników
print(FinalDetectionROIs)
print(f"Max Wykrytych Kodow {MaxQRDetected}")
print(counter)

# Zapis ostatniego obrazu


cap.release()

