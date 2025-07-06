#!/usr/bin/env python

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

python /home/PI/GP/OTA/stm32ota.py
'''

import serial
import struct
import os
import sys
from time import sleep
import requests
from azure.iot.device import IoTHubDeviceClient, MethodResponse

# Bootloader Commands
CBL_GET_CID_CMD = 0x10
CBL_GET_RDP_STATUS_CMD = 0x11
CBL_GO_TO_ADDR_CMD = 0x12
CBL_FLASH_ERASE_CMD = 0x13
CBL_MEM_WRITE_CMD = 0x14

INVALID_SECTOR_NUMBER = 0x00
VALID_SECTOR_NUMBER = 0x01
UNSUCCESSFUL_ERASE = 0x02
SUCCESSFUL_ERASE = 0x03

FLASH_PAYLOAD_WRITE_FAILED = 0x00
FLASH_PAYLOAD_WRITE_PASSED = 0x01

verbose_mode = 1
Memory_Write_Active = 0
BinFile = None

# Serial port configuration
SERIAL_PORT = '/dev/ttyS0'
BAUD_RATE = 115200

# Azure IoT Hub connection string
AZURE_CONNECTION_STRING = "HostName=groundsensorshub.azure-devices.net;DeviceId=gsdev;SharedAccessKey=E7CbCD5/Mc4SnQdVzQyiqL0MOJ8RuP2TuLna6RDxPb0="

# Directory to save the downloaded file
DOWNLOAD_DIR = "/home/PI/GP/OTA"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Write a value to the serial port
def Write_Data_To_Serial_Port(Value, Length):
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=10) as ser:
            if isinstance(Value, int):
                Value = bytes([Value])
            elif isinstance(Value, str):
                Value = Value.encode()
            elif isinstance(Value, list):
                Value = bytes(Value)
            ser.write(Value[:Length])
            print(f"Sent: {Value[:Length]}")
    except serial.SerialException as e:
        print(f"Serial error: {e}")

# Read data from the serial port with retries
def Read_Serial_Port(Data_Len):
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=10) as Serial_Port_Obj:
            Serial_Value = Serial_Port_Obj.read(Data_Len)
            retries = 1
            while len(Serial_Value) < Data_Len and retries > 0:
                print("Waiting for reply from the bootloader...")
                Serial_Value += Serial_Port_Obj.read(Data_Len - len(Serial_Value))
                retries -= 1
                sleep(0.1)
            if len(Serial_Value) < Data_Len:
                print(f"Timeout !! Expected {Data_Len} bytes, received {len(Serial_Value)}")
            return Serial_Value
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return b''

# Read a single byte from the serial port and return it as an integer
def Read_Data_From_Serial_Port():
    data = Read_Serial_Port(1)
    if len(data) == 0:
        return 0
    return int.from_bytes(data, byteorder='little')

def Process_CBL_GET_CID_CMD(Data_Len):
    Serial_Data = Read_Serial_Port(Data_Len)
    CID = (Serial_Data[1] << 8) | Serial_Data[0]
    hex_cid = hex(CID)
    print("\n   Chip Identification Number : ", hex_cid)
    return {"CID": hex_cid}

def Process_CBL_GET_RDP_STATUS_CMD(Data_Len):
    Serial_Data = Read_Serial_Port(Data_Len)
    _value_ = bytearray(Serial_Data)
    protection_level = "UNKNOWN"
    if _value_[0] == 0xEE:
        protection_level = "ERROR"
    elif _value_[0] == 0x00:
        protection_level = "LEVEL 0"
    elif _value_[0] == 0x01:
        protection_level = "LEVEL 1"
    elif _value_[0] == 0x02:
        protection_level = "LEVEL 2"
    print("\n   FLASH Protection :", protection_level)
    return {"RDP_Level": protection_level}

def Process_CBL_FLASH_ERASE_CMD(Data_Len):
    Serial_Data = Read_Serial_Port(Data_Len)
    result = ""
    if len(Serial_Data):
        status = bytearray(Serial_Data)[0]
        if status == INVALID_SECTOR_NUMBER:
            result = "Invalid Sector Number"
        elif status == UNSUCCESSFUL_ERASE:
            result = "Unsuccessful Erase"
        elif status == SUCCESSFUL_ERASE:
            result = "Successful Erase"
        else:
            result = "Unknown Error"
    else:
        result = "Timeout"
    print("\n   Erase Status ->", result)
    return {"Erase_Status": result}

def Process_CBL_MEM_WRITE_CMD(Data_Len):
    global Memory_Write_All
    Serial_Data = Read_Serial_Port(Data_Len)
    if Serial_Data[0] == FLASH_PAYLOAD_WRITE_FAILED:
        print("\n   Write Status -> Write Failed or Invalid Address ")
    elif Serial_Data[0] == FLASH_PAYLOAD_WRITE_PASSED:
        print("\n   Write Status -> Write Successful ")
        Memory_Write_All = Memory_Write_All and FLASH_PAYLOAD_WRITE_PASSED
    else:
        print("Timeout !! Bootloader is not responding")

def Calculate_CRC32(Buffer, Buffer_Length):
    CRC_Value = 0xFFFFFFFF
    for DataElem in Buffer[0:Buffer_Length]:
        CRC_Value ^= DataElem
        for _ in range(32):
            if CRC_Value & 0x80000000:
                CRC_Value = (CRC_Value << 1) ^ 0x04C11DB7
            else:
                CRC_Value <<= 1
    return CRC_Value & 0xFFFFFFFF

def Word_Value_To_Byte_Value(Word_Value, Byte_Index, Byte_Lower_First):
    return (Word_Value >> (8 * (Byte_Index - 1))) & 0xFF

def CalulateBinFileLength():
    return os.path.getsize("/home/PI/GP/OTA/app.bin")

def OpenBinFile():
    global BinFile
    BinFile = open('/home/PI/GP/OTA/app.bin', 'rb')

def Decode_CBL_Command(Command):
    BL_Host_Buffer = [0] * 255
    result_payload = {}

    if Command == 0:
        print("Read the MCU chip identification number")
        CBL_GET_CID_CMD_Len = 6
        BL_Host_Buffer[0] = CBL_GET_CID_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_GET_CID_CMD
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_GET_CID_CMD_Len - 4)
        for i in range(4):
            BL_Host_Buffer[2 + i] = Word_Value_To_Byte_Value(CRC32_Value, i + 1, 1)
        Write_Data_To_Serial_Port(ord('U'), 1)
        sleep(0.1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[1:CBL_GET_CID_CMD_Len], CBL_GET_CID_CMD_Len - 1)
        sleep(0.1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            result_payload = Process_CBL_GET_CID_CMD(2)
        else:
            print("\nReceived Not Acknowledgment")
            result_payload = {"error": "NACK"}

    elif Command == 1:
        print("Read the FLASH Read Protection level")
        CBL_GET_RDP_STATUS_CMD_Len = 6
        BL_Host_Buffer[0] = CBL_GET_RDP_STATUS_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_GET_RDP_STATUS_CMD
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_GET_RDP_STATUS_CMD_Len - 4)
        for i in range(4):
            BL_Host_Buffer[2 + i] = Word_Value_To_Byte_Value(CRC32_Value, i + 1, 1)
        Write_Data_To_Serial_Port(ord('U'), 1)
        sleep(0.1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[1:CBL_GET_RDP_STATUS_CMD_Len], CBL_GET_RDP_STATUS_CMD_Len - 1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            result_payload = Process_CBL_GET_RDP_STATUS_CMD(1)
        else:
            print("\nReceived Not Acknowledgment")
            result_payload = {"error": "NACK"}

    elif Command == 2:
        print("Mass erase or sector erase of the user flash")
        CBL_FLASH_ERASE_CMD_Len = 6
        BL_Host_Buffer[0] = CBL_FLASH_ERASE_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_FLASH_ERASE_CMD
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_FLASH_ERASE_CMD_Len - 4)
        for i in range(4):
            BL_Host_Buffer[2 + i] = Word_Value_To_Byte_Value(CRC32_Value, i + 1, 1)
        Write_Data_To_Serial_Port(ord('U'), 1)
        sleep(0.1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[1:CBL_FLASH_ERASE_CMD_Len], CBL_FLASH_ERASE_CMD_Len - 1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            result_payload = Process_CBL_FLASH_ERASE_CMD(1)
        else:
            print("\nReceived Not Acknowledgment")
            result_payload = {"error": "NACK"}
            
    elif Command == 3:
        print("Write data into different memories of the MCU")
        global Memory_Write_All
        File_Total_Len = CalulateBinFileLength()
        print(f"Preparing to write binary file with length {File_Total_Len} bytes")
        OpenBinFile()
        BinFileRemainingBytes = File_Total_Len
        BinFileSentBytes = 0
        BaseMemoryAddress = 0x0800C000  # STM32 flash start address
        Memory_Write_All = 1
        FirstChunkSent = False

        while BinFileRemainingBytes > 0:
            Memory_Write_Active = 1
            BinFileReadLength = min(64, BinFileRemainingBytes)

            # Read one chunk
            chunk_data = BinFile.read(BinFileReadLength)

            # Determine how many times to send: twice for first, once for others
            send_count = 2 if not FirstChunkSent else 1

            for repeat in range(send_count):
                # Load chunk data into BL_Host_Buffer
                for i in range(BinFileReadLength):
                    BL_Host_Buffer[7 + i] = chunk_data[i]

                # Set up memory write command
                BL_Host_Buffer[1] = CBL_MEM_WRITE_CMD
                BL_Host_Buffer[2] = Word_Value_To_Byte_Value(BaseMemoryAddress, 1, 1)
                BL_Host_Buffer[3] = Word_Value_To_Byte_Value(BaseMemoryAddress, 2, 1)
                BL_Host_Buffer[4] = Word_Value_To_Byte_Value(BaseMemoryAddress, 3, 1)
                BL_Host_Buffer[5] = Word_Value_To_Byte_Value(BaseMemoryAddress, 4, 1)
                BL_Host_Buffer[6] = BinFileReadLength
                CBL_MEM_WRITE_CMD_Len = BinFileReadLength + 11
                BL_Host_Buffer[0] = CBL_MEM_WRITE_CMD_Len - 1

                # Calculate and insert CRC
                CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_MEM_WRITE_CMD_Len - 4) & 0xFFFFFFFF
                BL_Host_Buffer[7 + BinFileReadLength] = Word_Value_To_Byte_Value(CRC32_Value, 1, 1)
                BL_Host_Buffer[8 + BinFileReadLength] = Word_Value_To_Byte_Value(CRC32_Value, 2, 1)
                BL_Host_Buffer[9 + BinFileReadLength] = Word_Value_To_Byte_Value(CRC32_Value, 3, 1)
                BL_Host_Buffer[10 + BinFileReadLength] = Word_Value_To_Byte_Value(CRC32_Value, 4, 1)

                # Transmit the chunk
                Write_Data_To_Serial_Port(ord('U'), 1)
                sleep(0.1)
                Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
                for Data in BL_Host_Buffer[1:CBL_MEM_WRITE_CMD_Len]:
                    Write_Data_To_Serial_Port(Data, CBL_MEM_WRITE_CMD_Len - 1)

                print(f"\nChunk at 0x{BaseMemoryAddress:X})")

                if Read_Data_From_Serial_Port() == 1:
                    print("Received Acknowledgment")
                    Process_CBL_MEM_WRITE_CMD(1)
                else:
                    print("Received Not Acknowledgment. Aborting.")
                    return
                sleep(0.1)

            # Mark first chunk as sent
            if not FirstChunkSent:
                FirstChunkSent = True

            # Only increment address once per chunk, after send(s)
            BaseMemoryAddress += BinFileReadLength
            BinFileSentBytes += BinFileReadLength
            BinFileRemainingBytes = File_Total_Len - BinFileSentBytes

            print(f"Total bytes sent so far: {BinFileSentBytes}")

        Memory_Write_Active = 0
        if Memory_Write_All == 1:
            print("\nNew firmware successfully written to the STM32 flash memory")
            result_payload = {"result": "success", "message": "Firmware written successfully"}

    return result_payload

def handle_direct_method_request(device_client):
    print("Waiting for direct method calls from Azure IoT Hub...")
    method_to_command = {
        "bl0": 0,
        "bl1": 1,
        "bl2": 2,
        "bl3": 3
    }

    while True:
        try:
            method_request = device_client.receive_method_request()
            method_name = method_request.name
            print(f"Received method: {method_name}")
            print("Payload:", method_request.payload)

            response_payload = {}
            status = 200

            if method_name in method_to_command:
                result_payload = Decode_CBL_Command(method_to_command[method_name])
                response_payload = {"result": f"Command '{method_name}' executed successfully", "data": result_payload}

            elif method_name == "ota":
                try:
                    payload = method_request.payload
                    if not isinstance(payload, dict) or "URL" not in payload:
                        raise ValueError("Invalid payload. Expected a JSON object with 'URL' key.")

                    file_url = payload["URL"]
                    print(f"Downloading firmware from: {file_url}")

                    response = requests.get(file_url)
                    response.raise_for_status()

                    file_path = os.path.join(DOWNLOAD_DIR, "app.bin")
                    with open(file_path, "wb") as f:
                        f.write(response.content)

                    print(f"Firmware downloaded and saved to: {file_path}")
                    response_payload = {"result": "Download successful", "file": "app.bin"}

                except Exception as ota_error:
                    print(f"OTA download error: {ota_error}")
                    response_payload = {"error": str(ota_error)}
                    status = 400

            else:
                print("Unknown method received")
                response_payload = {"error": f"Unknown method: {method_name}"}
                status = 400

            print("Sending response to Azure:", response_payload)

            method_response = MethodResponse.create_from_method_request(
                method_request, status, response_payload
            )
            device_client.send_method_response(method_response)

        except Exception as e:
            print(f"Error handling method request: {e}")


def Main():
    device_client = IoTHubDeviceClient.create_from_connection_string(AZURE_CONNECTION_STRING)
    device_client.connect()

    try:
        handle_direct_method_request(device_client)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        if BinFile:
            BinFile.close()
        device_client.shutdown()

if __name__ == "__main__":
    try:
        Main()
    except Exception as e:
        print(f"Exception occurred: {e}")
        if BinFile:
            BinFile.close()
        sys.exit(1)
