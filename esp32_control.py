#!/usr/bin/env python3
import serial
import time
import threading
import os
import sys
import re
from colorama import init, Fore, Back, Style
import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

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
{Fore.CYAN}║ {Fore.YELLOW}Multi-Protocol Attack & Control Tool {Fore.GREEN}v1.0              {Fore.CYAN}  ║
{Fore.CYAN}║ {Fore.WHITE}WiFi | Bluetooth | IR | NFC                              {Fore.CYAN}║
{Fore.CYAN}╚══════════════════════════════════════════════════════════╝
"""

# Available commands for auto-completion
COMMANDS = [
    'help', 'exit', 'clear',
    'wifi scan', 'wifi deauth', 'wifi beacon', 'wifi jam', 'wifi eviltwin',
    'bt scan', 'bt spampair',
    'ir send', 'ir capture', 'ir replay',
    'nfc init', 'nfc scan', 'nfc save', 'nfc list', 'nfc clear', 'nfc load',
    'stop'
]

class ESP32Controller:
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.running = False
        self.reader_thread = None
        self.last_command = None
        self.command_running = False
    
    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Give ESP32 time to reset
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
        # Process different response types based on prefixes
        if response == "READY":
            print(f"{Fore.GREEN}[✓] ESP32 is ready")
            return
        parts = response.split(":")
        if len(parts) < 1:
            print(response)  # Print raw response if it doesn't match expected format
            return
        module_colors = {
            "WIFI": Fore.CYAN,
            "BT": Fore.BLUE,
            "IR": Fore.MAGENTA,
            "NFC": Fore.YELLOW,
            "ERROR": Fore.RED,
            "STATUS": Fore.WHITE
        }

# Extract module from the response
        module_action = parts[0].split("_")[0] if "_" in parts[0] else parts[0]
        color = module_colors.get(module_action, Fore.WHITE)

        if response.startswith("ERROR:"):
            print(f"{Fore.RED}[✗] {response[6:]}")
            self.command_running = False
        elif response.startswith("WIFI_SCAN:"):
            if "START" in response:
                print(f"{Fore.CYAN}[i] WiFi scanning started...")
            elif "FOUND" in response:
                count = parts[2] if len(parts) > 2 else "?"
                print(f"{Fore.CYAN}[i] Found {count} networks")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] WiFi scan completed")
                self.command_running = False
        elif response.startswith("WIFI_NETWORK:"):
            if len(parts) >= 5:
                mac = parts[1]
                ssid = parts[2]
                rssi = parts[3]
                channel = parts[4]
                print(f"{Fore.CYAN}  • {Fore.WHITE}{ssid} {Fore.YELLOW}({mac}) {Fore.GREEN}Ch:{channel} {Fore.BLUE}RSSI:{rssi}dBm")
        elif response.startswith("WIFI_DEAUTH:"):
            if "START" in response:
                target = parts[2] if len(parts) > 2 else "target"
                print(f"{Fore.CYAN}[i] Deauthentication attack started on {target}")
            elif "CHANNEL" in response:
                print(f"{Fore.CYAN}  • Sending deauth packets on channel {parts[2]}")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] Deauthentication attack completed")
                self.command_running = False
        elif response.startswith("WIFI_BEACON:"):
            if "START" in response:
                prefix = parts[2] if len(parts) > 2 else ""
                count = parts[3] if len(parts) > 3 else ""
                print(f"{Fore.CYAN}[i] Beacon flood started with prefix {prefix} ({count} networks)")
            elif "STATUS" in response:
                print(f"{Fore.CYAN}  • Beacon flood progress: {parts[2]}%")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] Beacon flood completed")
                self.command_running = False
        elif response.startswith("WIFI_JAM:"):
            if "START" in response:
                channel = parts[2] if len(parts) > 2 else "all"
                print(f"{Fore.CYAN}[i] WiFi jamming started on channel {channel}")
            elif "PACKETS" in response:
                print(f"{Fore.CYAN}  • Jamming packets sent: {parts[2]}")
            elif "COMPLETE" in response or "STOPPED" in response:
                print(f"{Fore.GREEN}[✓] WiFi jamming {parts[1].lower()}")
                self.command_running = False
        elif response.startswith("WIFI_EVILTWIN:"):
            if "START" in response:
                ssid = parts[2] if len(parts) > 2 else "target"
                print(f"{Fore.CYAN}[i] Evil Twin attack started for {ssid}")
            elif "RUNNING" in response:
                ip = parts[3] if len(parts) > 3 else "unknown"
                print(f"{Fore.CYAN}  • Evil Twin AP running with IP {ip}")
            elif "PASSWORD" in response:
                password = parts[2] if len(parts) > 2 else "unknown"
                print(f"{Fore.GREEN}[!] CAPTURED PASSWORD: {Fore.WHITE}{Back.RED}{password}{Style.RESET_ALL}")
        elif response.startswith("BT_SCAN:"):
            if "START" in response:
                print(f"{Fore.BLUE}[i] Bluetooth scanning started...")
            elif "FOUND" in response:
                count = parts[2] if len(parts) > 2 else "?"
                print(f"{Fore.BLUE}[i] Found {count} Bluetooth devices")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] Bluetooth scan completed")
                self.command_running = False
        elif response.startswith("BT_DEVICE:"):
            if len(parts) >= 4:
                address = parts[1]
                name = parts[2]
                rssi = parts[3]
                print(f"{Fore.BLUE}  • {Fore.WHITE}{name} {Fore.YELLOW}({address}) {Fore.BLUE}RSSI:{rssi}dBm")
        elif response.startswith("BT_SPAMPAIR:"):
            if "START" in response:
                print(f"{Fore.BLUE}[i] Bluetooth pairing spam started")
            elif "ADVERTISING" in response:
                device = parts[2] if len(parts) > 2 else "device"
                print(f"{Fore.BLUE}  • Advertising as {device}")
            elif "DEVICE_CONNECTED" in response:
                print(f"{Fore.GREEN}[!] Device connected to our fake Bluetooth device")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] Bluetooth pairing spam completed")
                self.command_running = False   
        elif response.startswith("IR_SEND:"):
            if "START" in response:
                code = parts[2] if len(parts) > 2 else "code"
                print(f"{Fore.MAGENTA}[i] Sending IR code: {code}")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] IR code sent")
                self.command_running = False
        elif response.startswith("IR_CAPTURE:"):
            if "START" in response:
                print(f"{Fore.MAGENTA}[i] IR capture started, point remote at device...")
            elif "WAITING" in response:
                print(f"{Fore.MAGENTA}  • Waiting for IR signal...")
            elif "CODE" in response:
                code = parts[2] if len(parts) > 2 else "unknown"
                print(f"{Fore.GREEN}[!] IR code captured: {Fore.WHITE}{code}")
        elif response.startswith("IR_REPLAY:"):
            if "START" in response:
                print(f"{Fore.MAGENTA}[i] Replaying last IR code")
            elif "ERROR" in response:
                print(f"{Fore.RED}[✗] {parts[2]}")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] IR code replayed")
                self.command_running = False
        elif response.startswith("NFC_INIT:"):
            if "START" in response:
                print(f"{Fore.YELLOW}[i] Initializing NFC reader...")
            elif "ERROR" in response:
                print(f"{Fore.RED}[✗] NFC initialization failed:...")
            elif "ERROR" in response:
                print(f"{Fore.RED}[✗] NFC initialization failed: {parts[2]}")
                self.command_running = False
            elif "COMPLETE" in response:
                version = parts[3] if len(parts) > 3 else "unknown"
                print(f"{Fore.GREEN}[✓] NFC reader initialized (Version: {version})")
                self.command_running = False
        elif response.startswith("NFC_SCAN:"):
            if "START" in response:
                print(f"{Fore.YELLOW}[i] NFC scanning started, place card on reader...")
            elif "FOUND" in response:
                uid = parts[3] if len(parts) > 3 else "unknown"
                type_info = parts[5] if len(parts) > 5 else "unknown"
                print(f"{Fore.GREEN}[!] NFC card found: {Fore.WHITE}{uid} {Fore.YELLOW}(Type: {type_info})")
            elif "TIMEOUT" in response:
                print(f"{Fore.YELLOW}[i] NFC scan timed out, no card detected")
                self.command_running = False
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] NFC scan completed")
                self.command_running = False
        elif response.startswith("NFC_SAVE:"):
            if "ERROR" in response:
                print(f"{Fore.RED}[✗] Failed to save NFC UID: {parts[2]}")
                self.command_running = False
            elif "FLASH" in response:
                print(f"{Fore.YELLOW}  • Saved to flash memory")
            elif "COMPLETE" in response:
                name = parts[3] if len(parts) > 3 else "unknown"
                uid = parts[5] if len(parts) > 5 else "unknown"
                print(f"{Fore.GREEN}[✓] NFC UID saved as '{name}': {uid}")
                self.command_running = False
        elif response.startswith("NFC_LIST:"):
            if "COUNT" in response:
                count = parts[2] if len(parts) > 2 else "0"
                print(f"{Fore.YELLOW}[i] Saved NFC UIDs: {count}")
            elif "ENTRY" in response:
                index = parts[2]
                entry = ":".join(parts[3:])
                print(f"{Fore.YELLOW}  • [{index}] {Fore.WHITE}{entry}")
            elif "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] NFC list completed")
                self.command_running = False
                
        elif response.startswith("NFC_CLEAR:"):
            if "COMPLETE" in response:
                print(f"{Fore.GREEN}[✓] All saved NFC UIDs cleared")
                self.command_running = False
                
        elif response.startswith("NFC_LOAD:"):
            if "FLASH" in response:
                count = parts[4] if len(parts) > 4 else "0"
                print(f"{Fore.GREEN}[✓] Loaded {count} NFC UIDs from flash")
                self.command_running = False
                
        elif response.startswith("STOP:"):
            attack = parts[1] if len(parts) > 1 else "attack"
            print(f"{Fore.YELLOW}[i] Stopping {attack}...")
            
        elif response.startswith("STATUS:"):
            if "NO_ATTACK_RUNNING" in response:
                print(f"{Fore.YELLOW}[i] No attack is currently running")
            elif "STOPPED" in response:
                print(f"{Fore.GREEN}[✓] Attack stopped successfully")
                self.command_running = False
        else:
            # Print any other responses with the module's color
            print(f"{color}[i] {response}")
    
    def send_command(self, command):
        if not self.serial or not self.serial.is_open:
            print(f"{Fore.RED}[✗] Not connected to ESP32")
            return False
        
        try:
            self.last_command = command
            self.command_running = True
            
            # Send the command
            self.serial.write((command + '\n').encode('utf-8'))
            self.serial.flush()
            
            # Special case for 'stop' command
            if command.lower() == 'stop':
                print(f"{Fore.YELLOW}[i] Sending stop command...")
                
            return True
        except Exception as e:
            print(f"{Fore.RED}[✗] Failed to send command: {e}")
            return False
    
    def stop_current_command(self):
        if self.command_running:
            self.send_command('STOP')
def print_help():
    print(f"\n{Fore.GREEN}Available Commands:{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}General Commands:{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}help{Style.RESET_ALL}                   - Show this help message")
    print(f"  {Fore.WHITE}exit{Style.RESET_ALL}                   - Exit the program")
    print(f"  {Fore.WHITE}clear{Style.RESET_ALL}                  - Clear the screen")
    print(f"  {Fore.WHITE}stop{Style.RESET_ALL}                   - Stop any running attack")
    
    print(f"\n{Fore.CYAN}WiFi Commands:{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}wifi scan{Style.RESET_ALL}              - Scan for WiFi networks")
    print(f"  {Fore.WHITE}wifi deauth <mac>{Style.RESET_ALL}      - Deauthenticate a device by MAC")
    print(f"  {Fore.WHITE}wifi beacon <prefix> <count>{Style.RESET_ALL} - Create fake access points")
    print(f"  {Fore.WHITE}wifi jam <channel>{Style.RESET_ALL}     - Jam WiFi on specified channel")
    print(f"  {Fore.WHITE}wifi eviltwin <ssid> <channel>{Style.RESET_ALL} - Create evil twin AP")
    
    print(f"\n{Fore.BLUE}Bluetooth Commands:{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}bt scan{Style.RESET_ALL}                - Scan for Bluetooth devices")
    print(f"  {Fore.WHITE}bt spampair{Style.RESET_ALL}            - Spam pairing requests")
    
    print(f"\n{Fore.MAGENTA}IR Commands:{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}ir send <code>{Style.RESET_ALL}         - Send IR code (hex)")
    print(f"  {Fore.WHITE}ir capture{Style.RESET_ALL}             - Capture IR code from remote")
    print(f"  {Fore.WHITE}ir replay{Style.RESET_ALL}              - Replay last captured IR code")
    
    print(f"\n{Fore.YELLOW}NFC Commands:{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}nfc init{Style.RESET_ALL}               - Initialize NFC reader")
    print(f"  {Fore.WHITE}nfc scan{Style.RESET_ALL}               - Scan for NFC tags")
    print(f"  {Fore.WHITE}nfc save <name>{Style.RESET_ALL}        - Save last scanned tag with name")
    print(f"  {Fore.WHITE}nfc list{Style.RESET_ALL}               - List saved NFC tags")
    print(f"  {Fore.WHITE}nfc clear{Style.RESET_ALL}              - Clear all saved NFC tags")
    print(f"  {Fore.WHITE}nfc load {Style.RESET_ALL}       - Load saved NFC tags from flash")
    print()


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ESP32 Multi-Protocol Attack & Control Tool')
    parser.add_argument('-p', '--port', help='Serial port for ESP32', required=True)
    parser.add_argument('-b', '--baud', help='Baud rate (default: 115200)', type=int, default=115200)
    args = parser.parse_args()
    
    # Clear screen and show banner
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    
    # Initialize ESP32 controller
    controller = ESP32Controller(args.port, args.baud)
    if not controller.connect():
        sys.exit(1)
    
    # Start serial reader thread
    controller.start_reader()
    
    # Setup command history and auto-completion
    history_file = os.path.expanduser('~/.esp32_cli_history')
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        completer=WordCompleter(COMMANDS, ignore_case=True)
    )
    
    try:
        while True:
            try:
                # Get command with auto-completion
                command = session.prompt(f"{Fore.GREEN}ESP32>{Fore.WHITE} ")
                command = command.strip()
                
                # Process special commands
                if not command:
                    continue
                elif command.lower() == 'exit':
                    break
                elif command.lower() == 'help':
                    print_help()
                elif command.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(BANNER)
                else:
                    # Send command to ESP32
                    controller.send_command(command.upper())
            except KeyboardInterrupt:
                # Handle Ctrl+C to stop current command
                print(f"\n{Fore.YELLOW}[i] Stopping current command...")
                controller.stop_current_command()
            except EOFError:
                # Handle Ctrl+D to exit
                break
    finally:
        # Clean up
        controller.stop_reader()
        controller.disconnect()
        print(f"{Fore.YELLOW}Exiting. Goodbye!")

if __name__ == "__main__":
    main()
