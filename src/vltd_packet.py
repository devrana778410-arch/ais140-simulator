# AIS-140 VLTD packet builder
# Official MoRTH / Parivahan Common Layer format
# Primary: commonlayer.parivahan.gov.in:9031 (LGN, HEL, PVT)
# Emergency: commonlayer.parivahan.gov.in:9032 (EPB,EMR / EPB,SEM)
#
# Implements all 5 VLTD packets:
#   1. $LGN     - Login packet (sent on connect to port 9031)
#   2. $HEL     - Health / Diagnostic packet (sent to port 9031)
#   3. $PVT     - Position / Velocity / Time tracking packet (sent to port 9031)
#   4. $EPB,EMR - Emergency ON (SOS Panic triggered, sent to port 9032)
#   5. $EPB,SEM - Emergency OFF (SOS Cleared, sent to port 9032)
import datetime

DEFAULT_VLTD_CELL_DATA = "20a8,6359,62b9,20a8,17,635a,20a8,15,6357,20a8,12,621a,20a8,11"


def build_login_packet(
    imei: str,
    vreg: str = "GJ01AC0000",
    lat: float = 0.0,
    lon: float = 0.0,
    fw: str = "4.1.01",
    **_extra,
) -> str:
    """
    Build VLTD $LGN Login packet.
    Format: $LGN,{VREG},{IMEI},{FW},AIS140,{LAT},{LON},*
    Example: $LGN,GJ01AC0000,869833088601301,4.1.01,AIS140,00.000000,00.000000,*
    """
    if lat == 0.0 and lon == 0.0:
        lat_str = "00.000000"
        lon_str = "00.000000"
    else:
        lat_str = f"{lat:09.6f}"
        lon_str = f"{lon:09.6f}"
    return f"$LGN,{vreg},{imei},{fw},AIS140,{lat_str},{lon_str},*"


def build_health_packet(
    imei: str,
    vendor: str = "TRAXINA",
    fw: str = "4.1.01",
    batt_pct: int = 100,
    low_batt: int = 20,
    mem_alert: int = 8,
    ign_on_interval: int = 10,
    ign_off_interval: int = 180,
    di_do: str = "0000",
    seq: str = "00",
    **_extra,
) -> str:
    """
    Build VLTD $HEL Health / Keepalive packet.
    Format: $HEL,{VENDOR},{FW},{IMEI},{BATT_PCT},{LOW_BATT},{MEM_ALERT},{IGN_ON_INT},{IGN_OFF_INT},{DI_DO},{SEQ}*
    Example: $HEL,TRAXINA,4.1.01,869833088601301,100,20,8,10,180,0000,00*
    """
    return f"$HEL,{vendor},{fw},{imei},{batt_pct},{low_batt},{mem_alert},{ign_on_interval},{ign_off_interval},{di_do},{seq}*"


def build_pvt_packet(
    imei: str,
    vreg: str = "GJ01AC0000",
    lat: float = 22.3004010,
    lon: float = 70.8046280,
    seq_num: int = 1,
    speed: float = 0.0,
    heading: float = 247.54,
    alt: int = 37,
    pdop: float = 20.940,
    hdop: float = 0.75,
    vdop: float = 0.46,
    operator: str = "AIRTEL",
    main_pwr: int = 0,
    gps_valid: int = 1,
    main_v: float = 12.5,
    bat_v: float = 4.2,
    tamper: int = 0,
    emg_flag: str = "O",   # 'O' = normal/off, 'E' = emergency active
    sats: int = 27,
    mcc: str = "404",
    mnc: str = "51",
    cell_data: str = DEFAULT_VLTD_CELL_DATA,
    din: str = "0001",
    dout: str = "00",
    checksum: str = "D3",
    vendor: str = "TRAXINA",
    fw: str = "4.1.01",
    nw: str = "NR",
    fix: str = "L",
    **_extra,
) -> str:
    """
    Build VLTD $PVT periodic tracking packet.
    Format matching confirmed wire capture on 2026-10-23.
    """
    now = datetime.datetime.utcnow()
    gps_date = now.strftime("%d%m%Y")
    gps_time = now.strftime("%H%M%S")
    seq_str = f"{seq_num:06d}"

    return (
        f"$PVT,{vendor},{fw},{nw},1,{fix},{imei},{vreg},1,"
        f"{gps_date},{gps_time},"
        f"{lat:.7f},N,{lon:.7f},E,"
        f"{speed:05.1f},{heading:.2f},{alt},"
        f"{pdop:.3f},{hdop:.2f},{vdop:.2f},"
        f"{operator},{main_pwr},{gps_valid},"
        f"{main_v:.1f},{bat_v:.1f},{tamper},{emg_flag},{sats},"
        f"{mcc},{mnc},{cell_data},"
        f"{din},{dout},{seq_str},{checksum}*"
    )


def build_emergency_packet(
    imei: str,
    vreg: str = "GJ01AC0000",
    mode: str = "EMR",    # "EMR" = Emergency ON, "SEM" = Emergency OFF (Stop Emergency)
    lat: float = 22.3004010,
    lon: float = 70.8046280,
    mobile: str = "+910000000000",
    seq_num: int = 1000,
    **_extra,
) -> str:
    """
    Build VLTD $EPB Emergency Alert / Stop Emergency packet.
    Format matching confirmed wire capture on 2026-10-23.
    """
    now = datetime.datetime.utcnow()
    dt_str = now.strftime("%d%m%Y%H%M%S")
    seq_str = f"{seq_num:08d}"

    return (
        f"$EPB,{mode},{imei},NM,{dt_str},A,"
        f"{lat:.7f},N,{lon:.7f},E,"
        f"000.0,0.0,000.0,G,{vreg},{mobile},*,{seq_str}"
    )


# Default packet builder alias for VLTD periodic transmission
build_packet = build_pvt_packet
