# Per-device tab panel — supports CGM, GPCB and VLTD profiles
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from ..rto_data import get_rto_display_list, get_rto_coords, code_from_display


STATUS_COLORS = {
    "Stopped":      "#888888",
    "Connecting":   "#f39c12",
    "Connected":    "#27ae60",
    "Sending":      "#2980b9",
    "Error":        "#e74c3c",
    "Disconnected": "#e74c3c",
}

PROFILES = ["CGM", "GPCB", "VLTD"]

# Server presets per profile
PROFILE_SERVER = {
    "CGM":  {"host": "103.234.162.150", "port": 5013, "connect_timeout": 10, "retry_delay": 5},
    "GPCB": {"host": "103.234.162.31",  "port": 9999, "connect_timeout": 0.5, "retry_delay": 0.1},
    "VLTD": {
        "host": "commonlayer.parivahan.gov.in",
        "port": 9031,             # Primary Port: $LGN, $HEL, $PVT
        "emergency_port": 9032,   # Emergency Port: $EPB,EMR / $EPB,SEM
        "connect_timeout": 10,
        "retry_delay": 2,
    },
}


class DeviceTab(ttk.Frame):
    """
    One tab in the notebook — represents one simulated device.

    Profile field visibility:
      CGM  → IMEI, Lat, Lon, Interval          (N/E hardcoded, no vreg shown)
      GPCB → IMEI, Vehicle Reg, Lat, Lon, Int  (N/E hardcoded)
      VLTD → IMEI, RTO dropdown, Interval      (lat/lon auto-filled from table,
                                                manual push buttons for all 5 packets,
                                                auto-emergency ON/OFF option)

    Calls on_start(cfg) / on_stop() / on_sos(mode) / on_push_single(ptype).
    """

    def __init__(self, parent, device_num: int,
                 on_start: Callable, on_stop: Callable,
                 on_remove: Callable,
                 on_sos: Optional[Callable] = None,
                 on_push_single: Optional[Callable] = None,
                 **kwargs):
        super().__init__(parent, **kwargs)
        self._dev_num        = device_num
        self._on_start       = on_start
        self._on_stop        = on_stop
        self._on_remove      = on_remove
        self._on_sos         = on_sos
        self._on_push_single = on_push_single
        self._running        = False
        self._rto_list       = get_rto_display_list()

        self._build_ui(device_num)

    # ------------------------------------------------------------------ #
    #  UI Construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self, num: int) -> None:
        self.columnconfigure(1, weight=1)
        pad = {"padx": 6, "pady": 3}

        # --- Row 0: Profile selector ---
        ttk.Label(self, text="Profile:").grid(row=0, column=0, sticky="w", **pad)
        self._profile_var = tk.StringVar(value="CGM")
        profile_cb = ttk.Combobox(
            self, textvariable=self._profile_var,
            values=PROFILES, state="readonly", width=8
        )
        profile_cb.grid(row=0, column=1, sticky="w", **pad)
        profile_cb.bind("<<ComboboxSelected>>", self._on_profile_change)

        # --- Row 1: IMEI ---
        ttk.Label(self, text="IMEI:").grid(row=1, column=0, sticky="w", **pad)
        self._imei = ttk.Entry(self, width=20)
        self._imei.insert(0, "866224083766096")
        self._imei.grid(row=1, column=1, sticky="ew", **pad)

        # --- Row 2: Vehicle Reg (CGM hidden, GPCB visible) ---
        self._vreg_label = ttk.Label(self, text="Vehicle Reg:")
        self._vreg_label.grid(row=2, column=0, sticky="w", **pad)
        self._vreg = ttk.Entry(self, width=16)
        self._vreg.insert(0, "GJ01AC0000")
        self._vreg.grid(row=2, column=1, sticky="ew", **pad)

        # --- Row 3: RTO dropdown (VLTD only) ---
        self._rto_label = ttk.Label(self, text="RTO:")
        self._rto_label.grid(row=3, column=0, sticky="w", **pad)
        rto_container = ttk.Frame(self)
        rto_container.grid(row=3, column=1, sticky="ew", **pad)
        rto_container.columnconfigure(0, weight=1)

        self._rto_var = tk.StringVar()
        self._rto_cb = ttk.Combobox(
            rto_container, textvariable=self._rto_var,
            values=self._rto_list, state="readonly", width=28
        )
        if self._rto_list:
            self._rto_cb.set(self._rto_list[0])
        self._rto_cb.grid(row=0, column=0, sticky="ew")
        self._rto_cb.bind("<<ComboboxSelected>>", self._on_rto_change)

        self._rto_coord_lbl = ttk.Label(
            rto_container, text="", font=("Consolas", 8), foreground="#555555"
        )
        self._rto_coord_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self._update_rto_preview()

        # --- Row 4: Latitude ---
        self._lat_label = ttk.Label(self, text="Latitude:")
        self._lat_label.grid(row=4, column=0, sticky="w", **pad)
        lat_frame = ttk.Frame(self)
        lat_frame.grid(row=4, column=1, sticky="ew", **pad)
        self._lat = ttk.Entry(lat_frame, width=12)
        self._lat.insert(0, "21.749826")
        self._lat.pack(side="left")
        ttk.Label(lat_frame, text="N").pack(side="left", padx=(4, 0))

        # --- Row 5: Longitude ---
        self._lon_label = ttk.Label(self, text="Longitude:")
        self._lon_label.grid(row=5, column=0, sticky="w", **pad)
        lon_frame = ttk.Frame(self)
        lon_frame.grid(row=5, column=1, sticky="ew", **pad)
        self._lon = ttk.Entry(lon_frame, width=12)
        self._lon.insert(0, "73.098231")
        self._lon.pack(side="left")
        ttk.Label(lon_frame, text="E").pack(side="left", padx=(4, 0))

        # --- Row 6: Interval ---
        ttk.Label(self, text="Interval (s):").grid(row=6, column=0, sticky="w", **pad)
        self._interval = ttk.Spinbox(self, from_=1, to=3600, width=6)
        self._interval.delete(0, "end")
        self._interval.insert(0, "10")
        self._interval.grid(row=6, column=1, sticky="w", **pad)

        # --- Row 7: Auto SOS Option (VLTD only) ---
        self._auto_sos_var = tk.BooleanVar(value=True)
        self._auto_sos_cb = ttk.Checkbutton(
            self, text="Auto-push Emergency ON & OFF cycle during continuous run",
            variable=self._auto_sos_var
        )
        self._auto_sos_cb.grid(row=7, column=0, columnspan=2, sticky="w", padx=6, pady=2)

        # --- Row 8: Main Start/Stop/Remove buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(4, 2))

        self._start_btn = ttk.Button(btn_frame, text="▶  Start", command=self._on_start_click, width=11)
        self._start_btn.pack(side="left", padx=3)

        self._stop_btn = ttk.Button(btn_frame, text="■  Stop", command=self._on_stop_click,
                                    width=11, state="disabled")
        self._stop_btn.pack(side="left", padx=3)

        self._remove_btn = ttk.Button(btn_frame, text="✕ Remove", command=self._on_remove, width=9)
        self._remove_btn.pack(side="left", padx=3)

        # Live Emergency toggle buttons (active during run)
        self._sos_frame = ttk.Frame(btn_frame)
        self._sos_frame.pack(side="left", padx=(10, 0))

        self._sos_on_btn = tk.Button(
            self._sos_frame, text="🚨 SOS ON", bg="#c0392b", fg="white",
            activebackground="#e74c3c", activeforeground="white",
            font=("Segoe UI", 9, "bold"), width=10, relief="raised",
            command=lambda: self._trigger_sos("EMR"), state="disabled"
        )
        self._sos_on_btn.pack(side="left", padx=2)

        self._sos_off_btn = tk.Button(
            self._sos_frame, text="🛡️ SOS OFF", bg="#2980b9", fg="white",
            activebackground="#3498db", activeforeground="white",
            font=("Segoe UI", 9, "bold"), width=10, relief="raised",
            command=lambda: self._trigger_sos("SEM"), state="disabled"
        )
        self._sos_off_btn.pack(side="left", padx=2)

        # --- Row 9: Manual Individual Packet Push Frame (VLTD only) ---
        self._manual_frame = ttk.LabelFrame(
            self, text="Push Individual Packet (Manual / On-Demand)  [9031: Primary | 9032: Emerg]"
        )
        self._manual_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 4))

        ttk.Button(
            self._manual_frame, text="🔑 Login ($LGN) :9031", width=20,
            command=lambda: self._on_manual_push("LGN")
        ).pack(side="left", padx=3, pady=4)

        ttk.Button(
            self._manual_frame, text="🩺 Health ($HEL) :9031", width=20,
            command=lambda: self._on_manual_push("HEL")
        ).pack(side="left", padx=3, pady=4)

        ttk.Button(
            self._manual_frame, text="📍 Position ($PVT) :9031", width=21,
            command=lambda: self._on_manual_push("PVT")
        ).pack(side="left", padx=3, pady=4)

        tk.Button(
            self._manual_frame, text="🚨 Emerg. ON :9032", bg="#c0392b", fg="white",
            activebackground="#e74c3c", activeforeground="white",
            font=("Segoe UI", 8, "bold"), width=16, relief="raised",
            command=lambda: self._on_manual_push("EMR")
        ).pack(side="left", padx=3, pady=4)

        tk.Button(
            self._manual_frame, text="🛡️ Emerg. OFF :9032", bg="#2980b9", fg="white",
            activebackground="#3498db", activeforeground="white",
            font=("Segoe UI", 8, "bold"), width=16, relief="raised",
            command=lambda: self._on_manual_push("SEM")
        ).pack(side="left", padx=3, pady=4)

        # --- Row 10: Status bar ---
        status_frame = ttk.Frame(self)
        status_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=6)

        ttk.Label(status_frame, text="Status:").pack(side="left")
        self._status_dot = tk.Label(status_frame, text="●", fg="#888888",
                                    bg=self.winfo_toplevel().cget("bg"))
        self._status_dot.pack(side="left", padx=(2, 0))
        self._status_lbl = ttk.Label(status_frame, text="Stopped")
        self._status_lbl.pack(side="left", padx=(2, 10))

        ttk.Label(status_frame, text="Packets:").pack(side="left")
        self._count_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self._count_var, width=6).pack(side="left")

        # --- Row 11: Mini log ---
        log_frame = ttk.LabelFrame(self, text="Device Log")
        log_frame.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=6, pady=(4, 6))
        self.rowconfigure(11, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=8, wrap="none",
                            font=("Consolas", 8), state="disabled",
                            bg="#1e1e1e", fg="#d4d4d4")
        self._log.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self._log.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._log["yscrollcommand"] = vsb.set

        hsb = ttk.Scrollbar(log_frame, orient="horizontal", command=self._log.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self._log["xscrollcommand"] = hsb.set

        # Apply initial profile visibility
        self._apply_profile_visibility("CGM")

    # ------------------------------------------------------------------ #
    #  Profile & RTO switching                                             #
    # ------------------------------------------------------------------ #

    def _on_profile_change(self, event=None) -> None:
        profile = self._profile_var.get()
        self._apply_profile_visibility(profile)

    def _on_rto_change(self, event=None) -> None:
        self._update_rto_preview()

    def _update_rto_preview(self) -> None:
        rto_display = self._rto_var.get()
        if rto_display:
            code = code_from_display(rto_display)
            lat, lon = get_rto_coords(code)
            self._rto_coord_lbl.config(text=f"Coordinates: {lat:.6f}°N, {lon:.6f}°E")

    def _apply_profile_visibility(self, profile: str) -> None:
        """Show/hide rows based on selected profile."""
        if profile == "CGM":
            self._vreg_label.grid_remove()
            self._vreg.grid_remove()
            self._rto_label.grid_remove()
            self._rto_cb.master.grid_remove()
            self._lat_label.grid()
            self._lat.master.grid()
            self._lon_label.grid()
            self._lon.master.grid()
            self._auto_sos_cb.grid_remove()
            self._sos_frame.pack_forget()
            self._manual_frame.grid_remove()

        elif profile == "GPCB":
            self._vreg_label.grid()
            self._vreg.grid()
            self._rto_label.grid_remove()
            self._rto_cb.master.grid_remove()
            self._lat_label.grid()
            self._lat.master.grid()
            self._lon_label.grid()
            self._lon.master.grid()
            self._auto_sos_cb.grid_remove()
            self._sos_frame.pack_forget()
            self._manual_frame.grid_remove()

        elif profile == "VLTD":
            self._vreg_label.grid_remove()
            self._vreg.grid_remove()
            self._rto_label.grid()
            self._rto_cb.master.grid()
            self._lat_label.grid_remove()
            self._lat.master.grid_remove()
            self._lon_label.grid_remove()
            self._lon.master.grid_remove()
            self._auto_sos_cb.grid()
            self._sos_frame.pack(side="left", padx=(10, 0))
            self._manual_frame.grid()
            if self._running:
                self._sos_on_btn.config(state="normal")
                self._sos_off_btn.config(state="normal")
            else:
                self._sos_on_btn.config(state="disabled")
                self._sos_off_btn.config(state="disabled")

    # ------------------------------------------------------------------ #
    #  Button handlers                                                     #
    # ------------------------------------------------------------------ #

    def _on_start_click(self) -> None:
        cfg = self._collect_config()
        if cfg is None:
            return
        self._running = True
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_fields_state("disabled")
        if self._profile_var.get() == "VLTD":
            self._sos_on_btn.config(state="normal")
            self._sos_off_btn.config(state="normal")
        self._on_start(cfg)

    def _on_stop_click(self) -> None:
        self._running = False
        self._stop_btn.config(state="disabled")
        self._sos_on_btn.config(state="disabled")
        self._sos_off_btn.config(state="disabled")
        self._on_stop()

    def _trigger_sos(self, mode: str) -> None:
        if not self._running:
            return
        cfg = self._collect_config()
        if cfg and self._on_sos:
            if mode == "EMR":
                self._sos_on_btn.config(relief="sunken", text="🚨 ACTIVE")
                self._sos_off_btn.config(relief="raised", text="🛡️ SOS OFF")
            else:
                self._sos_on_btn.config(relief="raised", text="🚨 SOS ON")
                self._sos_off_btn.config(relief="raised", text="🛡️ CLEARED")
                self.after(2000, lambda: self._sos_off_btn.config(text="🛡️ SOS OFF"))
            self._on_sos(self._dev_num, cfg, mode)

    def _on_manual_push(self, ptype: str) -> None:
        """Called when user clicks any of the 5 manual packet push buttons."""
        cfg = self._collect_config()
        if cfg and self._on_push_single:
            self._on_push_single(self._dev_num, cfg, ptype)

    def _collect_config(self) -> dict | None:
        profile = self._profile_var.get()

        imei = self._imei.get().strip()
        if not imei or not imei.isdigit() or len(imei) < 10:
            messagebox.showerror("Invalid Input", "IMEI must be a numeric string (10-15 digits).")
            return None

        if profile == "VLTD":
            rto_display = self._rto_var.get()
            if not rto_display:
                messagebox.showerror("Invalid Input", "Please select an RTO.")
                return None
            rto_code = code_from_display(rto_display)
            lat, lon = get_rto_coords(rto_code)
            vreg = "GJ01AC0000"   # default for VLTD
        else:
            try:
                lat = float(self._lat.get().strip())
                lon = float(self._lon.get().strip())
            except ValueError:
                messagebox.showerror("Invalid Input", "Latitude and Longitude must be decimal numbers.")
                return None
            vreg = self._vreg.get().strip() if profile == "GPCB" else "GJ01AC0000"
            rto_code = None

        try:
            interval = max(1, int(self._interval.get()))
        except ValueError:
            interval = 10

        return {
            "profile":        profile,
            "imei":           imei,
            "vreg":           vreg,
            "lat":            lat,
            "lat_h":          "N",
            "lon":            lon,
            "lon_h":          "E",
            "interval":       interval,
            "rto":            rto_code,
            "auto_sos":       self._auto_sos_var.get(),
            "emergency_port": PROFILE_SERVER.get(profile, {}).get("emergency_port"),
        }

    def _set_fields_state(self, state: str) -> None:
        profile = self._profile_var.get()
        for w in (self._imei, self._interval):
            w.config(state=state)
        if profile == "GPCB":
            self._vreg.config(state=state)
        if profile in ("CGM", "GPCB"):
            self._lat.config(state=state)
            self._lon.config(state=state)
        if profile == "VLTD":
            self._rto_cb.config(state="disabled" if state == "disabled" else "readonly")
            self._auto_sos_cb.config(state=state)

    def get_profile(self) -> str:
        return self._profile_var.get()

    # ------------------------------------------------------------------ #
    #  Public update methods (called via root.after from worker thread)   #
    # ------------------------------------------------------------------ #

    def set_status(self, status: str, count: int) -> None:
        color = STATUS_COLORS.get(status, "#888888")
        self._status_dot.config(fg=color)
        self._status_lbl.config(text=status)
        self._count_var.set(str(count))

        if status == "Stopped":
            self._start_btn.config(state="normal")
            self._stop_btn.config(state="disabled")
            self._sos_on_btn.config(state="disabled", relief="raised", text="🚨 SOS ON")
            self._sos_off_btn.config(state="disabled", relief="raised", text="🛡️ SOS OFF")
            self._set_fields_state("normal")

    def append_log(self, msg: str) -> None:
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.config(state="normal")
        self._log.insert("end", f"[{ts}] {msg}\n")
        self._log.see("end")
        self._log.config(state="disabled")

    def clear_log(self) -> None:
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")
