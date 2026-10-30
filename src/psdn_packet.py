# AIS-140 / PSDN (ONTC) packet builder
# Specific protocol variant used by Gujarat Pollution Control Board / PSDN telemetry gateways
# Reverse-engineered from com.example.tcpforpsdn (base.apk)
#
# Default Server: 43.205.159.137:17003
# Wire format:
#   $NRM,PSDN,1.ONTC,NR,01,L,<IMEI>,<VEHICLE_NO>,1,<DDMMYYYY>,<HHMMSS>,<LAT>,N,<LON>,E,0.1,000.00,17,0044.98,1.00,0.59,<OPERATOR>,0,1,26.0,4.0,0,O,16,404,98,140c,ee1,ed8,140c,11,edd,140c,03,0000,0000,00,0000,0000,00,0000,00,0.000,0.000,002421,0.140,-,1.0,0,0,23_08_23_1_49._C_1_0_1_75,C8CE79AC*

import datetime
from typing import Optional


def _fmt_coord(value: float, int_digits: int = 3) -> str:
    """Format coordinates to zero-padded 6 decimal places (e.g. 021.749826, 073.098231)."""
    abs_v = abs(value)
    int_part = int(abs_v)
    frac_part = int(round((abs_v - int_part) * 1_000_000))
    return f"{int_part:0{int_digits}d}.{frac_part:06d}"


def build_packet(
    imei: str,
    vreg: str = "GJ01AC0000",
    lat: float = 21.749826,
    lat_h: str = "N",
    lon: float = 73.098231,
    lon_h: str = "E",
    speed: float = 0.1,
    heading: float = 0.0,
    operator: str = "airtel",
    mcc: str = "404",
    mnc: str = "98",
    seq: str = "01",
    fix: str = "L",
    **_extra,  # absorb GUI keys like interval, name, hmac_key, etc.
) -> str:
    """
    Builds the official PSDN / ONTC GPCB telemetry wire packet.
    """
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%d%m%Y")
    time_str = now.strftime("%H%M%S")

    lat_str = _fmt_coord(lat, 3)
    lon_str = _fmt_coord(lon, 3)
    op_lower = operator.lower() if operator else "airtel"

    # Static cell tower telemetry & firmware token matching the ONTC gateway schema
    tail = (
        f"{speed:.1f},{heading:06.2f},17,0044.98,1.00,0.59,{op_lower},0,1,26.0,4.0,0,O,16,{mcc},{mnc},"
        f"140c,ee1,ed8,140c,11,edd,140c,03,0000,0000,00,0000,0000,00,0000,00,"
        f"0.000,0.000,002421,0.140,-,1.0,0,0,23_08_23_1_49._C_1_0_1_75,C8CE79AC*"
    )

    return (
        f"$NRM,PSDN,1.ONTC,NR,{seq},{fix},"
        f"{imei},{vreg},1,"
        f"{date_str},{time_str},"
        f"{lat_str},{lat_h},"
        f"{lon_str},{lon_h},"
        f"{tail}"
    )
