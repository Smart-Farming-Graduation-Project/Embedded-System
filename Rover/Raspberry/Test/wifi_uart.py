import os
import socket
import subprocess
import serial
from time import sleep

SERIAL_PORT = '/dev/ttyS0'
BAUD_RATE = 115200

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

def start_uart():
    try:
        uart = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"UART ready on {SERIAL_PORT} at {BAUD_RATE} baud.")
        return uart
    except serial.SerialException as e:
        print("UART error:", e)
        return None

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

            # Send to ESP32 via UART
            if uart:
                uart.write((command + "\n").encode())
                print(f"Sent to ESP32: {command}")
                sleep(0.1)

            conn.sendall(f"Command '{command}' sent to ESP32\n".encode())

        conn.close()
        print(f"Disconnected from {addr}")

if __name__ == "__main__":
    setup_hotspot()
    uart = start_uart()
    if uart:
        start_server(uart)
