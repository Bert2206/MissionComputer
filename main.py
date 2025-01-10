import sys
import time
import cv2
import serial
import struct
from pymavlink import mavutil

gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! video/x-raw,format=BGR ! appsink"

# Parametry UART
uart_port = '/dev/serial0'  # Port UART na Raspberry Pi 4
baudrate = 57600

tracker_type = 'CSRT'
div = 1
camera_fov = 42
target_fps = 5
frame_duration = 1.0 / target_fps

def init_tracker():
    global tracker
    tracker = cv2.TrackerCSRT_create()
    tracker.init(frame, bbox)

def click_event(event, x, y, flags, param):
    global frame, bbox, tracker
    if event == cv2.EVENT_LBUTTONDOWN:
        k = 2
        bbox = (int(x - 15 * k / div), int(y - 15 * k / div), int(30 * k / div), int(30 * k / div))
        init_tracker()

def detect_obstacles(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 120, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 10000:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "Obstacle", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return frame

def calculate_angular_deviation(frame_width, bbox):
    frame_center_x = frame_width / 2
    object_center_x = int(bbox[0] + bbox[2] / 2)
    offset_x = object_center_x - frame_center_x
    angle = (offset_x / frame_width) * camera_fov
    return angle

# Inicjalizacja MAVLink i UART
ser = serial.Serial(uart_port, baudrate=baudrate, timeout=1)
master = mavutil.mavlink_connection('udpout:localhost:14540', baud=baudrate)

def calculate_checksum(data):
    """Wylicz sumę kontrolną (Checksum) jako sumę modulo 65536."""
    return sum(data) & 0xFFFF

def send_angle_mavlink(ser, angle, packet_seq):
    # Tworzenie wiadomości MAVLink
    
    Header = 0xFE,
    PayloadLength = 4,
    PacketSequence = packet_seq % 256,
    SystemID = 3,
    ComponentID = 2,
    MessageID = 1,
    Payload = struct.pack('<f', angle) + b'\x00' * 4
    
    # Serializacja i wysyłanie wiadomości przez UART
    packet = struct.pack('<BBBBBB', Header, PayloadLength, PacketSequence, SystemID, ComponentID, MessageID) + Payload

    checksum = calculate_checksum(frame[3:])

    packet += struct.pack('<H', checksum)

    ser.write(packet)

if __name__ == '__main__':
    # cv2.namedWindow("Tracking")
    # cv2.setMouseCallback("Tracking", click_event)

    with open("dane.txt", "w") as plik:
        plik.write("x\ty\n")
        plik.close()

    video = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    ok, frame = video.read()
    if not ok:
        print("Cannot read video file")
        sys.exit()

    frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_rate = int(video.get(cv2.CAP_PROP_FPS))
    if frame_rate == 0:
        frame_rate = 30
    frame = cv2.resize(frame, (int(frame_width / div), int(frame_height / div)), interpolation=cv2.INTER_AREA)
    print(f"Rozdzielczość kamery: {frame_width}x{frame_height}, Frame rate: {frame_rate} FPS")

    udp_pipeline = (
    f"appsrc ! video/x-raw,format=BGR,width={frame_width},height={frame_height},framerate={frame_rate}/1 ! "
    "videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency bitrate=5000 speed-preset=ultrafast ! h264parse ! rtph264pay config-interval=1 pt=96 ! "
    "udpsink host=192.168.1.104 port=5000"
)

    out = cv2.VideoWriter(udp_pipeline, cv2.CAP_GSTREAMER, 0, frame_rate, (frame_width, frame_height), True)

    if not out.isOpened():
        print("Nie można otworzyć wyjścia GStreamer. Sprawdź konfigurację.")
        video.release()
        exit()

    bbox = (int(frame_width / div / 2), int(frame_height / div / 2), 30, 30)
    init_tracker()

    packet_seq = 0

    while True:
        loop_start_time = time.time()

        ok, frame = video.read()
        if not ok:
            break

        frame = cv2.resize(frame, (int(frame_width / div), int(frame_height / div)), interpolation=cv2.INTER_AREA)

        ok, bbox = tracker.update(frame)

        if ok:
            # Tracking success
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)

            angle = calculate_angular_deviation(frame_width, bbox)
            cv2.putText(frame, f"Angle: {angle:.2f} degrees", (100, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            
            send_angle_mavlink(ser, angle, packet_seq)
            packet_seq += 1
            
        else:
            cv2.putText(frame, "Tracking failure", (100, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

        frame = detect_obstacles(frame)

        cv2.putText(frame, tracker_type + " Tracker", (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2)
        out.write(frame)

        with open("dane.txt", "a") as plik:
            plik.write(str(int(bbox[0])) + "\t" + str(int(bbox[1])) + "\n")

        elapsed_time = time.time() - loop_start_time
        if elapsed_time < frame_duration:
            time.sleep(frame_duration - elapsed_time)

        k = cv2.waitKey(1) & 0xff
        if k == 27:
            break
    video.release()
    out.release()
    ser.close()
