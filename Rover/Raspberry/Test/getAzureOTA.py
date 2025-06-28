'''
    1- Ensure Python venv tools are installed:

sudo apt install python3-venv python3-pip -y

    2- Create a virtual environment:

python3 -m venv ~/.venv

    3- Activate the virtual environment:

source ~/.venv/bin/activate

    4- Install required packages inside the venv:

pip install azure-iot-device

    5- Run your script using Python from the venv:

python /home/PI/GP/Test/getAzureOTA.py
'''

import os
import requests
from azure.iot.device import IoTHubDeviceClient, MethodResponse

# Your Azure IoT Hub device connection string
CONNECTION_STRING = "HostName=groundsensorshub.azure-devices.net;DeviceId=gsdev;SharedAccessKey=E7CbCD5/Mc4SnQdVzQyiqL0MOJ8RuP2TuLna6RDxPb0="

# Directory to save the downloaded file
DOWNLOAD_DIR = "/home/PI/GP/Test"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def handle_ota_method(request):
    print("Received direct method:", request.name)
    if request.name != "ota":
        print("Unknown method")
        return MethodResponse.create_from_method_request(request, 404, {"result": "Unknown method"})

    try:
        payload = request.payload
        if not isinstance(payload, dict) or "URL" not in payload:
            raise ValueError("Invalid payload. Expected a JSON with 'URL' key.")
        
        file_url = payload["URL"]
        print(f"Downloading file from: {file_url}")

        response = requests.get(file_url)
        response.raise_for_status()

        # save as app.bin
        file_path = os.path.join(DOWNLOAD_DIR, "app.bin")

        with open(file_path, "wb") as f:
            f.write(response.content)

        print(f"Downloaded and saved to: {file_path}")
        return MethodResponse.create_from_method_request(request, 200, {"result": "Download successful", "file": "app.bin"})

    except Exception as e:
        print("Error during OTA method:", str(e))
        return MethodResponse.create_from_method_request(request, 500, {"result": str(e)})

def main():
    print("Connecting to Azure IoT Hub...")
    device_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

    device_client.connect()
    print("Connected. Waiting for 'ota' direct method...")

    # Set handler for direct method
    device_client.on_method_request_received = lambda req: device_client.send_method_response(handle_ota_method(req))

    try:
        while True:
            pass  # Keep the script running

    except KeyboardInterrupt:
        print("Disconnecting...")
        device_client.shutdown()

if __name__ == "__main__":
    main()
