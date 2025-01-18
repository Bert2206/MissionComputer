import csv
import serial
import struct

# Parametry UART
uart_port = '/dev/serial0'  # Port UART na Raspberry Pi 4
baudrate = 57600

# Inicjalizacja MAVLink i UART
ser = serial.Serial(uart_port, baudrate=baudrate, timeout=1)

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

def send_angle_mavlink(angle, packet_seq):
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

if __name__ == '__main__':
    with open('daned.txt', 'r') as file:
        packet_seq = 0
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            xd = row['x']
            yd = row['y']
            angle = int(float(row['angle']))
            send_angle_mavlink(ser, angle, packet_seq)
            packet_seq += 1
ser.close()
file.close()