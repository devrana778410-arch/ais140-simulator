# TCP client for a single device — runs in its own background thread
import socket
import threading
import time
from typing import Callable, Optional
from .vltd_packet import (
    build_login_packet,
    build_health_packet,
    build_pvt_packet,
    build_emergency_packet,
)


class DeviceClient:
    """
    Manages TCP connection + periodic packet sending for one simulated device.
    Robust against servers that drop idle TCP connections (e.g. Parivahan Common Layer).

    For VLTD profile:
      - Automatically sends $LGN (Login) and $HEL (Health) upon connect.
      - Periodic $PVT tracking stream.
      - Can auto-cycle Emergency ON ($EPB,EMR) and Emergency OFF ($EPB,SEM).
      - Thread-safe instant dispatch for any of the 5 individual packets.
    """

    def __init__(
        self,
        host: str,
        port: int,
        device_config: dict,
        packet_builder: Callable,
        on_log: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        connect_timeout: float = 10.0,
        retry_delay: float = 2.0,
        emergency_port: Optional[int] = None,
    ):
        self.host            = host
        self.port            = port
        self.emergency_port  = emergency_port or device_config.get("emergency_port")
        self.config          = device_config
        self.packet_builder  = packet_builder
        self.on_log          = on_log    or (lambda msg: None)
        self.on_status       = on_status or (lambda status, count: None)
        self.connect_timeout = connect_timeout
        self.retry_delay     = retry_delay

        self._sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.packet_count = 0
        self._connect_attempt = 0
        self.emergency_mode: Optional[str] = None   # "EMR" when SOS is ON, None when normal
        self.auto_sos = bool(self.config.get("auto_sos", False))

    # ------------------------------------------------------------------ #
    #  Public API (safe to call from any thread)                          #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self.packet_count = 0
            self._connect_attempt = 0
            self.emergency_mode = None
            self.auto_sos = bool(self.config.get("auto_sos", False))
            name = f"AIS-{str(self.config.get('imei', '?'))[-6:]}"
            self._thread = threading.Thread(target=self._run, daemon=True, name=name)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self.emergency_mode = None
        self._close_socket()

    def update_config(self, new_config: dict) -> None:
        """Hot-update config — takes effect on the next packet send."""
        with self._lock:
            self.config.update(new_config)
            self.auto_sos = bool(self.config.get("auto_sos", False))

    def set_emergency(self, mode: Optional[str]) -> None:
        """Set or clear emergency mode ('EMR' for active SOS, None for normal)."""
        with self._lock:
            self.emergency_mode = mode

    def send_packet_type(self, ptype: str) -> bool:
        """
        Build and send any of the 5 VLTD packets individually.
        Automatically routes:
          - $LGN, $HEL, $PVT to Primary Port (9031)
          - $EPB,EMR and $EPB,SEM to Emergency Port (9032)
        Works whether the simulation loop is currently running or stopped.
        """
        cfg = self.config.copy()
        cfg["seq_num"] = self.packet_count + 1

        target_port = self.port
        if ptype in ("EMR", "SEM") and self.emergency_port:
            target_port = self.emergency_port

        if ptype == "LGN":
            pkt = build_login_packet(**cfg)
            lbl = "1/5 LGN (Login)"
        elif ptype == "HEL":
            pkt = build_health_packet(**cfg)
            lbl = "2/5 HEL (Health)"
        elif ptype == "PVT":
            pkt = build_pvt_packet(**cfg)
            lbl = "3/5 PVT (Position)"
        elif ptype == "EMR":
            pkt = build_emergency_packet(mode="EMR", **cfg)
            lbl = "4/5 SOS ON (EMR)"
        elif ptype == "SEM":
            pkt = build_emergency_packet(mode="SEM", **cfg)
            lbl = "5/5 SOS OFF (SEM)"
        else:
            return False

        return self.send_instant(pkt, label=lbl, port=target_port)

    def send_instant(self, packet: str, label: str = "INSTANT", port: Optional[int] = None) -> bool:
        """
        Thread-safe instant packet transmission.
        For VLTD (or explicit target port), connects cleanly per packet, eliminating
        TCP reset (WinError 10054) errors from servers that drop idle connections.
        For CGM/GPCB persistent streams, sends over existing socket or reconnects.
        """
        target_port = port or self.port
        is_vltd = (self.config.get("profile") == "VLTD")

        with self._lock:
            # For VLTD, or stopped state, or if target_port differs from self.port:
            if not self._running or is_vltd or (target_port != self.port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.connect_timeout)
                    sock.connect((self.host, target_port))
                    sock.sendall(packet.encode("utf-8"))
                    sock.close()
                    self.packet_count += 1
                    preview = packet[:80] + "..." if len(packet) > 80 else packet
                    self.on_log(f"TX [{label}] -> :{target_port}: {preview}")
                    cur_status = "Sending" if self._running else "Stopped"
                    self.on_status(cur_status, self.packet_count)
                    return True
                except Exception as exc:
                    self.on_log(f"Send [{label}] failed on :{target_port}: {exc}")
                    return False

            # If running in persistent socket mode (CGM / GPCB):
            if not self._ensure_connected():
                self.on_log(f"Send [{label}] failed: unable to connect to {self.host}:{self.port}")
                return False

            try:
                self._sock.sendall(packet.encode("utf-8"))
                self.packet_count += 1
                preview = packet[:80] + "..." if len(packet) > 80 else packet
                self.on_log(f"TX [{label}]: {preview}")
                self.on_status("Sending", self.packet_count)
                return True
            except Exception as exc:
                self.on_log(f"Send [{label}] retrying on fresh socket ({exc})...")
                self._close_socket()
                if self._ensure_connected():
                    try:
                        self._sock.sendall(packet.encode("utf-8"))
                        self.packet_count += 1
                        preview = packet[:80] + "..." if len(packet) > 80 else packet
                        self.on_log(f"TX [{label}]: {preview}")
                        self.on_status("Sending", self.packet_count)
                        return True
                    except Exception as e2:
                        self.on_log(f"Send [{label}] retry failed: {e2}")
                return False

    # ------------------------------------------------------------------ #
    #  Internal Connection & Send Helpers                                  #
    # ------------------------------------------------------------------ #

    def _close_socket(self) -> None:
        sock = self._sock
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
            self._sock = None

    def _is_socket_closed(self) -> bool:
        """Check if remote server has closed or reset the TCP connection."""
        if not self._sock:
            return True
        try:
            self._sock.setblocking(False)
            peek_data = self._sock.recv(1, socket.MSG_PEEK)
            self._sock.setblocking(True)
            if peek_data == b"":
                return True   # EOF from server
            return False
        except BlockingIOError:
            self._sock.setblocking(True)
            return False      # Socket is alive
        except Exception:
            return True

    def _ensure_connected(self) -> bool:
        """Check connection health; establish or reconnect if needed."""
        if self._sock and self._is_socket_closed():
            self._close_socket()

        if self._sock is None and self._running:
            try:
                self._connect_attempt += 1
                self.on_log(f"Connecting to {self.host}:{self.port} (attempt {self._connect_attempt})...")
                self.on_status("Connecting", self.packet_count)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.connect_timeout)
                sock.connect((self.host, self.port))
                sock.settimeout(None)
                self._sock = sock
                self.on_log(f"Connected to {self.host}:{self.port}")
                self.on_status("Connected", self.packet_count)
                self._connect_attempt = 0
                return True
            except Exception as exc:
                self.on_log(f"Connect failed (attempt {self._connect_attempt}): {exc}")
                self.on_status("Connecting", self.packet_count)
                return False

        return self._sock is not None

    def _run(self) -> None:
        is_vltd = (self.config.get("profile") == "VLTD")

        if is_vltd:
            self.on_status("Connected", self.packet_count)
            self.on_log(
                f"VLTD dual-port active: Primary={self.host}:{self.port} | "
                f"Emergency={self.host}:{self.emergency_port or 9032}"
            )
        else:
            # Initial connect for persistent socket profiles (CGM / GPCB)
            with self._lock:
                self._ensure_connected()

        cycle_count = 0

        while self._running:
            if not is_vltd:
                with self._lock:
                    connected = self._ensure_connected()
                if not connected:
                    self._interruptible_sleep(self.retry_delay)
                    continue

            cycle_count += 1

            if is_vltd:
                # Automatically transmit all 5 VLTD packets in sequence
                self.on_log(f"--- [Cycle #{cycle_count}] Pushing all 5 VLTD packets in sequence ---")
                for ptype in ("LGN", "HEL", "PVT", "EMR", "SEM"):
                    if not self._running:
                        break
                    self.send_packet_type(ptype)
                    time.sleep(0.7)
            else:
                # Persistent socket send for CGM / GPCB
                with self._lock:
                    try:
                        cfg = self.config.copy()
                        cfg["seq_num"] = self.packet_count + 1
                        if self.emergency_mode == "EMR":
                            packet = build_emergency_packet(mode="EMR", **cfg)
                            lbl = f"{self.packet_count + 1:04d} EMR"
                        else:
                            packet = self.packet_builder(**cfg)
                            lbl = f"{self.packet_count + 1:04d}"

                        self._sock.sendall(packet.encode("utf-8"))
                        self.packet_count += 1
                        preview = packet[:80] + "..." if len(packet) > 80 else packet
                        self.on_log(f"TX [{lbl}]: {preview}")
                        self.on_status("Sending", self.packet_count)
                    except Exception as exc:
                        self.on_log(f"Send notice ({exc}) - auto-reconnecting next interval")
                        self._close_socket()

                        self._sock.sendall(packet.encode("utf-8"))
                        self.packet_count += 1
                        preview = packet[:80] + "..." if len(packet) > 80 else packet
                        self.on_log(f"TX [{lbl}]: {preview}")
                        self.on_status("Sending", self.packet_count)
                    except Exception as exc:
                        self.on_log(f"Send notice ({exc}) - auto-reconnecting next interval")
                        self._close_socket()

            interval = max(1, int(self.config.get("interval", 10)))
            if not self._interruptible_sleep(interval):
                break

        self._close_socket()
        self.on_status("Stopped", self.packet_count)
        self.on_log("Stopped.")

    def _interruptible_sleep(self, seconds: int) -> bool:
        """Sleep seconds in 0.1s ticks. Returns False if stop() called."""
        for _ in range(int(seconds * 10)):
            if not self._running:
                return False
            time.sleep(0.1)
        return True
