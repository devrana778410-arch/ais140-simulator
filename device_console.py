# Standalone Interactive Command Console for GPS Devices & Gateways
# Supports:
#   1. Remote Gateway / Server Client (tracktcp.gpsbull.com:5179, Parivahan, etc.)
#   2. Direct Hardware Tracker Listener (Listen on port 8600/5179/5000 so real GPS hardware connects directly to this PC)
#   3. Complete AIS-140 / Bull / Traxsmart Diagnostic & Configuration Command Cheatsheet

import sys
import socket
import threading
import time

def print_banner():
    print("=" * 72)
    print("   🛰️  AIS-140 & GPS TRACKER INTERACTIVE COMMAND CONSOLE")
    print("=" * 72)
    print("Modes:")
    print("  [1] Connect to Remote Gateway / Server Socket (e.g. tracktcp.gpsbull.com:5179)")
    print("  [2] Listen for Direct Hardware Tracker Connections (Local Server Mode)")
    print("  [3] Show Complete Hardware Diagnostic & Configuration Command Cheatsheet")
    print("=" * 72)

def print_cheatsheet():
    print("\n" + "=" * 72)
    print("   📋 AIS-140 & TRACKER HARDWARE COMMAND CHEATSHEET")
    print("=" * 72)
    print("""
1. CONNECTION & DIAGNOSTIC DISCOVERY COMMANDS:
   • GETSTATS
     -> Returns: All 3 Server IPs (IP1, IP2, IP3), Mains/Battery Voltages,
                 SIM ICCID, Signal (CSQ), Active eSIM profile, Telemetry Intervals,
                 GPS Satellite Fix, Tamper status, and Packet Sequence No.
   • GETCONFIG
     -> Returns: Vehicle No (VEH), APN (e.g. m2misafe), Turn Angle, Odometer,
                 OBD state, Accelerometer calibration, Harsh driving thresholds
                 (HA, HB, RT), Overspeed limit (OST), and Firmware Version (VER).
   • GETLIVE
     -> Prompts immediate live $PVT / AIS-140 location packet over IP3.

2. SERVER ROUTING & NETWORK CONFIGURATION:
   • SETIP1,<host>,<port>    -> Set Primary Parivahan/Govt Server (e.g. commonlayer.parivahan.gov.in,9031)
   • SETIP2,<host>,<port>    -> Set Emergency SOS Server (e.g. commonlayer.parivahan.gov.in,9032)
   • SETIP3,<host>,<port>    -> Set Vendor Live Telemetry Server (e.g. tracktcp.gpsbull.com,5179)
   • SETIP4,<host>,<port>    -> Secondary/Backup vendor stream (Admin unlocked)
   • SETIP5,<host>,<port>    -> Secondary/Backup vendor stream (Admin unlocked)
   • APN,<apn_name>#         -> Configure GPRS APN (e.g. APN,m2misafe#)

3. ACTIVATION & VEHICLE BINDING:
   • SETVRN <vehicle_number> -> Sets Vehicle Registration Number (e.g. SETVRN MH12AB1234)
   • ACTV,<phone_number>     -> Initiates VLTD Activation handshake with Govt/Portal
   • SETPRT <p1>,<p2>,<p3>,<p4> -> Protocol mode (e.g. SETPRT NIC,NIC,NIC,NIC)

4. TRANSMISSION INTERVALS:
   • INT1:15,60,3600,60,60   -> Moving(15s), Stopped(60s), Standby(3600s), Health(60s), OBD(60s)
   • INT3:15,120,3600,600    -> Vendor OTA Interval: Moving(15s), Stopped(120s), Standby(3600s)
   • INTEMG:10               -> Emergency SOS reporting frequency (10 seconds)

5. MAINTENANCE & CONTROL:
   • RESET# / REBOOT#        -> Soft-reboots the tracker MCU and 4G modem
   • FACTORY#                -> Restores tracker to factory defaults
   • CLRBUF                  -> Flushes offline buffered packets from flash memory
""")
    print("=" * 72 + "\n")

def receiver_loop(sock, stop_event):
    while not stop_event.is_set():
        try:
            data = sock.recv(4096)
            if not data:
                print("\n[!] Connection closed by remote side.")
                stop_event.set()
                break
            ts = time.strftime("%H:%M:%S")
            text = data.decode("utf-8", errors="replace")
            for line in text.splitlines():
                line_str = line.strip()
                if not line_str:
                    continue
                if "OK" in line_str:
                    print(f"\n\033[92m[{ts}] ← {line_str}\033[0m")
                elif line_str.startswith("IP1:") or line_str.startswith("IP2:") or line_str.startswith("IP3:"):
                    print(f"\033[93m[{ts}]   🌐 {line_str}\033[0m")
                elif line_str.startswith("SIG:") or line_str.startswith("MAINS:") or line_str.startswith("GPS:"):
                    print(f"\033[96m[{ts}]   ⚡ {line_str}\033[0m")
                elif line_str.startswith("$PVT") or line_str.startswith("GPSBULL") or line_str.startswith("$NMP"):
                    print(f"\n\033[92m[{ts}] ← {line_str}\033[0m")
                elif line_str.startswith("$HEL"):
                    print(f"\n\033[93m[{ts}] ← {line_str}\033[0m")
                else:
                    print(f"[{ts}]   {line_str}")
            print("Console > ", end="", flush=True)
        except socket.timeout:
            continue
        except Exception as e:
            if not stop_event.is_set():
                print(f"\n[!] Socket error: {e}")
                stop_event.set()
            break

