'''
    1- Ensure Python venv tools are installed:

sudo apt install python3-venv python3-pip -y

    2- Create a virtual environment:

python3 -m venv ~/.venv

    3- Activate the virtual environment:

source ~/.venv/bin/activate

    4- Install the Azure Blob package inside the venv:

pip install azure-storage-blob

    5- Run your script using Python from the venv:

python /home/PI/GP/Test/uploadImageToAzure.py
'''

import os
import sys
import mimetypes
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings

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

# Check if the local file exists
if not os.path.isfile(local_file_path):
    print(f"File {local_file_path} does not exist.")
    sys.exit(1)

# Set the content type
content_type = mimetypes.guess_type(local_file_path)[0]
if content_type is None:
    content_type = "application/octet-stream"
content_settings = ContentSettings(content_type=content_type)

# Upload the file
try:
    with open(local_file_path, "rb") as data:
        blob_client.upload_blob(data, content_settings=content_settings)
    print(f"Uploaded {local_file_path} to {container_name}/{blob_name}")
except Exception as e:
    print(f"An error occurred: {e}")
