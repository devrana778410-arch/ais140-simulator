# Standalone Interactive Command Console for GPS Devices & Gateways
# Supports both:
#   1. Gateway / Device Channel Client (Connect to ddr.gpsbull.com, Traxsmart, or Parivahan)
#   2. Hardware Tracker Listener (Listen on port 8600/5000 so real GPS hardware connects directly to you)

import sys
import socket
import threading
import time

def print_banner():
    print("=" * 65)
    print("   🛰️  AIS-140 & GPS TRACKER INTERACTIVE COMMAND CONSOLE")
    print("=" * 65)
    print("Modes:")
    print("  [1] Connect to Remote Gateway / Server (e.g. ddr.gpsbull.com:8600)")
    print("  [2] Listen for Direct Hardware Tracker Connections (Server Mode)")
    print("=" * 65)

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
            # Highlight device responses
            for line in text.splitlines():
                if line.strip():
                    if "OK" in line:
                        print(f"\n\033[92m[{ts}] ← {line}\033[0m")
                    elif line.startswith("$PVT"):
                        print(f"\n\033[96m[{ts}] ← {line}\033[0m")
                    elif line.startswith("$HEL"):
                        print(f"\n\033[93m[{ts}] ← {line}\033[0m")
                    else:
                        print(f"\n[{ts}] ← {line}")
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
    print("    Quick shortcuts:")
    print("      'getlive' -> GETLIVE")
    print("      'setip <host> <port>' -> SETIP3,<host>,<port>")
    print("      'status'  -> STATUS#")
    print("      'exit'    -> Close connection & quit\n")

    while not stop_event.is_set():
        try:
            cmd = input("Console > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                stop_event.set()
                break

            # Handle friendly shortcuts
            if cmd.lower() == "getlive":
                payload = "GETLIVE\r\n"
            elif cmd.lower().startswith("setip "):
                parts = cmd.split()
                if len(parts) >= 3:
                    payload = f"SETIP3,{parts[1]},{parts[2]}\r\n"
                else:
                    print("[!] Usage: setip <host> <port>")
                    continue
            elif cmd.lower() == "status":
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
    host = input("Enter Target Host (default: ddr.gpsbull.com): ").strip() or "ddr.gpsbull.com"
    port_str = input("Enter Target Port (default: 8600): ").strip() or "8600"
    port = int(port_str)

    imei = input("Enter Device IMEI (e.g. 866192079747836 or press Enter to skip): ").strip()

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

    # If an IMEI / channel handshake is needed
    if imei:
        print(f"[*] Joining device channel for IMEI {imei}...")
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
    print(f"[*] Point your GPS tracker to this machine's IP and port {port}.")
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
    choice = input("Select Mode (1 or 2): ").strip()
    if choice == "2":
        mode_server()
    else:
        mode_client()

if __name__ == "__main__":
    main()
