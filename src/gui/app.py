# Main application window
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
from .device_tab import DeviceTab, PROFILE_SERVER
from ..client import DeviceClient
from ..packet import build_packet as build_cgm_packet
from ..gpcb_packet import build_packet as build_gpcb_packet
from ..vltd_packet import (
    build_packet as build_vltd_packet,
    build_emergency_packet,
)


# Profile -> periodic packet builder function
PACKET_BUILDERS = {
    "CGM":  build_cgm_packet,
    "GPCB": build_gpcb_packet,
    "VLTD": build_vltd_packet,
}

CGM_HMAC_KEY   = "26bcb9e368440d4a"
CGM_HMAC_BYTES = CGM_HMAC_KEY.encode("ascii")


class SimulatorApp:
    """
    Main AIS-140 Simulator window.
    Supports multiple simultaneous device tabs (CGM / GPCB / VLTD),
    each with its own TCP connection and packet builder.
    """

    APP_TITLE   = "AIS-140 Simulator"
    APP_VERSION = "v1.2"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{self.APP_TITLE}  {self.APP_VERSION}")
        self.root.minsize(860, 680)
        self.root.resizable(True, True)

        # device_id -> (DeviceTab, DeviceClient | None)
        self._devices: dict[int, tuple] = {}
        self._next_id = 1

        self._build_ui()
        self._add_device()   # start with one device tab

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    #  UI Construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=3)
        self.root.rowconfigure(3, weight=1)

        # ---- Top: info bar ----
        info_frame = ttk.LabelFrame(self.root, text="AIS-140 Multi-Profile Simulator")
        info_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        info_frame.columnconfigure(0, weight=1)

        ttk.Label(
            info_frame,
            text="CGM: 103.234.162.150:5013  |  GPCB: 103.234.162.31:9999  |  VLTD: commonlayer.parivahan.gov.in (Primary: 9031, Emerg: 9032)",
            font=("Consolas", 8),
            foreground="#444444",
        ).grid(row=0, column=0, padx=8, pady=4, sticky="w")

        # CGM HMAC key
        key_frame = ttk.Frame(info_frame)
        key_frame.grid(row=0, column=1, padx=(6, 8), pady=4, sticky="e")
        ttk.Label(key_frame, text="CGM HMAC:").pack(side="left", padx=(0, 2))
        self._hmac_var = tk.StringVar(value=CGM_HMAC_KEY)
        self._hmac_entry = ttk.Entry(key_frame, textvariable=self._hmac_var, width=18, show="*")
        self._hmac_entry.pack(side="left", padx=2)
        self._show_key = False
        ttk.Button(key_frame, text="Show", width=5,
                   command=self._toggle_key_visibility).pack(side="left", padx=2)

        # ---- Device toolbar ----
        toolbar = ttk.Frame(self.root)
        toolbar.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 0))

        ttk.Button(toolbar, text="＋ Add Device", command=self._add_device, width=14).pack(side="left", padx=(0, 4))
        ttk.Button(toolbar, text="▶▶ Start All",  command=self._start_all,  width=14).pack(side="left", padx=4)
        ttk.Button(toolbar, text="■■ Stop All",   command=self._stop_all,   width=14).pack(side="left", padx=4)

        # ---- Device notebook ----
        self._notebook = ttk.Notebook(self.root)
        self._notebook.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)

        # ---- Master log ----
        log_frame = ttk.LabelFrame(self.root, text="Master Log")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 4))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._master_log = tk.Text(log_frame, height=7, wrap="none",
                                   font=("Consolas", 8), state="disabled",
                                   bg="#111111", fg="#cccccc")
        self._master_log.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self._master_log.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._master_log["yscrollcommand"] = vsb.set

        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 2))
        ttk.Button(log_btn_frame, text="Clear",      command=self._clear_master_log, width=8).pack(side="left", padx=4)
        ttk.Button(log_btn_frame, text="Export Log", command=self._export_log,       width=10).pack(side="left", padx=4)

        # Status bar
        self._status_bar = ttk.Label(self.root, text="Ready", relief="sunken", anchor="w")
        self._status_bar.grid(row=4, column=0, sticky="ew", padx=0)

    # ------------------------------------------------------------------ #
    #  Device management                                                   #
    # ------------------------------------------------------------------ #

    def _add_device(self) -> None:
        dev_id = self._next_id
        self._next_id += 1

        tab = DeviceTab(
            self._notebook,
            device_num=dev_id,
            on_start=lambda cfg, did=dev_id: self._start_device(did, cfg),
            on_stop=lambda did=dev_id: self._stop_device(did),
            on_remove=lambda did=dev_id: self._remove_device(did),
            on_sos=lambda did, cfg, mode: self._handle_sos(did, cfg, mode),
            on_push_single=lambda did, cfg, ptype: self._handle_push_single(did, cfg, ptype),
        )
        self._notebook.add(tab, text=f"  Device {dev_id}  ")
        self._notebook.select(tab)
        self._devices[dev_id] = (tab, None)
        self._master_log_write(f"[SYS] Device {dev_id} added.")

    def _remove_device(self, dev_id: int) -> None:
        if dev_id not in self._devices:
            return
        tab, client = self._devices[dev_id]
        if client:
            client.stop()
        for idx in range(self._notebook.index("end")):
            if self._notebook.nametowidget(self._notebook.tabs()[idx]) is tab:
                self._notebook.forget(idx)
                break
        del self._devices[dev_id]
        self._master_log_write(f"[SYS] Device {dev_id} removed.")

    def _start_device(self, dev_id: int, cfg: dict) -> None:
        if dev_id not in self._devices:
            return

        profile = cfg.get("profile", "CGM")

        # Resolve server host/port for this profile
        srv = PROFILE_SERVER.get(profile, PROFILE_SERVER["CGM"])
        host = srv["host"]
        port = srv["port"]

        if not host:
            messagebox.showwarning("Not Implemented", f"{profile} server not configured.")
            tab, _ = self._devices[dev_id]
            tab.set_status("Stopped", 0)
            return

        # Resolve packet builder
        builder = PACKET_BUILDERS.get(profile)
        if builder is None:
            messagebox.showwarning("Not Implemented", f"{profile} packet builder not configured.")
            tab, _ = self._devices[dev_id]
            tab.set_status("Stopped", 0)
            return

        # For CGM, inject HMAC key from the UI field
        if profile == "CGM":
            try:
                cfg["hmac_key"] = self._hmac_var.get().strip().encode("ascii")
            except Exception:
                cfg["hmac_key"] = CGM_HMAC_BYTES

        tab, old_client = self._devices[dev_id]
        if old_client:
            old_client.stop()

        client = DeviceClient(
            host=host,
            port=port,
            device_config=cfg,
            packet_builder=builder,
            on_log=lambda msg, did=dev_id: self._device_log(did, msg),
            on_status=lambda status, count, did=dev_id: self._device_status(did, status, count),
            connect_timeout=srv.get("connect_timeout", 10),
            retry_delay=srv.get("retry_delay", 5),
            emergency_port=srv.get("emergency_port"),
        )
        self._devices[dev_id] = (tab, client)
        client.start()

        # Update tab title with profile + IMEI suffix
        imei_suffix = cfg.get("imei", "?")[-6:]
        label = f"  [{profile}] Dev {dev_id} …{imei_suffix}  "
        for idx in range(self._notebook.index("end")):
            if self._notebook.nametowidget(self._notebook.tabs()[idx]) is tab:
                self._notebook.tab(idx, text=label)
                break

        srv_desc = f"{host}:{port} (Emerg: {srv.get('emergency_port')})" if srv.get("emergency_port") else f"{host}:{port}"
        self._master_log_write(
            f"[SYS] Device {dev_id} started  profile={profile}  "
            f"IMEI={cfg.get('imei')}  server={srv_desc}"
        )

    def _handle_sos(self, dev_id: int, cfg: dict, mode: str) -> None:
        """Triggered when user clicks SOS ON (EMR) or SOS OFF (SEM) on a VLTD device."""
        if dev_id not in self._devices:
            return
        tab, client = self._devices[dev_id]
        if not client:
            return

        # Update emergency mode in client
        client.set_emergency(mode if mode == "EMR" else None)

        ptype = "EMR" if mode == "EMR" else "SEM"
        sent = client.send_packet_type(ptype)
        if sent:
            lbl = "SOS ON (EMR)" if mode == "EMR" else "SOS OFF (SEM)"
            self._master_log_write(f"[Dev{dev_id}] Dispatched {lbl} -> :{client.emergency_port or 9032}")

    def _handle_push_single(self, dev_id: int, cfg: dict, ptype: str) -> None:
        """Triggered when user clicks one of the manual packet push buttons."""
        if dev_id not in self._devices:
            return
        tab, client = self._devices[dev_id]

        profile = cfg.get("profile", "VLTD")
        srv = PROFILE_SERVER.get(profile, PROFILE_SERVER["VLTD"])
        host = srv["host"]
        port = srv["port"]
        emergency_port = srv.get("emergency_port")
        builder = PACKET_BUILDERS.get(profile, build_vltd_packet)

        if client is None:
            client = DeviceClient(
                host=host,
                port=port,
                device_config=cfg,
                packet_builder=builder,
                on_log=lambda msg, did=dev_id: self._device_log(did, msg),
                on_status=lambda status, count, did=dev_id: self._device_status(did, status, count),
                connect_timeout=srv.get("connect_timeout", 10),
                retry_delay=srv.get("retry_delay", 2),
                emergency_port=emergency_port,
            )
            self._devices[dev_id] = (tab, client)
        else:
            client.update_config(cfg)

        success = client.send_packet_type(ptype)
        if success:
            self._master_log_write(f"[Dev{dev_id}] Pushed manual packet: {ptype}")

    def _stop_device(self, dev_id: int) -> None:
        if dev_id not in self._devices:
            return
        _, client = self._devices[dev_id]
        if client:
            client.stop()
        self._master_log_write(f"[SYS] Device {dev_id} stopped.")

    def _start_all(self) -> None:
        for dev_id, (tab, _) in list(self._devices.items()):
            tab._on_start_click()

    def _stop_all(self) -> None:
        for dev_id in list(self._devices.keys()):
            self._stop_device(dev_id)
            entry = self._devices.get(dev_id)
            if entry:
                tab, _ = entry
                tab.set_status("Stopped", 0)

    # ------------------------------------------------------------------ #
    #  Callbacks from DeviceClient (worker thread -> GUI thread via after)#
    # ------------------------------------------------------------------ #

    def _device_log(self, dev_id: int, msg: str) -> None:
        def _update():
            if dev_id in self._devices:
                tab, _ = self._devices[dev_id]
                tab.append_log(msg)
            self._master_log_write(f"[Dev{dev_id}] {msg}")
        self.root.after(0, _update)

    def _device_status(self, dev_id: int, status: str, count: int) -> None:
        def _update():
            if dev_id in self._devices:
                tab, _ = self._devices[dev_id]
                tab.set_status(status, count)
            self._status_bar.config(text=f"Device {dev_id}: {status}  |  Packets: {count}")
        self.root.after(0, _update)

    # ------------------------------------------------------------------ #
    #  Master log helpers                                                  #
    # ------------------------------------------------------------------ #

    def _master_log_write(self, msg: str) -> None:
        def _update():
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._master_log.config(state="normal")
            self._master_log.insert("end", f"[{ts}] {msg}\n")
            self._master_log.see("end")
            self._master_log.config(state="disabled")
        self.root.after(0, _update)

    def _clear_master_log(self) -> None:
        self._master_log.config(state="normal")
        self._master_log.delete("1.0", "end")
        self._master_log.config(state="disabled")

    def _export_log(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"ais140_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if path:
            content = self._master_log.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Exported", f"Log saved to:\n{path}")

    # ------------------------------------------------------------------ #
    #  Misc                                                                #
    # ------------------------------------------------------------------ #

    def _toggle_key_visibility(self) -> None:
        self._show_key = not self._show_key
        self._hmac_entry.config(show="" if self._show_key else "*")

    def _on_close(self) -> None:
        self._stop_all()
        self.root.destroy()
