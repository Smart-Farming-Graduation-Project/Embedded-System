
// Azure IoT Hub
#define IOT_CONFIG_IOTHUB_FQDN "ehabhub.azure-devices.net"
// Azure IoT Gub Device ID
#define IOT_CONFIG_DEVICE_ID "ehabdev"
// Azure IoT Hub Device Key (primary key)
#define IOT_CONFIG_DEVICE_KEY "XfVpLLxxNY67OiPMiAH0LB5S8Pd2/4uDxEmLEIWdDA0="

// Publish 1 message every 5 seconds
#define TELEMETRY_FREQUENCY_MILLISECS 10000


// az iot hub monitor-events --hub-name "ehabhub" --device-id "ehabdev" --output json