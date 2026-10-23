# AIS-140 Multi-Profile Client Simulator

A pure Python (standard library only, zero pip dependencies) desktop GUI simulator for **AIS-140 Vehicle Location Tracking Devices (VLTD)**. 

Supports simultaneous multi-device simulation across three major Indian vehicle tracking profiles:
1. **CGM** (Chemical & Hazardous Goods Movers — Gujarat backend)
2. **GPCB** (Gujarat Pollution Control Board — Hazardous Waste Tracking)
3. **VLTD** (MoRTH / Parivahan National Common Layer)

---

## Features

* **Zero External Dependencies**: Pure Python 3.10+ standard library (`tkinter`, `socket`, `hmac`, `hashlib`, `threading`).
* **Multi-Device Tabbed Interface**: Run and monitor multiple devices independently or synchronize them via **Start All** / **Stop All**.
* **Profile-Specific Dynamic Forms**: Form fields dynamically adapt based on the selected profile.
* **42 Verified Gujarat & UT RTOs**: Built-in coordinates table covering GJ-01 to GJ-38, DD-01, DD-02, DN-01, and DN-09.
* **Dual-Port Routing for VLTD**:
  * **Primary Port (`9031`)**: Streams `$LGN` (Login), `$HEL` (Health), and `$PVT` (Position tracking).
  * **Emergency Port (`9032`)**: Dispatches `$EPB,EMR` (Emergency ON) and `$EPB,SEM` (Emergency OFF).
* **On-Demand Manual Packet Push**: Individual buttons to fire any of the 5 VLTD packets on demand.
* **Auto-Emergency Simulation**: Optional automated test cycle that triggers Emergency ON at cycle 3, runs for 2 intervals, and clears with Emergency OFF at cycle 5.
* **HMAC-SHA256 Signing (CGM)**: Live HMAC calculation with configurable key and visibility toggle.
* **Resilient Connection Management**: Transparent reconnection handling for transactional/stateless servers and servers with aggressive idle timeouts.
* **Live Logging & Export**: Color-coded per-device status, real-time packet hex/ASCII previews, master log, and text export.

---

## Profiles & Packet Formats

### 1. CGM Profile
* **Endpoint**: `103.234.162.150:5013`
* **Packet Header**: `$NMP`
* **Security**: HMAC-SHA256 signature appended after `*` using the configured 16-byte ASCII key (default: `26bcb9e368440d4a`).

### 2. GPCB Profile
* **Endpoint**: `103.234.162.31:9999`
* **Packet Header**: `$NMP`
* **Security**: Unsigned CSV packet without HMAC trailer.
* **Transport**: Ultra-fast auto-reconnect (0.5s timeout, 0.1s retry) to handle frequent server disconnects.

### 3. VLTD (Parivahan Common Layer) Profile
* **Host**: `commonlayer.parivahan.gov.in`
* **Primary Port**: `9031` (for `$LGN`, `$HEL`, `$PVT`)
* **Emergency Port**: `9032` (for `$EPB,EMR`, `$EPB,SEM`)
* **Packets Implemented**:
  * `$LGN` – Login / Registration packet (`$LGN,{VREG},{IMEI},{FW},AIS140,{LAT:.7f},{LON:.7f},*`)
  * `$HEL` – Health diagnostic packet (`$HEL,{VENDOR},{FW},{IMEI},{BATT_PCT},{LOW_BATT},{MEM_ALERT},...`)
  * `$PVT` – Position, Velocity, and Time tracking (`$PVT,TRAXINA,4.0.27,NR,1,L,{IMEI},{VREG},...`)
  * `$EPB,EMR` – Emergency ON (Panic Button pressed)
  * `$EPB,SEM` – Emergency OFF (Panic Button cleared / Stop Emergency)

---

## Project Structure

```text
ais140-simulator/
├── main.py                 # Application entry point
├── run_simulator.bat       # Windows one-click launcher
├── .gitignore              # Git ignore rules
├── README.md               # Project documentation
└── src/
    ├── __init__.py
    ├── client.py           # Multi-threaded TCP client & dual-port dispatcher
    ├── packet.py           # CGM $NMP packet builder & HMAC signer
    ├── gpcb_packet.py      # GPCB $NMP packet builder
    ├── vltd_packet.py      # MoRTH/NIC VLTD packet builders ($LGN, $HEL, $PVT, $EPB)
    ├── rto_data.py         # 42 official RTO GPS coordinates (GJ, DD, DN)
    └── gui/
        ├── __init__.py
        ├── app.py          # Main application window & device notebook
        └── device_tab.py   # Individual device control tab & UI widgets
```

---

## Installation & Running

### Requirements
* Python 3.10 or newer (tested on Python 3.14).
* No pip dependencies required.

### Quick Start
Double-click `run_simulator.bat` or run from terminal:
```bash
python main.py
```

---

## License
MIT License
