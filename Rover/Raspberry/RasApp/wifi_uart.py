import os
import socket
import subprocess
import serial
from time import sleep
# Servo libraries
import RPi.GPIO as GPIO
from time import sleep
import signal
# Camera & Azure Blob Storage libraries
import sys
import mimetypes
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings

###################################### UART
SERIAL_PORT = '/dev/ttyS0'
BAUD_RATE = 115200

###################################### Servo Configuration
RightLeftPin = 12     # PWM 0
UpDownPin = 13        # PWM 1

GPIO.setmode(GPIO.BCM)

GPIO.setup(RightLeftPin, GPIO.OUT)
GPIO.setup(UpDownPin, GPIO.OUT)

RightLeftServo = GPIO.PWM(RightLeftPin, 50)  
RightLeftServo.start(0)

UpDownServo = GPIO.PWM(UpDownPin, 50)
UpDownServo.start(0)

#################################### Received commands from WiFi access point
STM32_COMMANDS = {'F', 'B', 'R', 'L', 'S', '0', '1', '2', '3', '4', '5'}
CAMERA_COMMANDS = {'U', 'C', 'J', 'O', 'D','T'}

#################################### Configuration of uploading image to Azure Blob Storage
# Configuration
connection_string = "DefaultEndpointsProtocol=https;AccountName=roverstorge;AccountKey=2l+Kt/4cDBgS/Ei6ESsR5uoA97RvSGTAmEV3iIGnPlwSUuqHmvtz1hMrRquvAcszzmpp81aEWeN3+ASt2wdpNg==;EndpointSuffix=core.windows.net"  # Replace with your Azure connection string
container_name = "rover-pohotes"                       # Your container name
local_file_path = "/home/PI/plant.jpg"                 # Path to your picture
# Extract base file name (without extension)
#filename = os.path.splitext(os.path.basename(local_file_path))[0]
# Get current date and time string
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
# Construct blob name
blob_name = f"plant-{timestamp}.cropguardrover.jpg"
print(blob_name)

# Create the BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Get or create the container
container_client = blob_service_client.get_container_client(container_name)
if not container_client.exists():
    container_client.create_container()

# Get the blob client
blob_client = container_client.get_blob_client(blob_name)

# Set the content type
content_type = mimetypes.guess_type(local_file_path)[0]
if content_type is None:
    content_type = "application/octet-stream"
content_settings = ContentSettings(content_type=content_type)


############################################### Function to set up the WiFi hotspot
def setup_hotspot():
    try:
        # Create ap0 if not exists
        result = subprocess.run("iwconfig ap0", shell=True, capture_output=True, text=True)
        if "No such device" in result.stderr:
            subprocess.run("sudo iw dev wlan0 interface add ap0 type __ap", shell=True, check=True)
            subprocess.run("sudo ip link set ap0 up", shell=True, check=True)

        # Assign static IP
        ip_check = subprocess.run("ip addr show ap0 | grep 192.168.2.1", shell=True, capture_output=True, text=True)
        if "192.168.2.1" not in ip_check.stdout:
            subprocess.run("sudo ip addr add 192.168.2.1/24 dev ap0", shell=True, check=True)

        # Create hostapd config if not exists
        hostapd_conf = "/etc/hostapd/hostapd.conf"
        if not os.path.exists(hostapd_conf):
            config = """
interface=ap0
driver=nl80211
ssid=PI
hw_mode=g
channel=7
country_code=EG
wpa=2
wpa_passphrase=password123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
ieee80211n=1
wmm_enabled=1
auth_algs=1
ignore_broadcast_ssid=0
"""
            subprocess.run(f"echo '{config}' | sudo tee {hostapd_conf}", shell=True, check=True)

        # Configure dnsmasq if not done
        dnsmasq_conf = "/etc/dnsmasq.conf"
        if not os.path.exists("/tmp/dnsmasq_configured"):
            dnsmasq_config = "\ninterface=ap0\ndhcp-range=192.168.2.2,192.168.2.100,12h\n"
            subprocess.run(f"echo '{dnsmasq_config}' | sudo tee -a {dnsmasq_conf}", shell=True, check=True)
            subprocess.run("touch /tmp/dnsmasq_configured", shell=True)

        # Start services
        subprocess.run("sudo systemctl stop hostapd", shell=True)
        subprocess.run("sudo hostapd /etc/hostapd/hostapd.conf &", shell=True)
        subprocess.run("sudo systemctl start dnsmasq", shell=True)

        print("Hotspot setup complete.")
    except subprocess.CalledProcessError as e:
        print("Hotspot setup error:", e)

############################################### Start UART communication
def start_uart():
    try:
        uart = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"UART ready on {SERIAL_PORT} at {BAUD_RATE} baud.")
        return uart
    except serial.SerialException as e:
        print("UART error:", e)
        return None
    
############################################### Servo control functions
def set_angle(servo,angle):
    duty_cycle = angle / 18 + 2
    servo.ChangeDutyCycle(duty_cycle)
    sleep(0.5)
    servo.ChangeDutyCycle(0)

def signal_handler(signum, frame):
    print("\nCleaning up GPIO...")
    RightLeftServo.stop()
    UpDownServo.stop()
    GPIO.cleanup()
    exit()

signal.signal(signal.SIGINT, signal_handler)  # Catch Ctrl+C

############################################### Start the server to listen for commands
def start_server(uart):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.2.1", 12345))
    server.listen(1)
    print("Server listening on 192.168.2.1:12345...")

    while True:
        conn, addr = server.accept()
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            command = data.decode().strip()
            print(f"Received: {command}")

            # Send to STM32 via UART
            if uart and command in STM32_COMMANDS:
                uart.write((command + "\n").encode())
                print(f"Sent to STM32: {command}")
                sleep(0.1)
            # Control camera commands
            elif command in CAMERA_COMMANDS:
                print(f"Sent to Camera: {command}")
                if command == 'C':
                    # Capture image
                    print("Capturing image...")
                    # upload image to Azure Blob Storage
                    print("Uploading image to Azure Blob Storage...")
                    try:
                        with open(local_file_path, "rb") as data:
                            blob_client.upload_blob(data, overwrite=True)
                        print(f"Uploaded {local_file_path} to {container_name}/{blob_name}")
                    except Exception as e:
                        print(f"An error occurred: {e}")
                elif command == 'U':
                    set_angle(UpDownServo, 90)
                elif command == 'D':
                    set_angle(UpDownServo, 0)
                elif command == 'J':
                    set_angle(RightLeftServo, 90)
                elif command == 'O':
                    set_angle(RightLeftServo, 0)
                elif command == 'T':
                    print("nothing to do")
            else:
                print(f"Unknown command: {command}")

            conn.sendall(f"Command '{command}' sent to STM32\n".encode())

        conn.close()
        print(f"Disconnected from {addr}")

if __name__ == "__main__":
    setup_hotspot()
    uart = start_uart()
    if uart:
        start_server(uart)
