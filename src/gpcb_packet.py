# AIS-140 GPCB packet builder
# GPCB uses the exact same $NMP wire format as CGM,
# but WITHOUT the trailing HMAC signature.
# Confirmed from TCP proxy capture on 2026-10-23.
#
# Server: 103.234.162.31:9999
# Wire:   {body}   (ends at )*)  — NO comma, NO hash
from .packet import (
    build_packet as _build_cgm,
    DEFAULT_CELL_DATA,
)
import datetime


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
    **_extra,   # absorb GUI-only keys like 'name', 'interval', 'hmac_key'
) -> str:
    """
    Build a complete AIS-140 GPCB wire packet.
    Identical structure to CGM $NMP but NO HMAC appended.
    Ends at )* — no trailing comma or signature.
    """
    from .packet import _fmt_coord
    now = datetime.datetime.utcnow()
    gps_date = now.strftime("%d%m%Y")
    gps_time = now.strftime("%H%M%S")

    return (
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
