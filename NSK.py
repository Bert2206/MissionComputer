from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSplitter
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QTimer
import pygame
import socket
import struct
import sys
import threading


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
        self.splitter.addWidget(self.map_section)

        # Media player setup
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Connect video click to function
        self.video_widget.pixel_clicked.connect(self.on_pixel_clicked)

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
        if self.joystick:
            pygame.event.pump()
            axis_x = self.joystick.get_axis(0)
            axis_y = self.joystick.get_axis(1)
            if abs(axis_x) < 0.05:
                axis_x = 0.00
            if abs(axis_y) < 0.05:
                axis_y = 0.00
            print(f"Joystick Axis: X={axis_x:.2f}, Y={axis_y:.2f}")
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    print(f"Joystick Button {i} pressed")

    def on_pixel_clicked(self, x, y):
        print(f"Pixel clicked at: ({x}, {y})")
        source_port = 12345
        destination_port = 12345
        payload = struct.pack('dd', float(x), float(y))
        length = 8 + len(payload)
        checksum = 0
        packet = struct.pack('!HHHH', source_port, destination_port, length, checksum) + payload
        self.udp_socket.sendto(packet, ("192.168.1.121", 12345))


def gnss_reader():
    UDP_IP = "192.168.1.104"
    UDP_PORT = 12346
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    while True:
        data, addr = sock.recvfrom(4096)
        lat, long, vel, head = struct.unpack('dddd', data[8:])


class CustomVideoWidget(QVideoWidget):
    from PySide6.QtCore import Signal
    pixel_clicked = Signal(int, int)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.position().x()
            y = event.position().y()
            self.pixel_clicked.emit(int(x), int(y))
        super().mousePressEvent(event)


if __name__ == "__main__":
    udp_thread = threading.Thread(target=gnss_reader, daemon=True)
    udp_thread.start()
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
