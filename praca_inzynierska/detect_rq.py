import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
from ultralytics import YOLO


def detect_qr(img, model, margin=10):
    #detections = decode(img, symbols=[ZBarSymbol.QRCODE])
    res = model.predict(source=img, conf=0.6, save=False)
    print("wykrywanie")

    rois = []

    for r in res:
        for box in r.boxes:
            cls = box.cls  # Klasa obiektu
            if cls == 0:  # Zakładamy, że kod QR ma odpowiedni indeks klasy (musisz dostosować)
                # Pobieranie współrzędnych z ramki
                x1, y1, x2, y2 = box.xyxy[0].numpy()

                # Dodanie marginesu
                x1 = max(int(x1) - margin, 0)
                y1 = max(int(y1) - margin, 0)
                x2 = min(int(x2) + margin, img.shape[1])
                y2 = min(int(y2) + margin, img.shape[0])

                rois.append((x1, y1, x2 - x1, y2 - y1))

    # Sortowanie wyników (opcjonalnie)
    rois.sort(key=lambda x: (-x[1], x[0]))

    return rois
