# AIS-140 Web Application Server & TCP Telematics Socket Bridge
# Python stdlib HTTP + SSE Server (Zero External Dependencies)
import os
import sys
import json
import time
import socket
import threading
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.geo_link import extract_coordinates, find_nearest_rto
from src.rto_data import RTO_TABLE, search_rto, code_from_display
from src.packet import build_packet as build_cgm_packet
from src.gpcb_packet import build_packet as build_gpcb_packet
from src.vltd_packet import build_packet as build_vltd_packet
from src.psdn_packet import build_packet as build_psdn_packet
from src.client import DeviceClient

START_TIME = time.time()

PACKET_BUILDERS = {
    "VLTD":        build_vltd_packet,
    "CGM":         build_cgm_packet,
    "GPCB":        build_gpcb_packet,
    "PSDN":        build_psdn_packet,
    "GPCB (PSDN)": build_psdn_packet,
}

PROFILE_SERVERS = {
    "CGM":         {"host": "103.234.162.150", "port": 5013,  "connect_timeout": 10, "retry_delay": 5},
    "GPCB":        {"host": "103.234.162.31",  "port": 9999,  "connect_timeout": 0.5, "retry_delay": 0.1},
    "PSDN":        {"host": "43.205.159.137",  "port": 17003, "connect_timeout": 10, "retry_delay": 5},
    "GPCB (PSDN)": {"host": "43.205.159.137",  "port": 17003, "connect_timeout": 10, "retry_delay": 5},
    "VLTD": {
        "host": "commonlayer.parivahan.gov.in",
        "port": 9031,
        "emergency_port": 9032,
        "connect_timeout": 10,
        "retry_delay": 2,
    },
}

class TelematicsBridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients = {}  # device_id -> DeviceClient
        self.device_states = {}  # device_id -> {status, count, logs: []}
        self.event_subscribers = []  # list of queue/callbacks for SSE

    def subscribe(self, callback):
        with self.lock:
            self.event_subscribers.append(callback)

    def unsubscribe(self, callback):
        with self.lock:
            if callback in self.event_subscribers:
                self.event_subscribers.remove(callback)

    def broadcast(self, event_type, data):
        payload = json.dumps({"event": event_type, "data": data})
        with self.lock:
            subscribers = list(self.event_subscribers)
        for sub in subscribers:
            try:
                sub(payload)
            except Exception:
                pass

    def log(self, dev_id, msg):
        entry = {"time": time.strftime("%H:%M:%S"), "dev_id": dev_id, "msg": msg}
        with self.lock:
            st = self.device_states.setdefault(dev_id, {"status": "Stopped", "count": 0, "logs": []})
            st["logs"].append(entry)
            if len(st["logs"]) > 200:
                st["logs"].pop(0)
        self.broadcast("log", entry)

    def status(self, dev_id, status_str, count):
        with self.lock:
            st = self.device_states.setdefault(dev_id, {"status": "Stopped", "count": 0, "logs": []})
            st["status"] = status_str
            st["count"] = count
        self.broadcast("status", {"dev_id": dev_id, "status": status_str, "count": count})

    def start_device(self, dev_id, config):
        self.stop_device(dev_id)
        profile = config.get("profile", "VLTD")
        srv = PROFILE_SERVERS.get(profile, PROFILE_SERVERS["VLTD"])
        builder = PACKET_BUILDERS.get(profile, build_vltd_packet)

        client = DeviceClient(
            host=srv["host"],
            port=srv["port"],
            device_config=config,
            packet_builder=builder,
            on_log=lambda msg, d=dev_id: self.log(d, msg),
            on_status=lambda st, cnt, d=dev_id: self.status(d, st, cnt),
            connect_timeout=srv.get("connect_timeout", 10),
            retry_delay=srv.get("retry_delay", 2),
            emergency_port=srv.get("emergency_port"),
        )
        with self.lock:
            self.clients[dev_id] = client
        client.start()
        return True

    def stop_device(self, dev_id):
        with self.lock:
            client = self.clients.pop(dev_id, None)
        if client:
            client.stop()
            self.status(dev_id, "Stopped", self.device_states.get(dev_id, {}).get("count", 0))

    def send_single(self, dev_id, config, ptype):
        with self.lock:
            client = self.clients.get(dev_id)
        if not client:
            profile = config.get("profile", "VLTD")
            srv = PROFILE_SERVERS.get(profile, PROFILE_SERVERS["VLTD"])
            builder = PACKET_BUILDERS.get(profile, build_vltd_packet)
            client = DeviceClient(
                host=srv["host"],
                port=srv["port"],
                device_config=config,
                packet_builder=builder,
                on_log=lambda msg, d=dev_id: self.log(d, msg),
                on_status=lambda st, cnt, d=dev_id: self.status(d, st, cnt),
                connect_timeout=srv.get("connect_timeout", 10),
                retry_delay=srv.get("retry_delay", 2),
                emergency_port=srv.get("emergency_port"),
            )
            with self.lock:
                self.clients[dev_id] = client
        else:
            client.update_config(config)
        client.send_packet_type(ptype)

    def trigger_sos(self, dev_id, config, mode):
        with self.lock:
            client = self.clients.get(dev_id)
        if client:
            client.set_emergency(mode if mode == "EMR" else None)
            client.send_packet_type("EMR" if mode == "EMR" else "SEM")

