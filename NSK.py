from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSplitter
from qtpy.QtMultimedia import QMediaPlayer, QAudioOutput
from qtpy.QtMultimediaWidgets import QVideoWidget
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy.QtCore import QUrl, Qt, QTimer
from pyqtlet2 import L, MapWidget
import pygame
import socket
import serial
import struct
import sys
import os
import threading
import time

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
# Wymuszenie użycia PySide6 w pyqtlet2
os.environ['QT_API'] = 'qtpy5'

uart_port = '/dev/serial0'  # Port UART, COM12 u Kacpra
baudrate = 57600
ser = serial.Serial(uart_port, baudrate=baudrate, timeout=1)
sq_pckt = 0

class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Naziemna Stacja Kontroli")
        self.setGeometry(100, 100, 1280, 480)  # Adjusted width to fit both sections

        # Main layout structure (splitter: video on the left, map on the right)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(self.splitter)

        # Video section
        self.video_section = QWidget(self)
        self.video_layout = QVBoxLayout(self.video_section)
        self.video_widget = CustomVideoWidget(self)
        self.video_layout.addWidget(self.video_widget)
        self.video_section.setFixedSize(640, 480)  # Set fixed size
        self.splitter.addWidget(self.video_section)

        # Map section (Google Maps)
        self.map_section = QWidget(self)
        self.map_layout = QVBoxLayout(self.map_section)
        self.map_view = QWebEngineView(self)
        self.map_layout.addWidget(self.map_view)
        self.map_section.setFixedSize(640, 480)  # Set fixed size
        
        # Load Google Maps
        self.map_view.setUrl(QUrl("https://www.google.com/maps"))

        datatest = gnss_reader()
        self.latitude = datatest[0]
        self.longitude = datatest[1]

        self.mapWidget = MapWidget()
        self.map = L.map(self.mapWidget)
        self.map.setView([self.latitude, self.longitude], 10)

        self.marker = L.marker([self.latitude, self.longitude])
        self.marker.bindPopup("Twoja lokalizacja")
        self.map.addLayer(self.marker)

        self.title = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}')
        self.title.addTo(self.map)
        #self.splitter.layout.addWidget(self.mapWidget)

        self.splitter.addWidget(self.mapWidget)

        # Media player setup
        self.media_player = QMediaPlayer(self)
        #self.audio_output = QAudioOutput(self)
        #self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Connect video click to function
        #self.video_widget.pixel_clicked.connect(self.on_pixel_clicked)
        self.video_widget.pixel_clicked.connect(self.on_pixel_clicked)
        #self.pixel_clicked.emit(int(x), int(y))
        # Joystick initialization
        self.init_joystick()

        # Timer to poll joystick events
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_joystick)
        self.timer.start(50)  # Poll joystick every 50 ms

        # Create UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.udp_socket.bind(("192.168.1.104", 12345))  # NSK
        #self.udp_target = ("192.168.1.121", 12345)  # KM

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_map)
        self.timer.start(1000)

    def init_joystick(self):
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Joystick connected: {self.joystick.get_name()}")
        else:
            self.joystick = None
            print("No joystick found.")

    def poll_joystick(self):
        global sq_pckt
        if self.joystick:
            pygame.event.pump()
            axis_z = self.joystick.get_axis(0)
            axis_psi = self.joystick.get_axis(1)
            axis_x = self.joystick.get_axis(2)
            axis_y = self.joystick.get_axis(3)
            if abs(axis_x) < 0.05:
                axis_x = 0.00
            if abs(axis_y) < 0.05:
                axis_y = 0.00
            if abs(axis_psi) < 0.05:
                axis_psi = 0.00
            if abs(axis_z) < 0.05:
                axis_z = 0.00
            
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    print(f"Joystick Button {i} pressed")
            time.sleep(1)
            #wysylanie
            print(f"Joystick Axis: Z={axis_z:.2f}, PSI={axis_psi:.2f}, X={axis_x:.2f}, Y={axis_y:.2f}")
            send_angle_mavlink(ser, axis_x, sq_pckt, 0)
            send_angle_mavlink(ser, axis_y, sq_pckt, 1)
            send_angle_mavlink(ser, axis_z, sq_pckt, 2)
            send_angle_mavlink(ser, axis_psi, sq_pckt, 3)
            sq_pckt += 1

    def on_pixel_clicked(self, x, y):
        print(f"Pixel clicked at: ({x}, {y})")
        source_port = 12345
        destination_port = 12345
        payload = struct.pack('dd', float(x), float(y))
        length = 8 + len(payload)
        checksum = 0
        packet = struct.pack('!HHHH', source_port, destination_port, length, checksum) + payload
        self.udp_socket.sendto(packet, ("192.168.1.121", 12345))
    
    def update_map(self):
        datatest = gnss_reader()
        self.latitude = datatest[0]
        self.longitude = datatest[1]

        self.map.setView([self.latitude, self.longitude], 20)
        self.marker.setLatLng([self.latitude, self.longitude])

        # Aktualizacja pól tekstowych
        self.lat_input.setText(str(self.latitude))
        self.lon_input.setText(str(self.longitude))

def gnss_reader():
    UDP_IP = "192.168.1.104"
    UDP_PORT = 12346
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    while True:
        data, addr = sock.recvfrom(4096)
        lat, long, vel, head = struct.unpack('dddd', data[8:])
        return lat, long, vel, head
    
        

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

def send_angle_mavlink(ser, angle, packet_seq, messID):
    # Tworzenie wiadomości MAVLink
    
    Header = 0xFE
    PayloadLength = 4
    PacketSequence = packet_seq % 256
    SystemID = 1
    ComponentID = 6
    MessageID = messID
    Payload = struct.pack('<f', angle)
    Payload = Payload.ljust(4, b'\x00') 
    
    # Serializacja i wysyłanie wiadomości przez UART
    packet = struct.pack('<BBBBBB', Header, PayloadLength, PacketSequence, SystemID, ComponentID, MessageID) + Payload
    packet = packet.ljust(14, b'\x00')
    
    checksum = calculate_checksum(packet[3:])

    packet += struct.pack('<H', checksum)

    ser.write(packet)

class CustomVideoWidget(QVideoWidget):
    from qtpy.QtCore import Signal
    pixel_clicked = Signal(int, int)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            self.pixel_clicked.emit(int(x), int(y))
        super().mousePressEvent(event)


if __name__ == "__main__":
    udp_thread = threading.Thread(target=gnss_reader, daemon=True)
    udp_thread.start()
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
