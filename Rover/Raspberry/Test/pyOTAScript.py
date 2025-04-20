import serial
import struct
import os
import sys
from time import sleep

''' Bootloader Commands '''
CBL_GET_CID_CMD              = 0x10
CBL_GET_RDP_STATUS_CMD       = 0x11
CBL_GO_TO_ADDR_CMD           = 0x12
CBL_FLASH_ERASE_CMD          = 0x13
CBL_MEM_WRITE_CMD            = 0x14

INVALID_SECTOR_NUMBER        = 0x00
VALID_SECTOR_NUMBER          = 0x01
UNSUCCESSFUL_ERASE           = 0x02
SUCCESSFUL_ERASE             = 0x03

FLASH_PAYLOAD_WRITE_FAILED   = 0x00
FLASH_PAYLOAD_WRITE_PASSED   = 0x01

verbose_mode = 1
Memory_Write_Active = 0

BinFile = None  # Global binary file object

SERIAL_PORT = '/dev/ttyS0'
BAUD_RATE = 115200

def Write_Data_To_Serial_Port(Value, Length):
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=10) as ser:
            if isinstance(Value, int):
                Value = bytes([Value])  # Wrap single byte
            elif isinstance(Value, str):
                Value = Value.encode()
            elif isinstance(Value, list):
                Value = bytes(Value)

            ser.write(Value[:Length])
            print(f"Sent: {Value[:Length]}")
    except serial.SerialException as e:
        print(f"Serial error: {e}")
     

def Read_Serial_Port(Data_Len):
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=10) as Serial_Port_Obj:
            Serial_Value = Serial_Port_Obj.read(Data_Len)
            Serial_Value_len = len(Serial_Value)
            retries = 5

            while Serial_Value_len < Data_Len and retries > 0:
                print("Waiting for reply from the bootloader...")
                Serial_Value += Serial_Port_Obj.read(Data_Len - Serial_Value_len)
                Serial_Value_len = len(Serial_Value)
                retries -= 1
                sleep(0.1)

            if Serial_Value_len < Data_Len:
                print(f"Timeout !! Expected {Data_Len} bytes, received {Serial_Value_len}")
            
            return Serial_Value
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return b''

def Read_Data_From_Serial_Port():
    data = Read_Serial_Port(1)
    if len(data) == 0:
        return 0  # Assume NACK if no data received
    int_value_little = int.from_bytes(data, byteorder='little')
    return int_value_little

def Process_CBL_GET_CID_CMD(Data_Len):
    Serial_Data = Read_Serial_Port(Data_Len)
    CID = (Serial_Data[1] << 8) | Serial_Data[0]
    print("\n   Chip Identification Number : ", hex(CID))

def Process_CBL_GET_RDP_STATUS_CMD(Data_Len):
    print("Enter the RDP Function !")
    Serial_Data = Read_Serial_Port(Data_Len)
    _value_ = bytearray(Serial_Data)
    print(_value_)
    if _value_[0] == 0xEE:
        print("\n   Error While Reading FLASH Protection level !!")
    elif _value_[0] == 0x00:
        print("\n   FLASH Protection : LEVEL 0")
    elif _value_[0] == 0x01:
        print("\n   FLASH Protection : LEVEL 1")
    elif _value_[0] == 0x02:
        print("\n   FLASH Protection : LEVEL 2")

def Process_CBL_GO_TO_ADDR_CMD(Data_Len):
    print("Enter the Jumping Process !")
    Serial_Data = Read_Serial_Port(Data_Len)
    print("The Raspberry Pi Received the Data from the Serial Port !")
    _value_ = bytearray(Serial_Data)
    if _value_[0] == 1:
        print("\n   Address Status is Valid")
    else:
        print("\n   Address Status is InValid")

def Process_CBL_FLASH_ERASE_CMD(Data_Len):
    Serial_Data = Read_Serial_Port(Data_Len)
    if len(Serial_Data):
        BL_Erase_Status = bytearray(Serial_Data)
        if BL_Erase_Status[0] == INVALID_SECTOR_NUMBER:
            print("\n   Erase Status -> Invalid Sector Number ")
        elif BL_Erase_Status[0] == UNSUCCESSFUL_ERASE:
            print("\n   Erase Status -> Unsuccessful Erase ")
        elif BL_Erase_Status[0] == SUCCESSFUL_ERASE:
            print("\n   Erase Status -> Successful Erase ")
        else:
            print("\n   Erase Status -> Unknown Error")
    else:
        print("Timeout !! Bootloader is not responding")

