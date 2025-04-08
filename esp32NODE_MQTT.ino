#include <Arduino.h>
#include <WiFi.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <BLEServer.h>
// #include <IRremote.h>        // IR remote not used
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

// Original multi-tool configuration
#define SERIAL_BAUD_RATE 115200
// #define IR_RECEIVE_PIN 15      // IR pins no longer needed
// #define IR_SEND_PIN 4          // IR pins no longer needed
#define RC522_SS_PIN 5
#define RC522_RST_PIN 22

// IR functionality commented out:
// IRrecv irrecv(IR_RECEIVE_PIN);
// IRsend irsend(IR_SEND_PIN);

MFRC522 rfid(RC522_SS_PIN, RC522_RST_PIN);

String currentAttack = "";
// unsigned long lastIRCode = 0;   // IR code storage no longer needed
// decode_results irResults;       // IR decode results not used
DNSServer dnsServer;
WebServer webServer(80);

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
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  // Process the command directly (same format as serial commands)
  processCommand(message);
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
  // IR functionality commented out:
  // irrecv.enableIRIn();
  SPI.begin();
  rfid.PCD_Init();
  
  Serial.println(F("READY"));
}

// Modified loop function
void loop() {
  // Handle MQTT connection
  if (!mqttClient.connected()) {
    mqttReconnect();
  }
  mqttClient.loop();

  // Original serial handling
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
  
  // Check for IR code if capturing - IR functionality commented out
  /*
  if (currentAttack == "IR_CAPTURE" && irrecv.decode(&irResults)) {
    lastIRCode = irResults.value;
    sendResponse("IR_CAPTURE:CODE:" + String(lastIRCode, HEX));
    irrecv.resume();
  }
  */
  
  // Handle DNS for Evil Twin attack
  if (currentAttack == "EVIL_TWIN") {
    dnsServer.processNextRequest();
    webServer.handleClient();
  }
  
  delay(10);
}

void processCommand(const String& command) {
  String cmd = command;
  cmd.trim();
  cmd.toUpperCase();
  
  if (cmd == "HELP") {
    sendResponse("Available commands:");
    sendResponse("WIFI SCAN - Scan for nearby WiFi networks");
    sendResponse("WIFI DEAUTH <BSSID> - Deauthenticate devices from a network");
    sendResponse("WIFI BEACON <prefix> <count> - Spam fake beacon frames");
    sendResponse("BLE SCAN - Scan for BLE devices");
    sendResponse("BLE SPAM <count> - Spam BLE advertisements");
    // IR commands commented out:
    // sendResponse("IR CAPTURE - Capture IR signals");
    // sendResponse("IR SEND <code> - Send IR code");
    sendResponse("RFID READ - Read RFID tag");
    sendResponse("RFID WRITE <data> - Write data to RFID tag");
    sendResponse("EVIL TWIN <SSID> - Create evil twin access point");
    sendResponse("STOP - Stop current attack");
  }
  else if (cmd.startsWith("WIFI SCAN")) {
    sendResponse("WIFI_SCAN:START");
    executeWifiScan();
  }
  else if (cmd.startsWith("WIFI DEAUTH")) {
    String target = cmd.substring(11);
    target.trim();
    if (target.length() == 0) {
      sendResponse("ERROR:NO_BSSID");
      return;
    }
    sendResponse("WIFI_DEAUTH:START:" + target);
    // Execute deauth attack
    currentAttack = "WIFI_DEAUTH";
  }
  else if (cmd.startsWith("WIFI BEACON")) {
    int space1 = cmd.indexOf(' ', 11);
    if (space1 == -1) {
      sendResponse("ERROR:INVALID_FORMAT");
      return;
    }
    String prefix = cmd.substring(11, space1);
    String countStr = cmd.substring(space1 + 1);
    int count = countStr.toInt();
    sendResponse("WIFI_BEACON:START:" + prefix + ":" + String(count));
    // Execute beacon spam
    currentAttack = "WIFI_BEACON";
  }
  else if (cmd == "BLE SCAN") {
    sendResponse("BLE_SCAN:START");
    // Execute BLE scan
    currentAttack = "BLE_SCAN";
  }
  else if (cmd.startsWith("BLE SPAM")) {
    String countStr = cmd.substring(8);
    countStr.trim();
    int count = countStr.toInt();
    sendResponse("BLE_SPAM:START:" + String(count));
    // Execute BLE spam
    currentAttack = "BLE_SPAM";
  }
  // IR functionality commented out:
  /*
  else if (cmd == "IR CAPTURE") {
    sendResponse("IR_CAPTURE:START");
    currentAttack = "IR_CAPTURE";
  }
  else if (cmd.startsWith("IR SEND")) {
    String codeStr = cmd.substring(7);
    codeStr.trim();
    unsigned long code = strtoul(codeStr.c_str(), NULL, 16);
    sendResponse("IR_SEND:CODE:" + String(code, HEX));
    irsend.sendNEC(code, 32);
    currentAttack = "";
  }
  */
  else if (cmd == "RFID READ") {
    sendResponse("RFID_READ:START");
    // Execute RFID read
    currentAttack = "RFID_READ";
  }
  else if (cmd.startsWith("RFID WRITE")) {
    String data = cmd.substring(10);
    data.trim();
    sendResponse("RFID_WRITE:DATA:" + data);
    // Execute RFID write
    currentAttack = "RFID_WRITE";
  }
  else if (cmd.startsWith("EVIL TWIN")) {
    String ssid = cmd.substring(9);
    ssid.trim();
    if (ssid.length() == 0) {
      sendResponse("ERROR:NO_SSID");
      return;
    }
    sendResponse("EVIL_TWIN:START:" + ssid);
    // Setup evil twin
    currentAttack = "EVIL_TWIN";
  }
  else if (cmd == "STOP") {
    sendResponse("STOPPED:" + currentAttack);
    currentAttack = "";
  }
  else if (cmd.length() > 0) {
    sendResponse("ERROR:UNKNOWN_COMMAND");
  }
}

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
