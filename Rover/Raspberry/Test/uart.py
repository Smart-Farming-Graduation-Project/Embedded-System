import serial
from time import sleep

SERIAL_PORT = '/dev/ttyS0'
BAUD_RATE = 115200

def main():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Sending data to ESP32 on {SERIAL_PORT} at {BAUD_RATE} baud rate...")
            while True:
                message = input("Enter message to send (or 'exit'): ")
                if message.lower() == "exit":
                    print("Exiting.")
                    break
                ser.write((message + '\n').encode())
                print("Sent:", message)
                sleep(0.1)
    except serial.SerialException as e:
        print("Serial error:", e)

if __name__ == "__main__":
    main()
