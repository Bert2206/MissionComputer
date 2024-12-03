import cv2

# Strumień GStreamer do przechwytywania obrazu z kamery
gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! appsink ! video/x-raw format=BGR"

# Przechwytywanie strumienia w OpenCV
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Nie można otworzyć kamery")
    exit()

    # Parametry kodowania H.264 (lub H.265)
    fourcc = cv2.VideoWriter_fourcc(*'H264')  # Możesz zmienić na 'H265' dla H.265
    out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (1280, 720))

while True:
    ret, frame = cap.read()
    if not ret:
        print("Nie można odczytać klatki")
        break

    # Nakładanie OSD - tekst z datą i godziną
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, text, (10, 30), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Zapisanie klatki (nagrywanie wideo)
    out.write(frame)

    # Wyświetlanie podglądu z nałożonym OSD
    cv2.imshow("Podgląd kamery", frame)

# Wyjdź, jeśli naciśnięto 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Zatrzymano nagrywanie")
        break

    # Wyświetlenie klatki w oknie
    #cv2.imshow("Podgląd kamery", frame)

cap.release()
out.release()
cv2.destroyAllWindows()
