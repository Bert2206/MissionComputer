import sys
import time
import cv2
import serial
import struct
import socket
import random
import math
import threading

# GStreamer pipeline configuration
gst_pipeline = "v4l2src device=/dev/video0 ! videoconvert ! video/x-raw,format=BGR ! appsink"

# UART parameters
UART_PORT = '/dev/serial0'
BAUDRATE = 57600

# Tracking and camera settings
TRACKER_TYPE = 'CSRT'
DIV = 1
CAMERA_FOV = 72
TARGET_FPS = 5
FRAME_DURATION = 1.0 / TARGET_FPS

# Initialize tracker
def init_tracker():
    global tracker
    tracker = cv2.TrackerCSRT_create()
    tracker.init(frame, bbox)

# UDP listener thread
def udp_listener():
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock2.bind(("192.168.1.121", 12345))
    udp_target = ("192.168.1.104", 12345)
    global bbox, udp_data_received

    while True:
        data, _ = sock2.recvfrom(4096)
        x, y = struct.unpack('dd', data[8:])
        print(f"x: {x}, y: {y}")
        k = 2  # Scaling factor for tracking area
        bbox = (int(x - 15 * k / DIV), int(y - 15 * k / DIV), int(30 * k / DIV), int(30 * k / DIV))
        udp_data_received = True
        init_tracker()

# Detect obstacles in the frame
def detect_obstacles(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 120, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 20000:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "Obstacle", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return frame

# Calculate angular deviation
def calculate_angular_deviation(frame_width, bbox):
    frame_center_x = frame_width / 2
    object_center_x = int(bbox[0] + bbox[2] / 2)
    offset_x = object_center_x - frame_center_x
    return (offset_x / frame_width) * CAMERA_FOV

# GNSS Emulator class
class GNSS_Emulator:
    def __init__(self, start_lat, start_lon):
        self.latitude = start_lat
        self.longitude = start_lon
        self.velocity = 0.0  # m/s
        self.heading = random.uniform(0, 360)

    def update_position(self):
        self.heading += random.uniform(-10, 10)
        self.heading %= 360
        self.velocity += random.uniform(-1, 1) * 1.94384
        self.velocity = max(0, min(self.velocity, 30))
        distance = self.velocity
        delta_lat = distance * math.cos(math.radians(self.heading)) / 111320
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

# Send GNSS data over UDP
def send_gnss(lat, lon, vel, heading):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_target = ("192.168.1.104", 12346)
    payload = struct.pack('dddd', float(lat), float(lon), float(vel), float(heading))
    packet = struct.pack('!HHHH', 12346, 12346, 8 + len(payload), 0) + payload
    sock.sendto(packet, udp_target)

# Main program
if __name__ == '__main__':
    udp_thread = threading.Thread(target=udp_listener, daemon=True)
    udp_thread.start()

    video = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    ok, frame = video.read()
    if not ok:
        print("Cannot read video file")
        sys.exit()

    frame_width, frame_height = 640, 360
    frame = cv2.resize(frame, (frame_width // DIV, frame_height // DIV), interpolation=cv2.INTER_AREA)
    print(f"Rozdzielczość kamery: {frame_width}x{frame_height}")

    udp_pipeline = (
        f"appsrc ! video/x-raw,format=BGR,width={frame_width},height={frame_height},framerate=30/1 ! "
        "videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency bitrate=5000 speed-preset=ultrafast ! "
        "h264parse ! rtph264pay config-interval=1 pt=96 ! "
        "udpsink host=192.168.1.104 port=5000"
    )
    out = cv2.VideoWriter(udp_pipeline, cv2.CAP_GSTREAMER, 0, 30, (frame_width, frame_height), True)

    if not out.isOpened():
        print("Cannot open GStreamer output")
        video.release()
        sys.exit()

    bbox = (frame_width // (2 * DIV), frame_height // (2 * DIV), 30, 30)
    init_tracker()

    emulator = GNSS_Emulator(52.401, 16.951)
    packet_seq = 0

    while True:
        loop_start_time = time.time()

        ok, frame = video.read()
        if not ok:
            break

        frame = cv2.resize(frame, (frame_width // DIV, frame_height // DIV), interpolation=cv2.INTER_AREA)
        ok, bbox = tracker.update(frame)
        data_gnss = emulator.get_gnss_data()

        if ok:
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
            angle = calculate_angular_deviation(frame_width, bbox)
            cv2.putText(frame, f"Angle: {angle:.2f} degrees", (100, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            send_gnss(data_gnss['latitude'], data_gnss['longitude'], data_gnss['velocity'], data_gnss['heading'])
            packet_seq += 1
        else:
            cv2.putText(frame, "Tracking failure", (100, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

        frame = detect_obstacles(frame)
        out.write(frame)

        elapsed_time = time.time() - loop_start_time
        if elapsed_time < FRAME_DURATION:
            time.sleep(FRAME_DURATION - elapsed_time)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    video.release()
    out.release()
