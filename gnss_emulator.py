import sys
import os

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel
from pyqtlet2 import L, MapWidget
from qtpy.QtCore import QTimer

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
os.environ['QT_API'] = 'qtpy5'

import time
import random
import math

class GNSS_Emulator:
    def __init__(self, start_lat, start_lon):
        self.latitude = start_lat
        self.longitude = start_lon
        self.velocity = 0.0  # m/s
        self.heading = random.uniform(0, 360)  # 0 — północ, 90 — wschód, 180 — południe, 270 — zachód

    def update_position(self):
        self.heading += random.uniform(-10, 10)  # Losowa zmiana kierunku
        self.heading %= 360

        self.velocity += random.uniform(-1, 1) * 1.94384  # Zamiana z m/s na węzły
        self.velocity = max(0, min(self.velocity, 30))  # Ograniczenie do 30 węzłów

        distance = self.velocity  # Prędkość = droga / czas (zakładamy 1 sekundę)
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

class MapApp(QWidget):
    def __init__(self):
        super().__init__()

        # Inicjalizacja emulatora
        self.emulator = GNSS_Emulator(52.402, 16.9514)

        # Konfiguracja interfejsu
        self.setWindowTitle("Mapa z OpenStreetMap (pyqtlet2)")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Pola wejściowe
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        self.update_button = QPushButton("Zmień lokalizację")

        self.layout.addWidget(QLabel("Szerokość geograficzna:"))
        self.layout.addWidget(self.lat_input)
        self.layout.addWidget(QLabel("Długość geograficzna:"))
        self.layout.addWidget(self.lon_input)
        self.layout.addWidget(self.update_button)

        # Inicjalizacja mapy
        self.mapWidget = MapWidget()
        self.map = L.map(self.mapWidget)

        # Pobranie aktualnych danych
        data = self.emulator.get_gnss_data()
        self.latitude = data['latitude']
        self.longitude = data['longitude']

        # Ustawienie widoku mapy
        self.map.setView([self.latitude, self.longitude], 20)

        # Warstwa mapy
        self.title = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}')
        self.title.addTo(self.map)

        # Marker
        self.marker = L.marker([self.latitude, self.longitude])
        self.marker.bindPopup("Twoja lokalizacja")
        self.map.addLayer(self.marker)

        self.layout.addWidget(self.mapWidget)

        # Timer do aktualizacji mapy co sekundę
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_map)
        self.timer.start(1000)

    def update_map(self):
        data = self.emulator.get_gnss_data()
        self.latitude = data['latitude']
        self.longitude = data['longitude']

        self.map.setView([self.latitude, self.longitude], 20)
        self.marker.setLatLng([self.latitude, self.longitude])

        # Aktualizacja pól tekstowych
        self.lat_input.setText(str(self.latitude))
        self.lon_input.setText(str(self.longitude))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec())
