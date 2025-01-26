#include<Wire.h>
#include "FirebaseESP8266.h"
#include<ESP8266WiFi.h>

const int ledPin = 13;
char FIREBASE_AUTH [] = "AIzaSyC0jtJboe4ZlhjUNMb1EWHiBAH1JgNGiDQ"; // Your Firebase Web API Key
char FIREBASE_HOST [] = "https://farming-1d4b3-default-rtdb.firebaseio.com/"; // Your Firebase Host URL
char WIFI_SSID [] = "ManUtd";     // Your WIFI SSID
char WIFI_PASSWORD [] = "1q6z7b881q6z7b88"; // Your WIFI Password

FirebaseData firebaseData;

void setup(){
  Serial.begin(115200);
  pinMode(ledPin,OUTPUT);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Firebase.begin(FIREBASE_HOST, FIREBASE_AUTH);
}

void loop(){
  digitalWrite(ledPin, HIGH);
  Serial.println("LED is ON");
  Firebase.setString(firebaseData, "/data", "ON"); //This will create a path as 'data' and save the value on Firebase
  delay(5000);  

  digitalWrite(ledPin, LOW);
  Serial.println("LED is OFF");
  Firebase.setString(firebaseData, "/data", "OFF");
  delay(5000);  
}