
// C99 libraries
#include <cstdlib>
#include <string.h>
#include <time.h>
// Libraries for MQTT client and WiFi connection
#include <WiFiManager.h>
#include <mqtt_client.h>
// Azure IoT SDK for C includes
#include <az_core.h>
#include <az_iot.h>
#include <azure_ca.h>
// Additional sample headers
#include "AzIoTSasToken.h"
#include "SerialLogger.h"
#include "iot_configs.h"

String ssid = "";
String password = "";

/******************************************   Sensors   ***************************************/

#include "DHT.h" // install DHT knx library

#define DHT_PIN              25
#define FLAME_PIN            33
#define SOIL_MOISTURE_PIN    32
#define LIGHT_INTENSITY_PIN  34

#define DHT_TYPE      DHT22
DHT dht(DHT_PIN, DHT_TYPE);

float humidity = 0.0f;
float temperature = 0.0f;
uint16_t soil_moisture = 0;
uint16_t flame = 0;
uint16_t intensity = 0;

/****************************************************************************************************/

/**********************************************  OTA   **********************************************/
#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoJson.h>

// Variables for Receiving Version and Update URL
String Update_Version = "";
String Firmware_Update_URL = "";
bool newUpdateAvailable = false;

// Current firmware version
#define CURRENT_FIRMWARE_VERSION "1.0"

/****************************************************************************************************/

#define AZURE_SDK_CLIENT_USER_AGENT "c%2F" AZ_SDK_VERSION_STRING "(ard;esp32)"
// Utility macros and defines
#define sizeofarray(a) (sizeof(a) / sizeof(a[0]))
#define NTP_SERVERS "pool.ntp.org", "time.nist.gov"
#define MQTT_QOS1 1
#define DO_NOT_RETAIN_MSG 0
#define SAS_TOKEN_DURATION_IN_MINUTES 60
#define UNIX_TIME_NOV_13_2017 1510592825

#define PST_TIME_ZONE -8
#define PST_TIME_ZONE_DAYLIGHT_SAVINGS_DIFF 1

#define GMT_OFFSET_SECS (PST_TIME_ZONE * 3600)
#define GMT_OFFSET_SECS_DST ((PST_TIME_ZONE + PST_TIME_ZONE_DAYLIGHT_SAVINGS_DIFF) * 3600)

// Translate iot_configs.h defines into variables used by the sample
static const char* host = IOT_CONFIG_IOTHUB_FQDN;
static const char* mqtt_broker_uri = "mqtts://" IOT_CONFIG_IOTHUB_FQDN;
static const char* device_id = IOT_CONFIG_DEVICE_ID;
static const int mqtt_port = AZ_IOT_DEFAULT_MQTT_CONNECT_PORT;
// Memory allocated for the sample's variables and structures.
static esp_mqtt_client_handle_t mqtt_client;
static az_iot_hub_client client;

static char mqtt_client_id[128];
static char mqtt_username[128];
static char mqtt_password[200];
static uint8_t sas_signature_buffer[256];
static unsigned long next_telemetry_send_time_ms = 0;
static char telemetry_topic[128];
static uint32_t telemetry_send_count = 0;
static String telemetry_payload = "";

#define INCOMING_DATA_BUFFER_SIZE 512
static char incoming_data[INCOMING_DATA_BUFFER_SIZE];

// Auxiliary functions
#ifndef IOT_CONFIG_USE_X509_CERT
static AzIoTSasToken sasToken(
    &client,
    AZ_SPAN_FROM_STR(IOT_CONFIG_DEVICE_KEY),
    AZ_SPAN_FROM_BUFFER(sas_signature_buffer),
    AZ_SPAN_FROM_BUFFER(mqtt_password));
#endif // IOT_CONFIG_USE_X509_CERT

static void connectToWiFi()
{
  Logger.Info("Connecting to WIFI SSID " + String(ssid));

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");

  Logger.Info("WiFi connected, IP address: " + WiFi.localIP().toString());
}

