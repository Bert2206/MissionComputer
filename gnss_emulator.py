import time
import random
import math

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

if __name__ == "__main__":
    # Startowa pozycja
    emulator = GNSS_Emulator(52.401, 16.951)

    print("GNSS Emulator started. Press Ctrl+C to stop.")
    try:
        while True:
            data = emulator.get_gnss_data()
            print(f"Latitude: {data['latitude']:.6f}, Longitude: {data['longitude']:.6f}, "
                  f"Velocity: {data['velocity']:.2f} knots, Heading: {data['heading']:.2f} degrees")
            time.sleep(1)  # 1-second interval
    except KeyboardInterrupt:
        print("GNSS Emulator stopped.")