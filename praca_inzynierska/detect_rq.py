from pyzbar.pyzbar import decode, ZBarSymbol

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