static void initializeTime()
{
  Logger.Info("Setting time using SNTP");

  configTime(GMT_OFFSET_SECS, GMT_OFFSET_SECS_DST, NTP_SERVERS);
  time_t now = time(NULL);
  while (now < UNIX_TIME_NOV_13_2017)
  {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println("");
  Logger.Info("Time initialized!");
}


void receivedCallback(char* topic, byte* payload, unsigned int length)
{
  Logger.Info("Received [");
  Logger.Info(topic);
  Logger.Info("]: ");
  for (int i = 0; i < length; i++)
  {
    Serial.print((char)payload[i]);
  }
  Serial.println("");
}

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
  (void)handler_args;
  (void)base;
  (void)event_id;

  esp_mqtt_event_handle_t event = (esp_mqtt_event_handle_t)event_data;
#else // ESP_ARDUINO_VERSION_MAJOR
static esp_err_t mqtt_event_handler(esp_mqtt_event_handle_t event)
{
#endif // ESP_ARDUINO_VERSION_MAJOR
  switch (event->event_id)
  {
    int i, r;

    case MQTT_EVENT_ERROR:
      Logger.Info("MQTT event MQTT_EVENT_ERROR");
      break;
    case MQTT_EVENT_CONNECTED:
  Logger.Info("MQTT event MQTT_EVENT_CONNECTED");

  // Subscribe to cloud-to-device messages
  r = esp_mqtt_client_subscribe(mqtt_client, AZ_IOT_HUB_CLIENT_C2D_SUBSCRIBE_TOPIC, 1);
  if (r == -1) {
    Logger.Error("Could not subscribe for cloud-to-device messages.");
  } else {
    Logger.Info("Subscribed for cloud-to-device messages; message id:" + String(r));
  }

  // Subscribe to direct methods
  r = esp_mqtt_client_subscribe(mqtt_client, "$iothub/methods/POST/#", 1);
  if (r == -1) {
    Logger.Error("Could not subscribe for direct methods.");
  } else {
    Logger.Info("Subscribed for direct methods; message id:" + String(r));
  }

  break;
    case MQTT_EVENT_DISCONNECTED:
      Logger.Info("MQTT event MQTT_EVENT_DISCONNECTED");
      break;
    case MQTT_EVENT_SUBSCRIBED:
      Logger.Info("MQTT event MQTT_EVENT_SUBSCRIBED");
      break;
    case MQTT_EVENT_UNSUBSCRIBED:
      Logger.Info("MQTT event MQTT_EVENT_UNSUBSCRIBED");
      break;
    case MQTT_EVENT_PUBLISHED:
      Logger.Info("MQTT event MQTT_EVENT_PUBLISHED");
      break;
    case MQTT_EVENT_DATA:
  {
    Logger.Info("MQTT event MQTT_EVENT_DATA");

    // Extract topic and payload
    char topic[INCOMING_DATA_BUFFER_SIZE];
    char payload[INCOMING_DATA_BUFFER_SIZE];

    int topic_len = min(event->topic_len, INCOMING_DATA_BUFFER_SIZE - 1);
    strncpy(topic, event->topic, topic_len);
    topic[topic_len] = '\0';

    int payload_len = min(event->data_len, INCOMING_DATA_BUFFER_SIZE - 1);
    strncpy(payload, event->data, payload_len);
    payload[payload_len] = '\0';

    Logger.Info("Topic: " + String(topic));
    Logger.Info("Payload: " + String(payload));

    // Copy the topic to incoming_data for direct method processing
    strncpy(incoming_data, topic, INCOMING_DATA_BUFFER_SIZE);

    // Check if the message is a direct method
    if (strstr(topic, "$iothub/methods/POST/") != NULL) {
      // Extract method name from the topic
      char method_name[64];
      sscanf(topic, "$iothub/methods/POST/%[^/]", method_name);

      // Handle the direct method
      directMethodCallback(method_name, payload, payload_len);
    }
  }
  break;
    case MQTT_EVENT_BEFORE_CONNECT:
      Logger.Info("MQTT event MQTT_EVENT_BEFORE_CONNECT");
      break;
    default:
      Logger.Error("MQTT event UNKNOWN");
      break;
  }

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
#else // ESP_ARDUINO_VERSION_MAJOR
  return ESP_OK;
#endif // ESP_ARDUINO_VERSION_MAJOR
}

static void initializeIoTHubClient()
{
  az_iot_hub_client_options options = az_iot_hub_client_options_default();
  options.user_agent = AZ_SPAN_FROM_STR(AZURE_SDK_CLIENT_USER_AGENT);

  if (az_result_failed(az_iot_hub_client_init(
          &client,
          az_span_create((uint8_t*)host, strlen(host)),
          az_span_create((uint8_t*)device_id, strlen(device_id)),
          &options)))
  {
    Logger.Error("Failed initializing Azure IoT Hub client");
    return;
  }

  size_t client_id_length;
  if (az_result_failed(az_iot_hub_client_get_client_id(
          &client, mqtt_client_id, sizeof(mqtt_client_id) - 1, &client_id_length)))
  {
    Logger.Error("Failed getting client id");
    return;
  }

  if (az_result_failed(az_iot_hub_client_get_user_name(
          &client, mqtt_username, sizeofarray(mqtt_username), NULL)))
  {
    Logger.Error("Failed to get MQTT clientId, return code");
    return;
  }

  Logger.Info("Client ID: " + String(mqtt_client_id));
  Logger.Info("Username: " + String(mqtt_username));
}

static int initializeMqttClient()
{
#ifndef IOT_CONFIG_USE_X509_CERT
  if (sasToken.Generate(SAS_TOKEN_DURATION_IN_MINUTES) != 0)
  {
    Logger.Error("Failed generating SAS token");
    return 1;
  }
#endif

  esp_mqtt_client_config_t mqtt_config;
  memset(&mqtt_config, 0, sizeof(mqtt_config));

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
    mqtt_config.broker.address.uri = mqtt_broker_uri;
    mqtt_config.broker.address.port = mqtt_port;
    mqtt_config.credentials.client_id = mqtt_client_id;
    mqtt_config.credentials.username = mqtt_username;

  #ifdef IOT_CONFIG_USE_X509_CERT
    LogInfo("MQTT client using X509 Certificate authentication");
    mqtt_config.credentials.authentication.certificate = IOT_CONFIG_DEVICE_CERT;
    mqtt_config.credentials.authentication.certificate_len = (size_t)sizeof(IOT_CONFIG_DEVICE_CERT);
    mqtt_config.credentials.authentication.key = IOT_CONFIG_DEVICE_CERT_PRIVATE_KEY;
    mqtt_config.credentials.authentication.key_len = (size_t)sizeof(IOT_CONFIG_DEVICE_CERT_PRIVATE_KEY);
  #else // Using SAS key
    mqtt_config.credentials.authentication.password = (const char*)az_span_ptr(sasToken.Get());
  #endif

    mqtt_config.session.keepalive = 30;
    mqtt_config.session.disable_clean_session = 0;
    mqtt_config.network.disable_auto_reconnect = false;
    mqtt_config.broker.verification.certificate = (const char*)ca_pem;
    mqtt_config.broker.verification.certificate_len = (size_t)ca_pem_len;
#else // ESP_ARDUINO_VERSION_MAJOR  
  mqtt_config.uri = mqtt_broker_uri;
  mqtt_config.port = mqtt_port;
  mqtt_config.client_id = mqtt_client_id;
  mqtt_config.username = mqtt_username;

#ifdef IOT_CONFIG_USE_X509_CERT
  Logger.Info("MQTT client using X509 Certificate authentication");
  mqtt_config.client_cert_pem = IOT_CONFIG_DEVICE_CERT;
  mqtt_config.client_key_pem = IOT_CONFIG_DEVICE_CERT_PRIVATE_KEY;
#else // Using SAS key
  mqtt_config.password = (const char*)az_span_ptr(sasToken.Get());
#endif

  mqtt_config.keepalive = 30;
  mqtt_config.disable_clean_session = 0;
  mqtt_config.disable_auto_reconnect = false;
  mqtt_config.event_handle = mqtt_event_handler;
  mqtt_config.user_context = NULL;
  mqtt_config.cert_pem = (const char*)ca_pem;
#endif // ESP_ARDUINO_VERSION_MAJOR

  mqtt_client = esp_mqtt_client_init(&mqtt_config);

  if (mqtt_client == NULL)
  {
    Logger.Error("Failed creating mqtt client");
    return 1;
  }

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
    esp_mqtt_client_register_event(mqtt_client, MQTT_EVENT_ANY, mqtt_event_handler, NULL);
#endif // ESP_ARDUINO_VERSION_MAJOR

  esp_err_t start_result = esp_mqtt_client_start(mqtt_client);

  if (start_result != ESP_OK)
  {
    Logger.Error("Could not start mqtt client; error code:" + start_result);
    return 1;
  }
  else
  {
    Logger.Info("MQTT client started");
    return 0;
  }
}

static uint32_t getEpochTimeInSecs() { return (uint32_t)time(NULL); }

static void establishConnection()
{
  connectToWiFi();
  initializeTime();
  initializeIoTHubClient();
  (void)initializeMqttClient();
}

/************************* Handle Direct Methods Received from Azure *****************************/
static void directMethodCallback(const char* method_name, const char* payload, size_t payload_size) {
  Logger.Info("Direct method received: " + String(method_name));
  Logger.Info("Payload: " + String(payload));

  // Extract the request ID ($rid) from the topic
  char request_id[32];
  if (sscanf(incoming_data, "$iothub/methods/POST/%*[^/]/?$rid=%31[^&]", request_id) != 1) {
    Logger.Error("Failed to extract request ID from topic");
    Logger.Info("Topic for debugging: " + String(incoming_data));
    return;
  }

  // Generate the response topic
  char response_topic[128];
  snprintf(response_topic, sizeof(response_topic), "$iothub/methods/res/200/?$rid=%s", request_id);

  // Create a response payload with LED state
  String response_payload = "{}";

  // Publish the response
  if (esp_mqtt_client_publish(
          mqtt_client,
          response_topic,
          response_payload.c_str(),
          response_payload.length(),
          MQTT_QOS1,
          DO_NOT_RETAIN_MSG) == 0) {
    Logger.Error("Failed to publish direct method response");
  } else {
    Logger.Info("Direct method response sent successfully");
  }

  // Create JSON document
  StaticJsonDocument<512> doc;  
  DeserializationError error = deserializeJson(doc, payload);

  if (error) {
    Logger.Error("Failed to parse JSON payload");
    return;
  }

  // Extract values
  Update_Version = doc["version"].as<String>();
  Firmware_Update_URL = doc["URL"].as<String>();

  // Log extracted values
  Logger.Info("Extracted Version: " + Update_Version);
  Logger.Info("Extracted URL: " + Firmware_Update_URL);

  /************************************** Received Method ************************************/
  if (strcmp(method_name, "ota") == 0)
  {
    // Check if the received version is greater than the current firmware version
    if (Update_Version.toFloat() > static_cast<String>(CURRENT_FIRMWARE_VERSION).toFloat()) {
        Logger.Info("New firmware update available! Version: " + Update_Version);
        newUpdateAvailable = true;
    } else {
        Logger.Info("No update required. Current firmware is up to date.");
    }
  } else {
    Logger.Error("Unknown method: " + String(method_name));
  }
  /********************************************************************************************/
}

static void generateTelemetryPayload()
{
  /************************************  Write Sensors Data ************************************/
  telemetry_payload = "{ \"msgCount\": " + String(telemetry_send_count++) +
                      ", \"Temperature\": " + String(temperature) +
                      ", \"Humidity\": " + String(humidity) +
                      ", \"Flame\": " + String(flame) +
                      ", \"Soil Moisture\": " + String(soil_moisture) + 
                      ", \"Light Intensity\": " + String(intensity) +" }";

  /*********************************************************************************************/
}

static void sendTelemetry()
{
  Logger.Info("Sending telemetry ...");

  if (az_result_failed(az_iot_hub_client_telemetry_get_publish_topic(
          &client, NULL, telemetry_topic, sizeof(telemetry_topic), NULL)))
  {
    Logger.Error("Failed az_iot_hub_client_telemetry_get_publish_topic");
    return;
  }

  generateTelemetryPayload();

  if (esp_mqtt_client_publish(
          mqtt_client,
          telemetry_topic,
          (const char*)telemetry_payload.c_str(),
          telemetry_payload.length(),
          MQTT_QOS1,
          DO_NOT_RETAIN_MSG)
      == 0)
  {
    Logger.Error("Failed publishing");
  }
  else
  {
    Logger.Info("Message published successfully");
  }
}

/********************************************* OTA Update ****************************************/
void downloadAndUpdateFirmware()
{
    // Get the download URL from Firebase
    Serial.print("Firmware URL: ");
    Serial.println(Firmware_Update_URL);

    HTTPClient http;
    http.begin(Firmware_Update_URL);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK)
    {
      WiFiClient& client = http.getStream();
      int firmwareSize = http.getSize();
      Serial.print("Firmware Size: ");
      Serial.println(firmwareSize);

      if (Update.begin(firmwareSize))
      {
          Serial.println("Begin OTA Updata...");
          size_t written = Update.writeStream(client);

          if (Update.size() == written)
          {
              Serial.println("Update successfully completed. Rebooting...");

              if (Update.end())
              {
                  Serial.println("Rebooting...");
                  ESP.restart();
              } 
              else 
              {
                  Serial.print("Update failed: ");
                  Serial.println(Update.errorString());
              }
          }
          else
          {
              Serial.println("Not enough space for OTA.");
          }
      } 
        else
        {
            Serial.println("Failed to begin OTA update.");
        }
    }
    else
    {
        Serial.print("Failed to download firmware. HTTP code: ");
        Serial.println(httpCode);
    }

    http.end();
}
/*************************************************************************************************/

