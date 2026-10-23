# AIS-140 CGM packet builder + HMAC signer
# Confirmed wire format from TCP proxy capture on 2026-10-23
import hmac as _hmac
import hashlib
import datetime

# Signing key: ASCII bytes of the hex key string (NOT hex-decoded — 16 bytes)
DEFAULT_HMAC_KEY = "26bcb9e368440d4a".encode("ascii")

# Default static cell tower NMR blocks (from captured packets)
DEFAULT_CELL_DATA = (
    "16D5,56C5,56C2,"
    "16D5,14,5909,"
    "16D5,14,37CB,"
    "16D5,14,5980,"
    "16D5,14,0000"
)


def sign(body: str, key: bytes = DEFAULT_HMAC_KEY) -> str:
    """
    HMAC-SHA256 of body string using ASCII key bytes.
    body must end with ')*' (the alert tuple closing).
    Returns lowercase 64-char hex digest.
    """
    return _hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()


def _fmt_coord(value: float, int_digits: int = 3) -> str:
    """Zero-pad coordinate integer part: 21.749826 -> '021.749826'"""
    neg = value < 0
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
    heading: float  = 208.53,
    alt: int        = 46,
    pdop: float     = 136.7,
    hdop: float     = 0.7,
    vdop: float     = 0.4,
    operator: str   = "AIRTEL",
    main_pwr: int   = 0,
    gps_valid: int  = 1,
    main_v: float   = 25.8,
    bak_v: float    = 4.0,
    tamper: int     = 0,
    emg: str        = "C",
    sats: int       = 13,
    mcc: str        = "404",
    mnc: str        = "05",
    cell_data: str  = DEFAULT_CELL_DATA,
    din: str        = "00",
    odo: str        = "001994",
    adc1: float     = 0.80,
    adc2: float     = 0.00,
    vendor: str     = "TRAXINA",
    fw: str         = "4.0.27",
    nw: str         = "NR",
    seq: str        = "01",
    fix: str        = "L",
    alert_crash: int    = 0,
    alert_overload: int = 0,
    alert_geo: int      = 0,
    hmac_key: bytes = DEFAULT_HMAC_KEY,
    **_extra,   # absorb GUI-only keys like 'name', 'interval'
) -> str:
    """
    Build a complete AIS-140 $NMP wire packet with HMAC signature.
    GPS timestamp uses current UTC time.
    No \\r\\n — server is silent fire-and-forget.
    """
    now = datetime.datetime.utcnow()
    gps_date = now.strftime("%d%m%Y")   # DDMMYYYY (e.g. 23102026)
    gps_time = now.strftime("%H%M%S")   # HHmmss   (e.g. 154407)

    body = (
        f"$NMP,{vendor},{fw},{nw},{seq},{fix},{imei},{vreg},{ign},"
        f"{gps_date},{gps_time},"
        f"{_fmt_coord(lat)},{lat_h},{_fmt_coord(lon)},{lon_h},"
        f"{speed:.1f},{heading:.2f},{alt},"
        f"{pdop:.1f},{hdop:.1f},{vdop:.1f},"
        f"{operator},{main_pwr},{gps_valid},"
        f"{main_v:.1f},{bak_v:.1f},{tamper},{emg},{sats},"
        f"{mcc},{mnc},"
        f"{cell_data},"
        f"{din},{odo},{adc1:.2f},{adc2:.2f},0,"
        f"({alert_crash},{alert_overload},{alert_geo})*"
    )
    return f"{body},{sign(body, hmac_key)}"