def Process_CBL_MEM_WRITE_CMD(Data_Len):
    global Memory_Write_All
    Serial_Data = Read_Serial_Port(Data_Len)
    BL_Write_Status = bytearray(Serial_Data)
    if BL_Write_Status[0] == FLASH_PAYLOAD_WRITE_FAILED:
        print("\n   Write Status -> Write Failed or Invalid Address ")
    elif BL_Write_Status[0] == FLASH_PAYLOAD_WRITE_PASSED:
        print("\n   Write Status -> Write Successful ")
        Memory_Write_All = Memory_Write_All and FLASH_PAYLOAD_WRITE_PASSED
    else:
        print("Timeout !! Bootloader is not responding")

def Calculate_CRC32(Buffer, Buffer_Length):
    CRC_Value = 0xFFFFFFFF
    for DataElem in Buffer[0:Buffer_Length]:
        CRC_Value = CRC_Value ^ DataElem
        for DataElemBitLen in range(32):
            if CRC_Value & 0x80000000:
                CRC_Value = (CRC_Value << 1) ^ 0x04C11DB7
            else:
                CRC_Value = (CRC_Value << 1)
    return CRC_Value

def Word_Value_To_Byte_Value(Word_Value, Byte_Index, Byte_Lower_First):
    Byte_Value = (Word_Value >> (8 * (Byte_Index - 1)) & 0x000000FF)
    return Byte_Value

def CalulateBinFileLength():
    BinFileLength = os.path.getsize("app.bin")
    return BinFileLength

def OpenBinFile():
    global BinFile
    BinFile = open('app.bin', 'rb')