BRIDGE = TelematicsBridge()

class AIS140WebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            q = []
            ev_lock = threading.Condition()

            def on_msg(payload):
                with ev_lock:
                    q.append(payload)
                    ev_lock.notify()

            BRIDGE.subscribe(on_msg)
            try:
                # Send initial state
                initial = json.dumps({"event": "init", "data": {"states": BRIDGE.device_states, "rtos": RTO_TABLE}})
                self.wfile.write(f"data: {initial}\n\n".encode("utf-8"))
                self.wfile.flush()

                while True:
                    with ev_lock:
                        while not q:
                            ev_lock.wait(timeout=1.0)
                            if not q:
                                # Keep-alive ping
                                self.wfile.write(b": ping\n\n")
                                self.wfile.flush()
                        while q:
                            msg = q.pop(0)
                            self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                            self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                BRIDGE.unsubscribe(on_msg)
            return

        elif path == "/api/health":
            self._send_json({
                "status": "healthy",
                "service": "ais140-simulator",
                "uptime_seconds": round(time.time() - START_TIME, 1)
            })
            return

        elif path == "/api/rto_search":
            qs = urllib.parse.parse_qs(parsed.query)
            query = qs.get("q", [""])[0]
            display_matches = search_rto(query)
            results = []
            for item_str in display_matches[:12]:
                code = code_from_display(item_str)
                if code in RTO_TABLE:
                    info = RTO_TABLE[code]
                    results.append({
                        "code": code,
                        "name": info["name"],
                        "lat": info["lat"],
                        "lon": info["lon"]
                    })
            self._send_json({"matches": results})
            return

        elif path == "/api/extract_location":
            qs = urllib.parse.parse_qs(parsed.query)
            raw = qs.get("url", [""])[0]
            coords = extract_coordinates(raw)
            if coords:
                lat, lon = coords
                best_code, name, dist = find_nearest_rto(lat, lon)
                self._send_json({
                    "success": True,
                    "lat": lat,
                    "lon": lon,
                    "rto_code": best_code,
                    "rto_name": name,
                    "distance_km": round(dist, 1)
                })
            else:
                self._send_json({"success": False, "error": "Could not parse coordinates from link"})
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        data = json.loads(body) if body else {}

        if path == "/api/start":
            dev_id = data.get("device_id", 1)
            config = data.get("config", {})
            BRIDGE.start_device(dev_id, config)
            self._send_json({"status": "started"})
            return

        elif path == "/api/stop":
            dev_id = data.get("device_id", 1)
            BRIDGE.stop_device(dev_id)
            self._send_json({"status": "stopped"})
            return

        elif path == "/api/push":
            dev_id = data.get("device_id", 1)
            config = data.get("config", {})
            ptype = data.get("packet_type", "PVT")
            BRIDGE.send_single(dev_id, config, ptype)
            self._send_json({"status": "pushed", "packet_type": ptype})
            return

        elif path == "/api/sos":
            dev_id = data.get("device_id", 1)
            config = data.get("config", {})
            mode = data.get("mode", "EMR")
            BRIDGE.trigger_sos(dev_id, config, mode)
            self._send_json({"status": "sos_updated", "mode": mode})
            return

        self.send_error(404, "Unknown API endpoint")

    def _send_json(self, obj):
        res = json.dumps(obj).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(res)
        except (BrokenPipeError, ConnectionResetError):
            pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a separate thread so SSE never blocks API calls."""
    daemon_threads = True


def run(port=8080):
    host = "0.0.0.0"
    server = ThreadedHTTPServer((host, port), AIS140WebHandler)
    print("=" * 60)
    print(f"🛰️ AIS-140 Web App & Socket Bridge running at:")
    print(f"   Local:   http://localhost:{port}")
    print(f"   Network: http://{socket.gethostbyname(socket.gethostname())}:{port}")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        server.server_close()

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8080))
    run(p)