void setup()
{
    WiFiManager wm;

    // reset settings - wipe stored credentials for testing
    // these are stored by the esp library
    // wm.resetSettings();

    bool res;
    // password must be >= 8 chars
    res = wm.autoConnect("AP-Ehab","12345678");

    if(!res) 
      Serial.println("Failed to connect");
    else
    {
      Serial.println("Connected Succenfully!");
      Serial.println("SSID: " + WiFi.SSID());
      Serial.println("Password: " + WiFi.psk());
    }

    ssid = WiFi.SSID();
    password = WiFi.psk();

    establishConnection();                  // Establish Azure IoT Connection

    /**********************************  Setup Sensors and Begin Serial ********************************/

    dht.begin();                            // init DHT22
    pinMode(SOIL_MOISTURE_PIN, INPUT);      // init soil moisture pin
    pinMode(FLAME_PIN, INPUT);              // init flame pin
    pinMode(LIGHT_INTENSITY_PIN, INPUT);    // init light intensity pin

    /***************************************************************************************************/
}

void loop()
{
  if (WiFi.status() != WL_CONNECTED){ connectToWiFi(); }

  // Perform Firmare Update
  if(newUpdateAvailable)
    downloadAndUpdateFirmware();

  // Reading Humidty, Temperature, Soil Moisture and Flame Sensor and Light intensity values & mapping them (0->100)
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  // Check if readings are valid
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    humidity = 0.0;
    temperature = 0.0;
  }

  soil_moisture = map(analogRead(SOIL_MOISTURE_PIN), 0, 4095, 0, 100);
  flame = map(analogRead(FLAME_PIN), 0, 4095, 100, 0);
  intensity = map(analogRead(LIGHT_INTENSITY_PIN), 0, 4095, 0, 100);

  if (millis() > next_telemetry_send_time_ms || flame > 0)
  {
    Serial.print("Version: ");
    Serial.println(CURRENT_FIRMWARE_VERSION);

    // Sending Data to Azure IoT Hub
    sendTelemetry();
    next_telemetry_send_time_ms = millis() + TELEMETRY_FREQUENCY_MILLISECS;
  }
  
  delay(2000);
}