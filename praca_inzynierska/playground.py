import cv2

# Funkcja do obsługi zmian suwaka
def nothing(x):
    pass

# Otwórz kamerę (numer kamery może być różny w zależności od systemu)
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1920)

# Sprawdzenie, czy udało się otworzyć kamerę
if not cap.isOpened():
    print("Nie udało się otworzyć kamery!")
else:
    print("Kamera otwarta pomyślnie!")

# Utwórz okno, w którym będzie wyświetlany obraz
cv2.namedWindow('Frame')

# Utwórz suwak ostrości w oknie (zakres od 0 do 255) i ustaw skok na 5
cv2.createTrackbar('Focus', 'Frame', 0, 255, nothing)

# Odczyt klatki z kamery
while True:
    ret, frame = cap.read()
    if not ret:
        print("Nie udało się pobrać klatki!")
        break

    # Odczyt wartości z suwaka
    focus_value = cv2.getTrackbarPos('Focus', 'Frame')

    # Zaokrąglij wartość suwaka do najbliższego wielokrotności 5
    focus_value = (focus_value // 5) * 5  # Skok co 5

    # Ustawienie ostrości kamery na wartość z suwaka (jeśli kamera obsługuje tę funkcję)
    cap.set(cv2.CAP_PROP_FOCUS, focus_value)

    # Wyświetlanie klatki
    cv2.imshow('Frame', frame)

    # Jeśli użytkownik naciśnie 'q', zakończ
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Sprawdzenie aktualnej ostrości
    current_focus = cap.get(cv2.CAP_PROP_FOCUS)
    print(f"Obecna ostrość: {current_focus}")

# Zwalnianie kamery i zamykanie okna
cap.release()
cv2.destroyAllWindows()
