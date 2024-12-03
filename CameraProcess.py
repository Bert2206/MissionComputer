import cv2
from datetime import datetime

# Strumień GStreamer do przechwytywania obrazu z kamery
gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! video/x-raw,format=BGR ! appsink"

# Przechwytywanie strumienia w OpenCV
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Nie można otworzyć kamery. Sprawdź połączenie i konfigurację GStreamer.")
    exit()

# Pobranie natywnej rozdzielczości kamery
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Rozdzielczość kamery: {frame_width}x{frame_height}")

# Parametry kodowania H.264
fourcc = cv2.VideoWriter_fourcc(*'H264')
out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (frame_width, frame_height))

print("Nagrywanie rozpoczęte. Naciśnij Ctrl+C w terminalu, aby zatrzymać.")

try:
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Nie można odczytać klatki. Sprawdź połączenie.")
            break

        # Nakładanie OSD - tekst z datą i godziną
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, text, (10, 30), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # Zapisanie klatki (nagrywanie wideo)
        out.write(frame)
        frame_count += 1

        # Co 100 klatek wypisz komunikat w konsoli
        if frame_count % 100 == 0:
            print(f"Nagrano {frame_count} klatek...")

except KeyboardInterrupt:
    print("\nNagrywanie przerwane ręcznie.")

finally:
    cap.release()
    out.release()
    print("Zwolniono zasoby i zapisano plik output.mp4.")