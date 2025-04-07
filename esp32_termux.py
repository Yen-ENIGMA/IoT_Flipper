#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import getpass

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
COMMAND_TOPIC = "esp32/commands"
LOGS_TOPIC = "esp32/logs"

# Allowed users and their passwords
ALLOWED_USERS = {
    "VNCNT": "9142327534",
    "VSPR": "9567283585",
    "KSYP": "8606413490"
}

def authenticate():
    print("==== ESP32 Remote Control Login ====")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()
    if username in ALLOWED_USERS and ALLOWED_USERS[username] == password:
        print("Authentication successful.\n")
        return True
    else:
        print("Authentication failed. Exiting...")
        return False

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode('utf-8')
        data = json.loads(payload)
        print("Log:", json.dumps(data, indent=2))
    except Exception as e:
        print("Error decoding message:", e)

client = mqtt.Client("TermuxClient")
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(LOGS_TOPIC)
client.loop_start()

def send_command(cmd, params=None):
    if params is None:
        params = {}
    payload = {"cmd": cmd}
    payload.update(params)
    client.publish(COMMAND_TOPIC, json.dumps(payload))
    print("Command sent:", json.dumps(payload))

def main_menu():
    # Authenticate user first
    if not authenticate():
        exit(1)
    
    while True:
        print("\n=== ESP32 Remote Control Menu ===")
        print("1) Wi-Fi: Scan")
        print("2) Wi-Fi: Deauth")
        print("3) Wi-Fi: Beacon Flood")
        print("4) Wi-Fi: Jam")
        print("5) Bluetooth: Scan")
        print("6) Bluetooth: Spam Pair")
        print("7) NFC: Scan")
        print("8) NFC: List")
        print("9) NFC: Save")
        print("0) Exit")
        choice = input("Enter choice: ")
        if choice == "1":
            send_command("wifi_scan")
        elif choice == "2":
            target = input("Enter target MAC: ")
            send_command("wifi_deauth", {"target": target})
        elif choice == "3":
            prefix = input("Enter SSID prefix: ")
            count = int(input("Enter beacon count: "))
            send_command("wifi_beacon", {"prefix": prefix, "count": count})
        elif choice == "4":
            channel = int(input("Enter channel: "))
            send_command("wifi_jam", {"channel": channel})
        elif choice == "5":
            send_command("bt_scan")
        elif choice == "6":
            device = input("Enter Bluetooth device address: ")
            send_command("bt_spampair", {"device": device})
        elif choice == "7":
            send_command("nfc_scan")
        elif choice == "8":
            send_command("nfc_list")
        elif choice == "9":
            name = input("Enter name for NFC tag: ")
            send_command("nfc_save", {"name": name})
        elif choice == "0":
            break
        else:
            print("Invalid choice.")
        # Allow time to receive logs
        time.sleep(2)
        
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main_menu()
