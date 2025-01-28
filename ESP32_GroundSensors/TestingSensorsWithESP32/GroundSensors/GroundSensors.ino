#include "DHT.h"

#define DHT_PIN       4
#define LDR_PIN       32
#define FLAME_PIN     33
#define SOIL_MOISTURE_PIN    34

#define DHT_TYPE      DHT22
DHT dht(DHT_PIN, DHT_TYPE);

float humidity = 0.0f;
float temperature = 0.0f;
uint16_t ldr = 0;
uint16_t flame = 0;
uint16_t soilmoisture = 0;

void setup()
{
    Serial.begin(115200);
    dht.begin();
    pinMode(LDR_PIN, INPUT);
    pinMode(FLAME_PIN, INPUT);
    //pinMode(SOIL_MOISTURE_PIN, INPUT);
}

void loop()
{
    humidity = dht.readHumidity();
    temperature = dht.readTemperature();

    ldr = map(analogRead(LDR_PIN), 0, 4095, 100, 0);

    flame = map(analogRead(FLAME_PIN), 0, 4095, 100, 0);

    soilmoisture = map(analogRead(SOIL_MOISTURE_PIN), 0, 4095, 0, 100);

    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.print("% - Temperature: ");
    Serial.print(temperature);
    Serial.println("°C");

    Serial.print("LDR Percentage: ");
    Serial.print(ldr);
    Serial.println("%");

    Serial.print("Flame Percentage: ");
    Serial.print(flame);
    Serial.println("%");

    Serial.print("Soil Moisture Percentage: ");
    Serial.print(soilmoisture);
    Serial.println("%");

    delay(2500);
}