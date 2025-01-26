#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <base64.h>
#include <bearssl/bearssl.h>
#include <bearssl/bearssl_hmac.h>
#include <libb64/cdecode.h>
#include <ESP8266HTTPClient.h> // Required for firmware download
#include <ESP8266httpUpdate.h> // Required for FOTA updates

// Azure IoT SDK for C includes
#include <az_core.h>
#include <az_iot.h>
#include <azure_ca.h>

#include "C:\Users\DELL\Desktop\firmware.h" // Include the configuration file

// Define constants
#define POT_PIN A0
#define FIRMWARE_VERSION "1.1"
#define LED_PIN 2
#define sizeofarray(a) (sizeof(a) / sizeof(a[0]))
#define ONE_HOUR_IN_SECS 3600
#define NTP_SERVERS "pool.ntp.org", "time.nist.gov"
#define MQTT_PACKET_SIZE 1024

// Memory allocated for the sample's variables and structures.
static WiFiClientSecure wifi_client;
static X509List cert((const char*)ca_pem);
static PubSubClient mqtt_client(wifi_client);
static az_iot_hub_client client;

// Auxiliary variables
static char sas_token[200];
static uint8_t signature[512];
static unsigned char encrypted_signature[32];
static char base64_decoded_device_key[32];
static unsigned long next_telemetry_send_time_ms = 0;
static char telemetry_topic[128];
static uint8_t telemetry_payload[100];
static uint32_t telemetry_send_count = 0;

void connectToWiFi() {
  Serial.begin(115200);
  Serial.println();
  Serial.print("Connecting to WIFI SSID ");
  Serial.println(WIFI_SSID); // Use the defined SSID

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD); // Use the defined password
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.print("WiFi connected, IP address: ");
  Serial.println(WiFi.localIP());
  Serial.println("Firmware version " FIRMWARE_VERSION " installed"); // Print version message
}

// Callback function to handle incoming MQTT messages
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  // Check if the message is an update command
  if (String(topic).endsWith("/firmwareUpdate")) {
    Serial.println("Firmware update message received");
    String updateUrl = message;
    performFirmwareUpdate(updateUrl);
  }
}

// Initialize MQTT connection
void initMQTT() {
  mqtt_client.setServer(AZURE_IOT_HUB_HOST, MQTT_PORT); // Use the defined host and port
  mqtt_client.setCallback(mqttCallback);
}

// Function to connect to Azure IoT Hub
void connectToAzureIoT() {
  while (!mqtt_client.connected()) {
    Serial.print("Connecting to Azure IoT Hub...");
    if (mqtt_client.connect(AZURE_DEVICE_ID, sas_token, NULL)) { // Use the defined device ID
      Serial.println("connected");
      mqtt_client.subscribe(("devices/" + String(AZURE_DEVICE_ID) + "/messages/devicebound/#").c_str());

    } else {
      Serial.print("Failed, rc=");
      Serial.print(mqtt_client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// Function to perform FOTA
void performFirmwareUpdate(String firmwareUrl) {
  Serial.println("Starting firmware update...");
  t_httpUpdate_return ret = ESPhttpUpdate.update(wifi_client, firmwareUrl);

  switch (ret) {
    case HTTP_UPDATE_FAILED:
      Serial.printf("Update failed: %s\n", ESPhttpUpdate.getLastErrorString().c_str());
      break;
    case HTTP_UPDATE_NO_UPDATES:
      Serial.println("No update available.");
      break;
    case HTTP_UPDATE_OK:
      Serial.println("Update successful, rebooting...");
      ESP.restart();
      break;
  }
}

// Main setup function
void setup() {
  connectToWiFi();
  initMQTT();
  connectToAzureIoT();
}

// Main loop
void loop() {
  if (!mqtt_client.connected()) {
    connectToAzureIoT();
  }
  mqtt_client.loop();

  // Send telemetry data
  if (millis() > next_telemetry_send_time_ms) {
    snprintf(telemetry_topic, sizeof(telemetry_topic), "devices/%s/messages/events/", AZURE_DEVICE_ID); // Use defined device ID
    snprintf((char*)telemetry_payload, sizeof(telemetry_payload), "{\"temperature\":%d}", random(20, 30));
    mqtt_client.publish(telemetry_topic, (char*)telemetry_payload);
    telemetry_send_count++;
    next_telemetry_send_time_ms = millis() + 10000; // every 10 seconds
  }
}
