# AIS-140 Multi-Profile Telematics Simulator (Desktop, Web & Android)

A complete suite for simulating **AIS-140 Vehicle Location Tracking Devices (VLTD)** across Desktop (Windows `.exe`), Web Application (browser & cloud), and Android Native Application (`.apk`).

Supports direct **WhatsApp & Google Maps location link extraction** (`https://maps.google.com/maps?q=21.86664%2C73.1830466...`), auto-matching coordinates to 42 Gujarat/UT RTOs, and transmitting telematics packets to government gateways.

---

## 🌟 Supported Profiles & Destinations

1. **VLTD (MoRTH / Parivahan National Common Layer)**:
   - **Host**: `commonlayer.parivahan.gov.in`
   - **Primary Port (`9031`)**: Streams `$LGN` (Login), `$HEL` (Health), and `$PVT` (Position tracking).
   - **Emergency Port (`9032`)**: Dispatches `$EPB,EMR` (Emergency ON) and `$EPB,SEM` (Emergency OFF).
   - **Auto-Sequence**: Clicking **START SIMULATOR** automatically fires all 5 packets in sequence: `1/5 LGN` → `2/5 HEL` → `3/5 PVT` → `4/5 EMR` → `5/5 SEM`.
2. **GPCB (Gujarat Pollution Control Board - Hazardous Waste)**:
   - **Host**: `103.234.162.31:9999`
   - Formatted `$NMP` stream with custom vehicle registration.
3. **CGM (Chemical & Hazardous Goods Movers - Gujarat)**:
   - **Host**: `103.234.162.150:5013`
   - HMAC-SHA256 authenticated telemetry.

---

## 🚀 1. Windows Desktop Application (`.exe`)

The Windows application is bundled into a standalone, portable executable configured specifically to prevent **Windows Defender** false positives:
- **No UPX Compression** (`--noupx`): UPX packing is the #1 heuristic flag; our build runs uncompressed.
- **Embedded Application Manifest**: Standard user execution level `asInvoker`.
- **PE Version Metadata**: Full copyright, product version `2.0.0.0`, and file description.

### Ready-to-Run Executables:
- **Single Portable Executable**: `dist\AIS140-Simulator-Portable.exe` (10.9 MB, run anywhere, no installation needed)
- **Folder Distribution**: `dist\AIS140-Simulator\AIS140-Simulator.exe`

### Location Link Support ("Open with" / Drag & Drop / CLI):
You can pass WhatsApp location links directly to the executable:
```bash
"dist\AIS140-Simulator-Portable.exe" "https://maps.google.com/maps?q=21.86664%2C73.1830466&z=17&hl=en"
```
Or paste the link directly into the top **📍 Location Link** bar and click **[＋ Add Device]** or **[⚡ Apply to Active]**.

---

## 🌐 2. Web Application & Cloud Telematics Bridge

The Web App allows any desktop or mobile browser (including Android phones) to simulate telematics devices and send raw TCP packets through the backend gateway.

### Run Locally:
Double-click `run_web.bat` or run:
```bash
python web/server.py 8080
```
Then open: **`http://localhost:8080`**

### Direct URL Coordinate Opening:
Open links directly in browser to pre-populate coordinates and nearest RTO:
- `http://localhost:8080/?q=21.86664,73.1830466`
- `http://localhost:8080/?url=https://maps.google.com/maps?q=21.86664%2C73.1830466...`

### Cloud Deployment (Render / Railway / Docker):
Deploy with 1 click to [Render.com](https://render.com) using the included `web/render.yaml` or build the Docker image:
```bash
docker build -t ais140-web -f web/Dockerfile .
docker run -p 8080:8080 ais140-web
```

---

## 📱 3. Android Native Application (`.apk`)

Located in `C:\Users\PC\.gemini\antigravity\scratch\ais140-simulator\android\`.

### WhatsApp & Google Maps "Open with" Integration:
`AndroidManifest.xml` is registered with intent filters:
- `ACTION_VIEW` for `geo:` and `https://maps.google.com/...`
- `ACTION_SEND` with `mimeType="text/plain"` (allows selecting "AIS-140 Simulator" when sharing messages or locations from WhatsApp)
- `GeoLinkParser.kt` extracts coordinates automatically upon launch.

### Play Protect & Android Safety:
- Targets modern SDK (SDK 34).
- Clean permission footprint (`INTERNET`, `FOREGROUND_SERVICE`, `POST_NOTIFICATIONS`).
- Foreground service with notification keeps the TCP transmission alive in background without being killed by Android battery optimization.

---

## 🗺️ Google-Style RTO Autocomplete

Typing in the RTO field provides instant live recommendations:
- Typing `bh` instantly suggests **GJ-16 – Bharuch**, **GJ-04 – Bhavnagar**, and **GJ-12 – Bhuj**.
- Selecting an RTO automatically updates the GPS target coordinates and distance.

---

## 📁 Repository Layout

```text
ais140-simulator/
├── dist/
│   ├── AIS140-Simulator-Portable.exe    # Standalone Windows Desktop App
│   └── AIS140-Simulator/                # Folder distribution
├── web/
│   ├── index.html                       # Responsive Web Dashboard
│   ├── style.css                        # Modern Dark Aesthetic
│   ├── app.js                           # Web Client & RTO Autocomplete
│   ├── server.py                        # HTTP + SSE + TCP Telematics Bridge
│   ├── Dockerfile                       # Cloud container definition
│   └── render.yaml                      # 1-Click Render.com deployment
├── android/                             # Native Android Kotlin App
│   ├── app/src/main/AndroidManifest.xml # "Open with" & WhatsApp Intent Filters
│   ├── app/src/main/java/.../GeoLinkParser.kt # WhatsApp link coordinate parser
│   ├── app/src/main/java/.../MainActivity.kt  # Android UI & link handler
│   └── app/src/main/java/.../SimulatorService.kt # Foreground TCP service
├── src/
│   ├── geo_link.py                      # WhatsApp / Google Maps link parser
│   ├── rto_data.py                      # 42 Gujarat RTOs & Haversine calculator
│   ├── client.py                        # TCP client & 5-packet auto-sequence
│   ├── vltd_packet.py                   # Parivahan VLTD packet builders
│   ├── gpcb_packet.py                   # GPCB Hazardous packet builders
│   ├── packet.py                        # CGM packet builders & HMAC signer
│   └── gui/
│       ├── app.py                       # Modern Sidebar + Viewport GUI
│       ├── device_tab.py                # Per-device controls & logs
│       └── autocomplete.py              # Google-style RTO search widget
├── main.py                              # Desktop entry point
├── run_simulator.bat                    # One-click desktop launcher
├── run_web.bat                          # One-click web app launcher
└── README.md
```
