from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog, QSplitter
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QMouseEvent
import pygame
import socket


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video Player with Map and Joystick")
        self.setGeometry(100, 100, 1200, 600)

        # Główna struktura układu (splitter: wideo po lewej, mapa po prawej)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(self.splitter)

        # Sekcja wideo
        self.video_section = QWidget(self)
        self.video_layout = QVBoxLayout(self.video_section)
        self.video_widget = CustomVideoWidget(self)  # Custom widget for video
        self.video_layout.addWidget(self.video_widget)
        self.open_button = QPushButton("Open Video", self)
        self.open_button.clicked.connect(self.open_file)
        self.video_layout.addWidget(self.open_button)
        self.splitter.addWidget(self.video_section)

        # Sekcja mapy (Google Maps)
        self.map_section = QWidget(self)
        self.map_layout = QVBoxLayout(self.map_section)
        self.map_view = QWebEngineView(self)
        self.map_layout.addWidget(self.map_view)

        # Załaduj mapę Google (wymaga połączenia internetowego)
        self.map_view.setUrl(QUrl("https://www.google.com/maps"))
        self.splitter.addWidget(self.map_section)

        # Media player setup
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Połącz kliknięcie wideo z funkcją
        self.video_widget.pixel_clicked.connect(self.on_pixel_clicked)

        # Joystick initialization
        self.init_joystick()

        # Timer to poll joystick events
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_joystick)
        self.timer.start(50)  # Poll joystick every 50 ms

        # Create UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(("192.168.1.1", 12345))  # NSK
        self.udp_target = ("192.168.1.2", 12345)  # KM

    def init_joystick(self):
        """Initialize the joystick using pygame."""
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
        """Poll joystick events and print axis/button states."""
        if self.joystick:
            pygame.event.pump()  # Process joystick events

            # Odczyt osi joysticka
            axis_x = self.joystick.get_axis(0)  # Oś X
            axis_y = self.joystick.get_axis(1)  # Oś Y
            if abs(axis_x)<0.05: #Zerowanie niewielkich odchylen - potrzebne bo przy poczatkowej pozycji galki byla inna wartosc niz 0.00
                axis_x = 0.00
            if abs(axis_y)<0.05:
                axis_y = 0.00
            print(f"Joystick Axis: X={axis_x:.2f}, Y={axis_y:.2f}")

            # Odczyt przycisków joysticka
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    print(f"Joystick Button {i} pressed")

    def open_file(self):
        # Open file dialog to select a video
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")

        if file_path:
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()

    def on_pixel_clicked(self, x, y):
        # Handle pixel click coordinates
        print(f"Pixel clicked at: ({x}, {y})")
        # Send coordinates over UDP
        source_port = 12345  #  (NSK)
        destination_port = 12345  #  (KM)
        payload = struct.pack('dd', float(x), float(y))
        length = 8 + len(payload)  # (8 bajtow + payload)
        checksum = 0 # W naszym wypadku opcjonalna i nie wiem czy ja wykorzystac

        packet = struct.pack('!HHHH', source_port, destination_port, length, checksum) + payload

        # Wysłanie ramki
        self.udp_socket.sendto(packet, self.udp_target)


class CustomVideoWidget(QVideoWidget):
    from PySide6.QtCore import Signal

    # Custom signal to emit pixel coordinates
    pixel_clicked = Signal(int, int)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # Get coordinates of the click
            x = event.position().x()
            y = event.position().y()
            # Emit the coordinates
            self.pixel_clicked.emit(int(x), int(y))
        # Call the parent class's mousePressEvent
        super().mousePressEvent(event)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
