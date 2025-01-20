import sys
import time
import cv2
import serial
import struct
import socket
import random
import math
#from pymavlink import mavutil

gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! video/x-raw,format=BGR ! appsink"

# Parametry UART
uart_port = '/dev/serial0'  # Port UART, który działał na Raspberry Pi 4 -.-
baudrate = 57600

sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock2.bind(("192.168.1.121", 12345))  # KM
udp_target = ("192.168.1.104", 12345)  # NSK

tracker_type = 'CSRT'
div = 1
camera_fov = 42
target_fps = 5
frame_duration = 1.0 / target_fps
    
def init_tracker():
    global tracker
    tracker = cv2.TrackerCSRT_create()
    tracker.init(frame, bbox)

def udp_listener():
    global bbox, udp_data_received
    
    while True:
        data, _ = sock2.recvfrom(4096)
        print(f"Otrzymana wiadomość RAW: {data}")

        try:
            # Odczytujemy pierwsze 4 bajty jako nagłówek (opcjonalnie)
            header = data[:4]
            print(f"Nagłówek: {header}")

            # Parsowanie liczb double z pozostałych danych
            x, y = struct.unpack('dd', data[4:])
            print(f"x: {x}, y: {y}")

            # Obliczanie bbox
            k = 2  # Skala obszaru śledzenia
            bbox = (int(x - 15 * k / div), int(y - 15 * k / div), int(30 * k / div), int(30 * k / div))
            udp_data_received = True
            init_tracker()
        except Exception as e:
            print(f"Błąd podczas parsowania danych UDP: {e}")

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
#ser = serial.Serial(uart_port, baudrate=baudrate, timeout=1)
#master = mavutil.mavlink_connection('udpout:localhost:14540', baud=baudrate)

def calculate_checksum(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return crc & 0xFFFF

def send_angle_mavlink(ser, angle, packet_seq):
    # Tworzenie wiadomości MAVLink
    
    Header = 0xFE
    PayloadLength = 4
    PacketSequence = packet_seq % 256
    SystemID = 3
    ComponentID = 2
    MessageID = 1
    Payload = struct.pack('<f', angle) + b'\x00' * 4
    
    # Serializacja i wysyłanie wiadomości przez UART
    packet = struct.pack('<BBBBBB', Header, PayloadLength, PacketSequence, SystemID, ComponentID, MessageID) + Payload

    checksum = calculate_checksum(packet[3:])

    packet += struct.pack('<H', checksum)

    ser.write(packet)

class GNSS_Emulator:
    def __init__(self, start_lat, start_lon):
        self.latitude = start_lat
        self.longitude = start_lon
        self.velocity = 0.0  # m/s
        self.heading = random.uniform(0, 360)  # 0 — ruch na polnoc, 90 — ruch na wschod, 180 — ruch na poludnie, 270 — ruch na zachod.

    def update_position(self):
        # Update heading randomly to simulate a changing direction
        self.heading += random.uniform(-10, 10)  # Change heading by up to 10 degrees
        self.heading %= 360

        # Update velocity randomly to simulate acceleration or deceleration
        self.velocity += random.uniform(-1, 1)* 1.94384  # zamiana z m/s na wezly
        self.velocity = max(0, min(self.velocity, 30))  # ogranicznie max 30 wezlow

        # Calculate new position based on current velocity and heading
        distance = self.velocity  # Assuming update interval of 1 second (velocity = distance / time)
        delta_lat = distance * math.cos(math.radians(self.heading)) / 111320  # Convert meters to degrees latitude
        delta_lon = distance * math.sin(math.radians(self.heading)) / (111320 * math.cos(math.radians(self.latitude)))

        self.latitude += delta_lat
        self.longitude += delta_lon

    def get_gnss_data(self):
        self.update_position()
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "velocity": self.velocity,
            "heading": self.heading
        }
    
def send_GNSS(la, lo, vel, heading):

        # Send coordinates over UDP
        source_port = 12345  #  (KM)
        destination_port = 12345  #  (NSK)
        payload = struct.pack('dddd', float(la), float(lo), float(vel), float(heading))
        length = 8 + len(payload)  # (8 bajtow + payload)
        checksum = 0 # W naszym wypadku opcjonalna i nie wiem czy ja wykorzystac

        packet = struct.pack('!HHHH', source_port, destination_port, length, checksum) + payload

        sock2.sendto(packet, udp_target)

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

    # Startowa pozycja
    emulator = GNSS_Emulator(52.401, 16.951)

    while True:
        loop_start_time = time.time()

        ok, frame = video.read()
        if not ok:
            break

        frame = cv2.resize(frame, (int(frame_width / div), int(frame_height / div)), interpolation=cv2.INTER_AREA)

        ok, bbox = tracker.update(frame)

        dataGNSS = emulator.get_gnss_data()

        if ok:
            # Tracking success
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)

            angle = calculate_angular_deviation(frame_width, bbox)
            cv2.putText(frame, f"Angle: {angle:.2f} degrees", (100, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            
            #send_angle_mavlink(ser, angle, packet_seq)
            send_GNSS(dataGNSS['latitude'],dataGNSS['longitude'],dataGNSS['velocity'],dataGNSS['heading'])
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
    sock2.close()