def Decode_CBL_Command(Command):
    BL_Host_Buffer = [0] * 255  # Initialize buffer
    
    if Command == 0:
        print("Sending Bootloader Start Command")
        Write_Data_To_Serial_Port(ord('U'), 1)

    elif Command == 1:
        print("Read the MCU chip identification number")
        CBL_GET_CID_CMD_Len = 6
        BL_Host_Buffer[0] = CBL_GET_CID_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_GET_CID_CMD
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_GET_CID_CMD_Len - 4)
        CRC32_Value = CRC32_Value & 0xFFFFFFFF
        BL_Host_Buffer[2] = Word_Value_To_Byte_Value(CRC32_Value, 1, 1)
        BL_Host_Buffer[3] = Word_Value_To_Byte_Value(CRC32_Value, 2, 1)
        BL_Host_Buffer[4] = Word_Value_To_Byte_Value(CRC32_Value, 3, 1)
        BL_Host_Buffer[5] = Word_Value_To_Byte_Value(CRC32_Value, 4, 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        for Data in BL_Host_Buffer[1:CBL_GET_CID_CMD_Len]:
            Write_Data_To_Serial_Port(Data, CBL_GET_CID_CMD_Len - 1)
        sleep(0.1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            Process_CBL_GET_CID_CMD(2)
        else:
            print("\nReceived Not Acknowledgment")

    elif Command == 2:
        print("Read the FLASH Read Protection level")
        CBL_GET_RDP_STATUS_CMD_Len = 6
        BL_Host_Buffer[0] = CBL_GET_RDP_STATUS_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_GET_RDP_STATUS_CMD
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_GET_RDP_STATUS_CMD_Len - 4)
        CRC32_Value = CRC32_Value & 0xFFFFFFFF
        BL_Host_Buffer[2] = Word_Value_To_Byte_Value(CRC32_Value, 1, 1)
        BL_Host_Buffer[3] = Word_Value_To_Byte_Value(CRC32_Value, 2, 1)
        BL_Host_Buffer[4] = Word_Value_To_Byte_Value(CRC32_Value, 3, 1)
        BL_Host_Buffer[5] = Word_Value_To_Byte_Value(CRC32_Value, 4, 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        for Data in BL_Host_Buffer[1:CBL_GET_RDP_STATUS_CMD_Len]:
            Write_Data_To_Serial_Port(Data, CBL_GET_RDP_STATUS_CMD_Len - 1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            Process_CBL_GET_RDP_STATUS_CMD(1)
        else:
            print("\nReceived Not Acknowledgment")

    elif Command == 3:
        print("Jump bootloader to specified address")
        CBL_GO_TO_ADDR_CMD_Len = 10
        CBL_Jump_Address = input("\n   Please Enter the Address in Hex (e.g., 0x08000000): ")
        CBL_Jump_Address = int(CBL_Jump_Address, 16)
        BL_Host_Buffer[0] = CBL_GO_TO_ADDR_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_GO_TO_ADDR_CMD
        BL_Host_Buffer[2] = Word_Value_To_Byte_Value(CBL_Jump_Address, 1, 1)
        BL_Host_Buffer[3] = Word_Value_To_Byte_Value(CBL_Jump_Address, 2, 1)
        BL_Host_Buffer[4] = Word_Value_To_Byte_Value(CBL_Jump_Address, 3, 1)
        BL_Host_Buffer[5] = Word_Value_To_Byte_Value(CBL_Jump_Address, 4, 1)
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_GO_TO_ADDR_CMD_Len - 4)
        CRC32_Value = CRC32_Value & 0xFFFFFFFF
        BL_Host_Buffer[6] = Word_Value_To_Byte_Value(CRC32_Value, 1, 1)
        BL_Host_Buffer[7] = Word_Value_To_Byte_Value(CRC32_Value, 2, 1)
        BL_Host_Buffer[8] = Word_Value_To_Byte_Value(CRC32_Value, 3, 1)
        BL_Host_Buffer[9] = Word_Value_To_Byte_Value(CRC32_Value, 4, 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        for Data in BL_Host_Buffer[1:CBL_GO_TO_ADDR_CMD_Len]:
            Write_Data_To_Serial_Port(Data, CBL_GO_TO_ADDR_CMD_Len - 1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            Process_CBL_GO_TO_ADDR_CMD(1)
        else:
            print("\nReceived Not Acknowledgment")

    elif Command == 4:
        print("Mass erase or sector erase of the user flash")
        CBL_FLASH_ERASE_CMD_Len = 6
        BL_Host_Buffer[0] = CBL_FLASH_ERASE_CMD_Len - 1
        BL_Host_Buffer[1] = CBL_FLASH_ERASE_CMD
        CRC32_Value = Calculate_CRC32(BL_Host_Buffer, CBL_FLASH_ERASE_CMD_Len - 4)
        CRC32_Value = CRC32_Value & 0xFFFFFFFF
        BL_Host_Buffer[2] = Word_Value_To_Byte_Value(CRC32_Value, 1, 1)
        BL_Host_Buffer[3] = Word_Value_To_Byte_Value(CRC32_Value, 2, 1)
        BL_Host_Buffer[4] = Word_Value_To_Byte_Value(CRC32_Value, 3, 1)
        BL_Host_Buffer[5] = Word_Value_To_Byte_Value(CRC32_Value, 4, 1)
        Write_Data_To_Serial_Port(BL_Host_Buffer[0], 1)
        for Data in BL_Host_Buffer[1:CBL_FLASH_ERASE_CMD_Len]:
            Write_Data_To_Serial_Port(Data, CBL_FLASH_ERASE_CMD_Len - 1)
        if Read_Data_From_Serial_Port() == 1:
            print("\nReceived Acknowledgment")
            Process_CBL_FLASH_ERASE_CMD(1)
        else:
            print("\nReceived Not Acknowledgment")

    elif Command == 5:
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

                print(f"\nChunk at 0x{BaseMemoryAddress:X} sent (attempt {repeat + 1}/{send_count})")

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
            print("\nPayload Written Successfully")

def Main():
    '''
    # Step 1: Initialize the Raspberry Pi's UART
    if Serial_Port_Configuration() != 0:
        print("Failed to configure UART. Exiting...")
        sys.exit(1)
    
    # Step 2: Request STM32 to enter bootloader mode
    if not Request_Bootloader_Mode():
        print("FailSed to activate bootloader mode. Exiting...")
        sys.exit(1)'''
    
    # Step 3: Interactive bootloader command menu
    while True:
        print("\nSTM32F401 Custom Bootloader")
        print("==============================")
        print("Available commands to send to the bootloader:")
        print("   Bootloader_Start_CMD        --> 0")
        print("   CBL_GET_CID_CMD             --> 1")
        print("   CBL_GET_RDP_STATUS_CMD      --> 2")
        print("   CBL_GO_TO_ADDR_CMD          --> 3")
        print("   CBL_FLASH_ERASE_CMD         --> 4")
        print("   CBL_MEM_WRITE_CMD           --> 5")
        
        CBL_Command = input("\nEnter the command code (0-5, or 'q' to quit): ")
        
        if CBL_Command.lower() == 'q':
            print("Exiting bootloader interaction...")
            break
        
        if not CBL_Command.isdigit() or int(CBL_Command) not in range(6):
            print("Error !! Please enter a valid command (0-5) or 'q' to quit")
            continue
        
        Decode_CBL_Command(int(CBL_Command))
    
    if BinFile:
        BinFile.close()

if __name__ == "__main__":
    try:
        Main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        if BinFile:
            BinFile.close()
        sys.exit(0)