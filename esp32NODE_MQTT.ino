#include <Arduino.h>
#include <WiFi.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <BLEServer.h>
#include <IRremote.h>
#include <esp_wifi.h>
#include <esp_wifi_types.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <SPIFFS.h>
#include <SPI.h>
#include <MFRC522.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// MQTT Configuration
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic_commands = "esp32/commands";
const char* mqtt_topic_logs = "esp32/logs";
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// WiFi Credentials (configure these)
const char* wifi_ssid = "YOUR_WIFI_SSID";
const char* wifi_password = "YOUR_WIFI_PASSWORD";

// Original multi-tool configuration remains unchanged below
// [All original pin definitions and variables...]

// Add MQTT connection function
void mqttReconnect() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-MultiTool-";
    clientId += String(random(0xffff), HEX);
    
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected");
      mqttClient.subscribe(mqtt_topic_commands);
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

// Modified output function to handle both Serial and MQTT
void sendResponse(const String& message) {
  Serial.println(message);
  if (mqttClient.connected()) {
    mqttClient.publish(mqtt_topic_logs, message.c_str());
  }
}

// MQTT Callback Handler
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Parse JSON
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  if (error) {
    sendResponse("ERROR:INVALID_JSON");
    return;
  }

  // Extract command
  String command = doc["cmd"].as<String>();
  command.toUpperCase();
  String params = "";

  // Convert JSON command to serial-style command
  if (command == "WIFI_SCAN") {
    command = "WIFI SCAN";
  }
  else if (command == "WIFI_DEAUTH") {
    command = "WIFI DEAUTH " + doc["target"].as<String>();
  }
  else if (command == "WIFI_BEACON") {
    command = "WIFI BEACON " + doc["prefix"].as<String>() + " " + doc["count"].as<String>();
  }
  // [Add similar conversions for other commands...]

  // Process the constructed command
  processCommand(command);
}

// Modified setup function
void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  
  // Connect to WiFi
  WiFi.begin(wifi_ssid, wifi_password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  
  // Initialize MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);
  
  // Original initializations
  BLEDevice::init("");
  // [Rest of original setup code...]
  
  Serial.println(F("READY"));
}

// Modified loop function
void loop() {
  // Handle MQTT connection
  if (!mqttClient.connected()) {
    mqttReconnect();
  }
  mqttClient.loop();

  // Original loop content
  // [Existing serial handling and attack processing...]
  
  // Check for IR code if capturing
  if (currentAttack == "IR_CAPTURE" && irrecv.decode(&irResults)) {
    lastIRCode = irResults.value;
    sendResponse("IR_CAPTURE:CODE:" + String(lastIRCode, HEX));
    irrecv.resume();
  }
  
  // Handle DNS for Evil Twin attack
  if (currentAttack == "EVIL_TWIN") {
    dnsServer.processNextRequest();
    webServer.handleClient();
  }
  
  delay(10);
}

// Modified processCommand function
void processCommand(const String& command) {
  String cmd = command;
  cmd.trim();
  cmd.toUpperCase();
  
  // [Original command processing logic...]
  
  // Replace all Serial.println with sendResponse
  // Example:
  if (cmd.startsWith("WIFI SCAN")) {
    sendResponse("WIFI_SCAN:START");
    executeWifiScan();
  }
  // [Update all other commands similarly...]
}

// Example modified function with MQTT output
void executeWifiScan() {
  int networks = WiFi.scanNetworks(false, true, false, 300);
  
  if (networks == 0) {
    sendResponse("WIFI_SCAN:NO_NETWORKS");
  } else {
    sendResponse("WIFI_SCAN:FOUND:" + String(networks));
    
    for (int i = 0; i < networks; i++) {
      String output = "WIFI_NETWORK:" + WiFi.BSSIDstr(i) + ":" + 
                      WiFi.SSID(i) + ":" + WiFi.RSSI(i) + ":" + 
                      WiFi.channel(i);
      sendResponse(output);
    }
    sendResponse("WIFI_SCAN:COMPLETE");
  }
  WiFi.scanDelete();
}

// [Keep all other original functions but replace Serial.println with sendResponse]