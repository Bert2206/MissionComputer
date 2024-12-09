import cv2
from datetime import datetime
import time

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
frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
if frame_rate == 0:
    frame_rate = 30

print(f"Rozdzielczość kamery: {frame_width}x{frame_height}, Frame rate: {frame_rate} FPS")

# Strumień GStreamer do wysyłania wideo przez UDP
udp_pipeline = (
    f"appsrc ! video/x-raw,format=BGR,width={frame_width},height={frame_height},framerate={frame_rate}/1 ! "
    "videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency bitrate=5000 speed-preset=ultrafast ! h264parse ! rtph264pay config-interval=1 pt=96 ! "
    "udpsink host=192.168.1.104 port=5000"
)


#omxh264enc target-bitrate=500000 speed-preset=ultrafast,  v4l2h264enc #kodeki sprzętowe
#kodek x264enc to kodek programowy

# VideoWriter z GStreamer jako wyjście
out = cv2.VideoWriter(udp_pipeline, cv2.CAP_GSTREAMER, 0, frame_rate, (frame_width, frame_height), True)

if not out.isOpened():
    print("Nie można otworzyć wyjścia GStreamer. Sprawdź konfigurację.")
    cap.release()
    exit()

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
        position = (10, 50)
        cv2.putText(frame, text, position, font, 1, (255, 0, 0), 2, cv2.LINE_AA)

        # Wysyłanie klatki przez UDP
        out.write(frame)
        frame_count += 1

        # Co 100 klatek wypisz komunikat w konsoli
        if frame_count % 100 == 0:
            print(f"Wysłano {frame_count} klatek...")

        # Dodaj opóźnienie, aby zsynchronizować z frame rate
        time.sleep(1 / frame_rate)

except KeyboardInterrupt:
    print("\nStrumieniowanie przerwane ręcznie.")

finally:
    cap.release()
    out.release()
    print("Zwolniono zasoby i zakończono strumieniowanie.")

    #gst-inspect-1.0 | grep 264 #sprawdzanie dostępnych elementów gstreamer
