import cv2

# Strumień GStreamer do przechwytywania obrazu z kamery
gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! appsink"


# Przechwytywanie strumienia w OpenCV
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Nie można otworzyć kamery")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Nie można odczytać klatki")
        break

    # Wyświetlenie klatki w oknie
    cv2.imshow("Podgląd kamery", frame)

    # Wyjdź, jeśli naciśnięto 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
