import unittest
import py_compile
import socket
import time
import os
import sys

# Ensure project root is in sys.path
BASE_DIR = r"D:\ais140sim\ais140-simulator-main"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.packet import (
    build_packet as build_cgm_packet,
    compute_hex_checksum,
    sign as hmac_sign,
    DEFAULT_HMAC_KEY,
)
from src.gui.device_tab import PROFILE_SERVER
from web.server import PROFILE_SERVERS


class TestCgmApkParity(unittest.TestCase):

    def test_hmac_key_is_updated(self):
        """Verify default HMAC key matches app-debug.apk."""
        self.assertEqual(DEFAULT_HMAC_KEY, b"6ac1197229afb43f")

    def test_xor_checksum_function(self):
        """Verify 1-byte XOR checksum computation."""
        test_str = "ABC"  # ord('A')=65, ord('B')=66, ord('C')=67 -> 65^66^67 = 64 = 0x40
        self.assertEqual(compute_hex_checksum(test_str), "40")

    def test_cgm_packet_structure_and_delimiter(self):
        """Verify packet has Gagan header, injected XOR checksum, HMAC, and newline."""
        pkt = build_cgm_packet(
            imei="864000080731065",
            vreg="GJ01AB1234",
            lat=21.749826,
            lon=73.098231,
            operator="Airtel",
        )
        self.assertTrue(pkt.startswith("$NRM,ROADRPA,1.3.1,NR,"), f"Header mismatch: {pkt[:30]}")
        self.assertTrue(pkt.endswith("\n"), "Packet must end with \\n delimiter")
        
        # Strip newline for inspection
        body_with_sig = pkt.strip()
        parts = body_with_sig.rsplit(",", 1)
        self.assertEqual(len(parts), 2, "Must contain body and 64-char HMAC signature")
        
        payload_with_xor, signature = parts
        self.assertEqual(len(signature), 64, "HMAC-SHA256 signature must be 64 lowercase hex chars")
        
        # Verify ()* has 2-char hex checksum appended
        self.assertIn("()*", payload_with_xor)
        idx = payload_with_xor.find("()*")
        xor_injected = payload_with_xor[idx+3:idx+5]
        self.assertEqual(len(xor_injected), 2)
        
        # Verify signature actually matches
        expected_sig = hmac_sign(payload_with_xor, DEFAULT_HMAC_KEY)
        self.assertEqual(signature, expected_sig)

    def test_port_configuration(self):
        """Verify port is set to 5001 across GUI and Web servers."""
        self.assertEqual(PROFILE_SERVER["CGM"]["port"], 5001)
        self.assertEqual(PROFILE_SERVERS["CGM"]["port"], 5001)

    def test_py_compile_all_modified_files(self):
        """Ensure all modified python files compile without syntax errors."""
        files = [
            os.path.join(BASE_DIR, "src", "packet.py"),
            os.path.join(BASE_DIR, "src", "client.py"),
            os.path.join(BASE_DIR, "src", "gpcb_packet.py"),
            os.path.join(BASE_DIR, "src", "gui", "device_tab.py"),
            os.path.join(BASE_DIR, "web", "server.py"),
        ]
        for f in files:
            py_compile.compile(f, doraise=True)


if __name__ == "__main__":
    unittest.main()
