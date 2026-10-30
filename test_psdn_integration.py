import sys
import os
import csv

BASE_DIR = r"D:\ais140sim\ais140-simulator-main"
sys.path.insert(0, BASE_DIR)

from src.psdn_packet import build_packet as build_psdn
from src.gui.app import PACKET_BUILDERS, PROFILE_BADGE_COLORS
from src.gui.device_tab import PROFILE_SERVER, PROFILES
from web.server import PACKET_BUILDERS as WEB_BUILDERS, PROFILE_SERVERS as WEB_SERVERS
from src.rto_data import get_rto_coords

def test_psdn_packet():
    pkt = build_psdn(imei="864000080731065", vreg="GJ01AC1234", lat=23.022505, lon=72.571362)
    assert pkt.startswith("$NRM,PSDN,1.ONTC,NR,01,L,864000080731065,GJ01AC1234,1,"), f"Header mismatch: {pkt[:60]}"
    assert "023.022505,N,072.571362,E" in pkt, f"Coords mismatch: {pkt}"
    assert pkt.endswith("23_08_23_1_49._C_1_0_1_75,C8CE79AC*"), f"Tail mismatch: {pkt[-40:]}"
    print("✅ test_psdn_packet PASSED")

def test_gui_registrations():
    assert "GPCB (PSDN)" in PROFILES, "GPCB (PSDN) not in PROFILES"
    assert "GPCB (PSDN)" in PROFILE_SERVER, "GPCB (PSDN) not in PROFILE_SERVER"
    assert PROFILE_SERVER["GPCB (PSDN)"]["host"] == "43.205.159.137"
    assert PROFILE_SERVER["GPCB (PSDN)"]["port"] == 17003
    assert "GPCB (PSDN)" in PACKET_BUILDERS, "GPCB (PSDN) not in PACKET_BUILDERS"
    assert "GPCB (PSDN)" in PROFILE_BADGE_COLORS, "GPCB (PSDN) not in PROFILE_BADGE_COLORS"
    print("✅ test_gui_registrations PASSED")

def test_web_registrations():
    assert "PSDN" in WEB_BUILDERS, "PSDN not in WEB_BUILDERS"
    assert "GPCB (PSDN)" in WEB_BUILDERS, "GPCB (PSDN) not in WEB_BUILDERS"
    assert WEB_SERVERS["PSDN"]["host"] == "43.205.159.137"
    assert WEB_SERVERS["PSDN"]["port"] == 17003
    print("✅ test_web_registrations PASSED")

def test_sample_csv():
    csv_path = os.path.join(BASE_DIR, "sample_vehicles.csv")
    assert os.path.exists(csv_path), "sample_vehicles.csv missing"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 5, f"Expected 5 sample rows, got {len(rows)}"
    first = rows[0]
    assert first["imei"] == "864000080731065"
    assert first["vehicle_no"] == "GJ01AC1234"
    print(f"✅ test_sample_csv PASSED ({len(rows)} vehicles parsed cleanly)")

if __name__ == "__main__":
    print("--- RUNNING INTEGRATION TESTS ---")
    test_psdn_packet()
    test_gui_registrations()
    test_web_registrations()
    test_sample_csv()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
