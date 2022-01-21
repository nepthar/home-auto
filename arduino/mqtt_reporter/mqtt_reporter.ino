/**
 * Publish temperature/humditiy to MQTT broker
 */

#include <PubSubClient.h>
#include <ESP8266WiFi.h>
#include <DHT.h>
#include "Math.h"

#define DHTTYPE DHT22
#define DHTPIN  D2

#define WIFI_SSID "....."
#define WIFI_PASS "....."

#define MQTT_BROKER "10.16.51.5"
#define MQTT_PORT 1883
#define MQTT_TOPIC "alpine/climate/closet"
#define MQTT_CLIENT_ID "sense-closet"

#define REPORT_INTERVAL_MIN 2


DHT dht(DHTPIN, DHTTYPE, 11); // 11 works fine for ESP8266

long wake_millis = 0;

void setup() {
  wake_millis = millis();
  dht.begin();
  connectWifi();
  sendTeperatureTS(dht.readTemperature(true), dht.readHumidity());
  ESP.deepSleep(REPORT_INTERVAL_MIN * 60 * 1000000, WAKE_RF_DEFAULT);
}

void loop() {
}

void connectWifi()
{
  // todo: timeout
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(100);
}

void sendTeperatureTS(float temp, float humidity)
{
  WiFiClient wifiClient;

  PubSubClient psClient(wifiClient);
  psClient.setServer(MQTT_BROKER, 1883);

  if(psClient.connect(MQTT_CLIENT_ID)) {
    psClient.loop();

    psClient.publish(MQTT_TOPIC "/temp_c", String(temp).c_str());
    psClient.publish(MQTT_TOPIC "/humidity", String(humidity).c_str());

    psClient.disconnect();
  }
}
