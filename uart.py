import serial
import time

serial_port = '/dev/serial0' 
baud_rate = 9600

try:
    ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=1)
    print("Połączono z UART!")
except Exception as e:
    print(f"Nie udało się otworzyć portu UART: {e}")
    exit()

try:
    message = "Hello from Raspberry Pi!\n"
    ser.write(message.encode()) 
    print(f"Wysłano: {message.strip()}")
except KeyboardInterrupt:
    print("Zakończono.")
finally:
    ser.close()
