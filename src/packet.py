# AIS-140 CGM packet builder + HMAC signer
# Updated with Gagan (ROADRPA) protocol, XOR checksum injection, and 6ac1197229afb43f secret key
# Matches reverse-engineered specifications from app-debug.apk (TCP Continuous Client)
import hmac as _hmac
import hashlib
import datetime
from typing import Union

# Active signing key confirmed from app-debug.apk
DEFAULT_HMAC_KEY = "6ac1197229afb43f".encode("ascii")
LEGACY_HMAC_KEY = "26bcb9e368440d4a".encode("ascii")

# Default static cell tower NMR blocks for Gagan/Roadrpa profile
DEFAULT_GAGAN_CELL_DATA = (
    "14D0,E085,17,14D0,E086,13,14D0,C941,12,14CE,4BA0,00"
)

# Default static cell tower NMR blocks (legacy Traxina profile)
DEFAULT_CELL_DATA = (
    "16D5,56C5,56C2,"
    "16D5,14,5909,"
    "16D5,14,37CB,"
    "16D5,14,5980,"
    "16D5,14,0000"
)


def compute_hex_checksum(payload: str) -> str:
    """
    Computes 1-byte XOR checksum over UTF-8 bytes.
    Returns uppercase 2-character hex string (e.g. '7A').
    Matches computeHexChecksum() from app-debug.apk.
    """
    x = 0
    for b in payload.encode("utf-8"):
        x ^= b
    return f"{x:02X}"


def sign(body: str, key: Union[bytes, str] = DEFAULT_HMAC_KEY) -> str:
    """
    HMAC-SHA256 of body string using ASCII key bytes.
    Returns lowercase 64-char hex digest.
    """
    if isinstance(key, str):
        key = key.encode("ascii")
    return _hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()


def _fmt_coord(value: float, int_digits: int = 3) -> str:
    """Zero-pad coordinate integer part: 21.749826 -> '021.749826'"""
    value = abs(value)
    integer = int(value)
    frac = round((value - integer) * 1_000_000)
    return f"{integer:0{int_digits}d}.{frac:06d}"


def build_packet(
    imei: str,
    vreg: str       = "GJ01AC0000",
    ign: int        = 1,
    lat: float      = 21.749826,
    lat_h: str      = "N",
    lon: float      = 73.098231,
    lon_h: str      = "E",
    speed: float    = 0.0,
    heading: float  = 4.24,
    alt: int        = 50,
    pdop: float     = 39.1,
    hdop: float     = 0.70,
    vdop: float     = 0.40,
    operator: str   = "Airtel",
    main_pwr: int   = 1,
    gps_valid: int  = 1,
    main_v: float   = 28.0,
    bak_v: float    = 5.6,
    tamper: int     = 0,
    emg: str        = "C",
    sats: int       = 23,
    mcc: str        = "404",
    mnc: str        = "98",
    cell_data: str  = "",
    din: str        = "1100",
    odo: str        = "010672",
    adc1: float     = 44.29,
    adc2: float     = 44.64,
    vendor: str     = "ROADRPA",
    fw: str         = "1.3.1",
    nw: str         = "NR",
    seq: str        = "01",
    fix: str        = "L",
    alert_crash: int    = 0,
    alert_overload: int = 0,
    alert_geo: int      = 0,
    hmac_key: Union[bytes, str] = DEFAULT_HMAC_KEY,
    **_extra,   # absorb GUI-only keys like 'name', 'interval', etc.
) -> str:
    """
    Build a complete AIS-140 CGM wire packet with pre-HMAC XOR checksum and HMAC-SHA256 signature.
    Includes trailing '\\n' frame delimiter expected by CGM telematic gateways.
    """
    now = datetime.datetime.utcnow()
    gps_date = now.strftime("%d%m%Y")   # DDMMYYYY (e.g. 02112026)
    gps_time = now.strftime("%H%M%S")   # HHmmss   (e.g. 154407)

    # Format operator name correctly (canonicalize to Airtel / Voda / etc.)
    op_clean = "Airtel" if operator.lower() == "airtel" else operator

    # Normalize seq to 2 digits if integer
    if isinstance(seq, int) or (isinstance(seq, str) and seq.isdigit() and len(seq) == 1):
        seq_str = f"{int(seq):02d}"
    else:
        seq_str = str(seq)

    # Ensure latitude and longitude format
    lat_str = f"{abs(lat):.6f}"
    lon_str = f"{abs(lon):.6f}"

    if vendor.upper() in ("ROADRPA", "GAGAN"):
        c_data = cell_data if cell_data else DEFAULT_GAGAN_CELL_DATA
        payload = (
            f"$NRM,ROADRPA,{fw},{nw},{seq_str},{fix},{imei},{vreg},{ign},"
            f"{gps_date},{gps_time},{lat_str},{lat_h},{lon_str},{lon_h},"
            f"{speed:.1f},{heading:.2f},{alt},{pdop:.1f},{hdop:.2f},{vdop:.2f},"
            f"{op_clean},{main_pwr},{gps_valid},{main_v:.1f},{bak_v:.1f},{tamper},"
            f"{emg},{sats},{mcc},{mnc},{c_data},00,0000,0000,{din},00,"
            f"{odo},{adc1:.3f},{adc2:.3f},2963.767,()*"
        )
    else:
        # Legacy Traxina format
        c_data = cell_data if cell_data else DEFAULT_CELL_DATA
        payload = (
            f"$NMP,{vendor},{fw},{nw},{seq_str},{fix},{imei},{vreg},{ign},"
            f"{gps_date},{gps_time},"
            f"{_fmt_coord(lat)},{lat_h},{_fmt_coord(lon)},{lon_h},"
            f"{speed:.1f},{heading:.2f},{alt},"
            f"{pdop:.1f},{hdop:.1f},{vdop:.1f},"
            f"{op_clean.upper()},{main_pwr},{gps_valid},"
            f"{main_v:.1f},{bak_v:.1f},{tamper},{emg},{sats},"
            f"{mcc},{mnc},"
            f"{c_data},"
            f"{din},{odo},{adc1:.2f},{adc2:.2f},0,"
            f"({alert_crash},{alert_overload},{alert_geo})*"
        )

    # 1) Compute XOR checksum on payload ending in ')*'
    xor_chk = compute_hex_checksum(payload)

    # 2) Inject XOR checksum after ')*'
    if "()*" in payload:
        signed_body = payload.replace("()*", f"()*{xor_chk}")
    else:
        signed_body = f"{payload}{xor_chk}"

    # 3) Compute HMAC signature over the checksummed body
    sig = sign(signed_body, hmac_key)

    # 4) Return wire frame with trailing newline
    return f"{signed_body},{sig}\n"