def interactive_shell(sock, stop_event):
    print("\n[+] Console ready. Type your commands below.")
    print("    Quick Shortcuts:")
    print("      'getstats'             -> GETSTATS (Reveals all 3 IPs, voltage, signal, SIM)")
    print("      'getconfig'            -> GETCONFIG (Reveals APN, vehicle reg, thresholds)")
    print("      'getlive'              -> GETLIVE (Forces live position packet)")
    print("      'setip1 <host> <port>' -> SETIP1,<host>,<port> (Primary Parivahan)")
    print("      'setip2 <host> <port>' -> SETIP2,<host>,<port> (Parivahan SOS)")
    print("      'setip3 <host> <port>' -> SETIP3,<host>,<port> (Vendor Server)")
    print("      'setvrn <reg_no>'      -> SETVRN <reg_no> (Set Vehicle Number)")
    print("      'actv <phone>'         -> ACTV,<phone> (Activation handshake)")
    print("      'reset' / 'reboot'     -> RESET# (Reboot device MCU & modem)")
    print("      'help'                 -> Show full command cheatsheet")
    print("      'exit'                 -> Close connection & quit\n")

    while not stop_event.is_set():
        try:
            cmd = input("Console > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                stop_event.set()
                break

            cmd_lower = cmd.lower()
            if cmd_lower == "help":
                print_cheatsheet()
                continue
            elif cmd_lower == "getstats":
                payload = "GETSTATS\r\n"
            elif cmd_lower == "getconfig":
                payload = "GETCONFIG\r\n"
            elif cmd_lower == "getlive":
                payload = "GETLIVE\r\n"
            elif cmd_lower.startswith("setip1 "):
                parts = cmd.split()
                if len(parts) >= 3:
                    payload = f"SETIP1,{parts[1]},{parts[2]}\r\n"
                else:
                    print("[!] Usage: setip1 <host> <port>")
                    continue
            elif cmd_lower.startswith("setip2 "):
                parts = cmd.split()
                if len(parts) >= 3:
                    payload = f"SETIP2,{parts[1]},{parts[2]}\r\n"
                else:
                    print("[!] Usage: setip2 <host> <port>")
                    continue
            elif cmd_lower.startswith("setip3 ") or cmd_lower.startswith("setip "):
                parts = cmd.split()
                if len(parts) >= 3:
                    payload = f"SETIP3,{parts[1]},{parts[2]}\r\n"
                else:
                    print("[!] Usage: setip3 <host> <port>")
                    continue
            elif cmd_lower.startswith("setvrn "):
                parts = cmd.split(maxsplit=1)
                if len(parts) >= 2:
                    payload = f"SETVRN {parts[1].strip()}\r\n"
                else:
                    print("[!] Usage: setvrn <vehicle_number>")
                    continue
            elif cmd_lower.startswith("actv "):
                parts = cmd.split(maxsplit=1)
                payload = f"ACTV,{parts[1].strip()}\r\n"
            elif cmd_lower in ("reset", "reboot"):
                payload = "RESET#\r\n"
            elif cmd_lower == "status":
                payload = "STATUS#\r\n"
            else:
                payload = cmd + ("\r\n" if not cmd.endswith("\r\n") else "")

            ts = time.strftime("%H:%M:%S")
            print(f"\033[94m[{ts}] → {payload.strip()}\033[0m")
            sock.sendall(payload.encode("utf-8"))
        except (KeyboardInterrupt, EOFError):
            stop_event.set()
            break
        except Exception as e:
            print(f"[!] Send error: {e}")
            break

def mode_client():
    host = input("Enter Target Host (default: tracktcp.gpsbull.com): ").strip() or "tracktcp.gpsbull.com"
    port_str = input("Enter Target Port (default: 5179): ").strip() or "5179"
    port = int(port_str)

    imei = input("Enter Device IMEI (e.g. 864000080731065 or press Enter to skip): ").strip()

    print(f"\n[*] Connecting to {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((host, port))
        sock.settimeout(1.0)
        print(f"[+] Connected to {host}:{port} successfully!")
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        return

    if imei:
        print(f"[*] Sending IMEI identifier {imei}...")
        sock.sendall(f"{imei}\r\n".encode("utf-8"))

    stop_event = threading.Event()
    recv_thread = threading.Thread(target=receiver_loop, args=(sock, stop_event), daemon=True)
    recv_thread.start()

    interactive_shell(sock, stop_event)
    sock.close()
    print("\n[*] Disconnected.")

def mode_server():
    port_str = input("Enter Port to listen on (default: 8600): ").strip() or "8600"
    port = int(port_str)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(1)

    print(f"\n[*] Listening on 0.0.0.0:{port}...")
    print(f"[*] Point your GPS tracker (SETIP3,<your_public_or_lan_ip>,{port}) to connect here.")
    print("[*] Waiting for incoming tracker connection (Press Ctrl+C to cancel)...")

    try:
        conn, addr = server.accept()
        print(f"\n[+] Hardware Tracker Connected from {addr[0]}:{addr[1]}!")
        conn.settimeout(1.0)

        stop_event = threading.Event()
        recv_thread = threading.Thread(target=receiver_loop, args=(conn, stop_event), daemon=True)
        recv_thread.start()

        interactive_shell(conn, stop_event)
        conn.close()
    except KeyboardInterrupt:
        print("\n[*] Listener stopped.")
    finally:
        server.close()

def main():
    print_banner()
    choice = input("Select Option (1, 2, or 3): ").strip()
    if choice == "3":
        print_cheatsheet()
    elif choice == "2":
        mode_server()
    else:
        mode_client()

if __name__ == "__main__":
    main()
