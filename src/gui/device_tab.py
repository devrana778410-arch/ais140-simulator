# Per-device panel — Clean, minimalist modern UI with toggleable Debug Drawer
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional
import datetime
from ..rto_data import (
    get_rto_display_list,
    get_rto_coords,
    code_from_display,
    search_rto,
    resolve_rto,
    RTO_TABLE,
)
from .styles import COLORS, FONTS
from .autocomplete import AutocompleteRTO
from ..geo_link import find_nearest_rto

PROFILES = ["VLTD", "CGM", "GPCB"]

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


class DeviceTab(tk.Frame):
    """
    Modern Device Panel.
    Clean minimalist view by default:
      - Profile picker
      - Minimal inputs (IMEI, RTO dropdown, Interval)
      - Hero Stat Card with large Packets Sent counter
      - High-visibility Start / Stop button
      - Emergency ON / OFF buttons (for VLTD)
    All technical diagnostic clutter (logs, raw ports, HMAC key, manual packet pushes)
    is tucked away inside a Debug Drawer, visible only when Debug Mode is enabled.
    """

    def __init__(
        self,
        parent,
        device_num: int,
        on_start: Callable,
        on_stop: Callable,
        on_remove: Callable,
        on_sos: Optional[Callable] = None,
        on_push_single: Optional[Callable] = None,
        on_profile_change_cb: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, bg=COLORS["bg_app"], **kwargs)
        self._dev_num              = device_num
        self._on_start             = on_start
        self._on_stop              = on_stop
        self._on_remove            = on_remove
        self._on_sos               = on_sos
        self._on_push_single       = on_push_single
        self._on_profile_change_cb = on_profile_change_cb
        self._running              = False
        self._debug_mode           = False
        self._rto_list             = get_rto_display_list()

        self._build_ui(device_num)

    # ------------------------------------------------------------------ #
    #  UI Construction                                                   #
    # ------------------------------------------------------------------ #

    def _build_ui(self, num: int) -> None:
        self.columnconfigure(0, weight=1)

        # ---------------- 1. Device Header Bar ---------------- #
        header_frame = tk.Frame(self, bg=COLORS["bg_app"])
        header_frame.pack(fill="x", padx=16, pady=(14, 10))

        title_box = tk.Frame(header_frame, bg=COLORS["bg_app"])
        title_box.pack(side="left")

        self._title_lbl = tk.Label(
            title_box, text=f"Device {num}", font=FONTS["brand_title"],
            fg=COLORS["text_primary"], bg=COLORS["bg_app"]
        )
        self._title_lbl.pack(anchor="w")

        self._subtitle_lbl = tk.Label(
            title_box, text="Vehicle Location Tracking Simulator",
            font=FONTS["caption"], fg=COLORS["text_secondary"], bg=COLORS["bg_app"]
        )
        self._subtitle_lbl.pack(anchor="w")

        # Right side: Profile switcher + Remove button
        actions_box = tk.Frame(header_frame, bg=COLORS["bg_app"])
        actions_box.pack(side="right")

        tk.Label(
            actions_box, text="Profile:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_app"]
        ).pack(side="left", padx=(0, 6))

        self._profile_var = tk.StringVar(value="VLTD")
        self._profile_cb = ttk.Combobox(
            actions_box, textvariable=self._profile_var,
            values=PROFILES, state="readonly", width=8, font=FONTS["body_bold"]
        )
        self._profile_cb.pack(side="left", padx=(0, 14))
        self._profile_cb.bind("<<ComboboxSelected>>", self._on_profile_change)

        self._remove_btn = tk.Button(
            actions_box, text="✕ Remove", font=FONTS["caption"],
            bg=COLORS["bg_card"], fg=COLORS["danger"], activebackground=COLORS["danger"],
            activeforeground="white", relief="flat", bd=0, padx=8, pady=4,
            cursor="hand2", command=self._on_remove
        )
        self._remove_btn.pack(side="left")

        # ---------------- 2. Hero Metric & Action Card ---------------- #
        hero_card = tk.Frame(
            self, bg=COLORS["bg_card"], highlightbackground=COLORS["border"],
            highlightthickness=1, padx=16, pady=14
        )
        hero_card.pack(fill="x", padx=16, pady=(0, 12))
        hero_card.columnconfigure(0, weight=1)
        hero_card.columnconfigure(1, weight=1)

        # Left: Live Status + Primary Start/Stop Button
        hero_left = tk.Frame(hero_card, bg=COLORS["bg_card"])
        hero_left.grid(row=0, column=0, sticky="w")

        status_row = tk.Frame(hero_left, bg=COLORS["bg_card"])
        status_row.pack(anchor="w", pady=(0, 8))

        self._status_dot = tk.Label(
            status_row, text="●", font=("Segoe UI", 12),
            fg=COLORS["stopped"], bg=COLORS["bg_card"]
        )
        self._status_dot.pack(side="left", padx=(0, 6))

        self._status_badge = tk.Label(
            status_row, text="STOPPED", font=FONTS["badge"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self._status_badge.pack(side="left")

        # Prominent Start / Stop Button
        self._start_stop_btn = tk.Button(
            hero_left, text="▶  START SIMULATOR", font=FONTS["btn_large"],
            bg=COLORS["success"], fg="#ffffff", activebackground=COLORS["success_hover"],
            activeforeground="#ffffff", relief="flat", bd=0, padx=22, pady=10,
            cursor="hand2", command=self._toggle_start_stop
        )
        self._start_stop_btn.pack(anchor="w")

        # Right: Large Packets Sent Counter
        hero_right = tk.Frame(hero_card, bg=COLORS["bg_card"])
        hero_right.grid(row=0, column=1, sticky="e")

        tk.Label(
            hero_right, text="PACKETS TRANSMITTED", font=FONTS["stat_lbl"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        ).pack(anchor="e")

        self._count_var = tk.StringVar(value="0")
        self._count_display = tk.Label(
            hero_right, textvariable=self._count_var, font=FONTS["stat_num"],
            fg=COLORS["text_primary"], bg=COLORS["bg_card"]
        )
        self._count_display.pack(anchor="e")

        # ---------------- 3. Configuration Inputs Card ---------------- #
        self._inputs_card = tk.Frame(
            self, bg=COLORS["bg_card"], highlightbackground=COLORS["border"],
            highlightthickness=1, padx=16, pady=14
        )
        self._inputs_card.pack(fill="x", padx=16, pady=(0, 12))
        self._inputs_card.columnconfigure(1, weight=1)

        # Field: IMEI
        tk.Label(
            self._inputs_card, text="IMEI Number:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        ).grid(row=0, column=0, sticky="w", pady=6)

        self._imei = tk.Entry(
            self._inputs_card, font=FONTS["input"], bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"],
            relief="flat", highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._imei.insert(0, "869833088601301")
        self._imei.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=6)

        # Field: Vehicle Registration (GPCB only)
        self._vreg_lbl = tk.Label(
            self._inputs_card, text="Vehicle Reg:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self._vreg = tk.Entry(
            self._inputs_card, font=FONTS["input"], bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"],
            relief="flat", highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._vreg.insert(0, "GJ01AC0000")

        # Field: RTO Location Dropdown (VLTD only)
        self._rto_lbl = tk.Label(
            self._inputs_card, text="RTO Location:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self._rto_lbl.grid(row=1, column=0, sticky="w", pady=6)

        self._rto_container = tk.Frame(self._inputs_card, bg=COLORS["bg_card"])
        self._rto_container.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=6)
        self._rto_container.columnconfigure(0, weight=1)

        self._rto_coord_lbl = tk.Label(
            self._rto_container, text="", font=FONTS["caption"],
            fg=COLORS["text_accent"], bg=COLORS["bg_card"]
        )
        self._rto_coord_lbl.grid(row=1, column=0, sticky="w", pady=(3, 0))

        self._rto_input = AutocompleteRTO(
            self._rto_container,
            on_select=self._on_rto_autocomplete_selected,
            default_rto="GJ-16",
        )
        self._rto_input.grid(row=0, column=0, sticky="ew")
        code, lat, lon = self._rto_input.get_rto()
        self._rto_coord_lbl.config(text=f"GPS Target: {lat:.6f}°N, {lon:.6f}°E  ({RTO_TABLE[code]['name']})")

        # Fields: Manual Lat / Lon (CGM / GPCB)
        self._lat_lbl = tk.Label(
            self._inputs_card, text="Latitude:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self._lat_frame = tk.Frame(self._inputs_card, bg=COLORS["bg_card"])
        self._lat = tk.Entry(
            self._lat_frame, font=FONTS["input"], bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"],
            relief="flat", highlightbackground=COLORS["border"], highlightthickness=1, width=14
        )
        self._lat.insert(0, "21.749826")
        self._lat.pack(side="left")
        tk.Label(self._lat_frame, text="°N", fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side="left", padx=4)

        self._lon_lbl = tk.Label(
            self._inputs_card, text="Longitude:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )
        self._lon_frame = tk.Frame(self._inputs_card, bg=COLORS["bg_card"])
        self._lon = tk.Entry(
            self._lon_frame, font=FONTS["input"], bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"],
            relief="flat", highlightbackground=COLORS["border"], highlightthickness=1, width=14
        )
        self._lon.insert(0, "73.098231")
        self._lon.pack(side="left")
        tk.Label(self._lon_frame, text="°E", fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side="left", padx=4)

        # Field: Interval
        self._interval_lbl = tk.Label(
            self._inputs_card, text="Interval (sec):", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        )

        self._interval_box = tk.Frame(self._inputs_card, bg=COLORS["bg_card"])

        self._interval = tk.Spinbox(
            self._interval_box, from_=1, to=3600, width=6, font=FONTS["input"],
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"], relief="flat",
            highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._interval.delete(0, "end")
        self._interval.insert(0, "10")
        self._interval.pack(side="left")

        # Field: Auto Sequence / SOS cycle (VLTD only)
        self._auto_sos_var = tk.BooleanVar(value=True)
        self._auto_sos_cb = ttk.Checkbutton(
            self._interval_box, text="Auto-push all 5 packets (LGN → HEL → PVT → EMR → SEM) in sequence",
            variable=self._auto_sos_var, style="Card.TCheckbutton"
        )
        self._auto_sos_cb.pack(side="left", padx=(16, 0))

        # ---------------- 4. Emergency Action Row (VLTD only) ---------------- #
        self._emg_frame = tk.Frame(
            self, bg=COLORS["bg_card"], highlightbackground=COLORS["border"],
            highlightthickness=1, padx=16, pady=10
        )
        self._emg_frame.pack(fill="x", padx=16, pady=(0, 12))

        tk.Label(
            self._emg_frame, text="Emergency Response:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        ).pack(side="left", padx=(0, 12))

        self._sos_on_btn = tk.Button(
            self._emg_frame, text="🚨  SOS ON (EMR)", font=FONTS["btn_normal"],
            bg=COLORS["danger"], fg="#ffffff", activebackground=COLORS["danger_hover"],
            activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2", command=lambda: self._trigger_sos("EMR"), state="disabled"
        )
        self._sos_on_btn.pack(side="left", padx=4)

        self._sos_off_btn = tk.Button(
            self._emg_frame, text="🛡️  SOS OFF (SEM)", font=FONTS["btn_normal"],
            bg=COLORS["info"], fg="#ffffff", activebackground=COLORS["info_hover"],
            activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2", command=lambda: self._trigger_sos("SEM"), state="disabled"
        )
        self._sos_off_btn.pack(side="left", padx=4)

        # ---------------- 5. Debug Drawer (Technical diagnostics) ---------------- #
        self._debug_drawer = ttk.LabelFrame(
            self, text="⚙️ Debug Mode — Technical Diagnostics & Packet Inspector",
            style="Debug.TLabelframe", padding=(12, 8)
        )
        # Note: self._debug_drawer is packed/unpacked dynamically via set_debug_mode()

        # Debug Row 1: Server endpoints & CGM HMAC
        self._debug_srv_lbl = tk.Label(
            self._debug_drawer, text="", font=FONTS["code"],
            fg=COLORS["text_accent"], bg=COLORS["bg_input"]
        )
        self._debug_srv_lbl.pack(anchor="w", pady=(0, 6))

        # CGM HMAC key frame
        self._hmac_frame = tk.Frame(self._debug_drawer, bg=COLORS["bg_input"])
        tk.Label(
            self._hmac_frame, text="HMAC Key:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"]
        ).pack(side="left", padx=(0, 6))
        self._hmac_var = tk.StringVar(value="26bcb9e368440d4a")
        self._hmac_entry = tk.Entry(
            self._hmac_frame, textvariable=self._hmac_var, width=20,
            font=FONTS["code"], bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            relief="flat", highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._hmac_entry.pack(side="left")

        # Debug Row 2: Manual Packet Push Buttons
        self._debug_btns_frame = tk.Frame(self._debug_drawer, bg=COLORS["bg_input"])
        self._debug_btns_frame.pack(fill="x", pady=(4, 8))

        tk.Label(
            self._debug_btns_frame, text="Direct Push:", font=FONTS["caption"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"]
        ).pack(side="left", padx=(0, 6))

        for ptype, lbl in [
            ("LGN", "LGN :9031"),
            ("HEL", "HEL :9031"),
            ("PVT", "PVT :9031"),
            ("EMR", "EMR :9032"),
            ("SEM", "SEM :9032"),
        ]:
            ttk.Button(
                self._debug_btns_frame, text=lbl,
                command=lambda p=ptype: self._on_manual_push(p)
            ).pack(side="left", padx=2)

        # Debug Row 3: Log Stream
        log_header = tk.Frame(self._debug_drawer, bg=COLORS["bg_input"])
        log_header.pack(fill="x", pady=(2, 4))
        tk.Label(
            log_header, text="Socket Transmission Log:", font=FONTS["caption"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"]
        ).pack(side="left")

        tk.Button(
            log_header, text="Clear", font=FONTS["caption"], bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], relief="flat", bd=0, padx=6, pady=1,
            cursor="hand2", command=self.clear_log
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            log_header, text="Export", font=FONTS["caption"], bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"], relief="flat", bd=0, padx=6, pady=1,
            cursor="hand2", command=self._export_log
        ).pack(side="right")

        self._log = tk.Text(
            self._debug_drawer, height=7, wrap="none", font=FONTS["code"],
            state="disabled", bg="#050811", fg="#38bdf8", relief="flat",
            highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._log.pack(fill="both", expand=True)

        # Apply profile-specific view rules
        self._apply_profile_visibility("VLTD")

    # ------------------------------------------------------------------ #
    #  Profile and Input Visibility                                      #
    # ------------------------------------------------------------------ #

    def _on_profile_change(self, event=None) -> None:
        profile = self._profile_var.get()
        self._apply_profile_visibility(profile)
        if self._on_profile_change_cb:
            self._on_profile_change_cb(self._dev_num, profile)

    def _on_rto_autocomplete_selected(self, code: str, lat: float, lon: float) -> None:
        """Called automatically when an RTO recommendation is selected."""
        name = RTO_TABLE.get(code, {}).get("name", "Unknown")
        self._rto_coord_lbl.config(text=f"GPS Target: {lat:.6f}°N, {lon:.6f}°E  ({name})")

    def _apply_profile_visibility(self, profile: str) -> None:
        """Update field layouts based on active profile."""
        srv = PROFILE_SERVER.get(profile, PROFILE_SERVER["VLTD"])
        if profile == "VLTD":
            srv_text = f"Server: {srv['host']}  |  Primary: :{srv['port']}  |  Emergency: :{srv.get('emergency_port', 9032)}"
        else:
            srv_text = f"Server: {srv['host']}:{srv['port']}"
        self._debug_srv_lbl.config(text=srv_text)

        if profile == "VLTD":
            self._vreg_lbl.grid_remove()
            self._vreg.grid_remove()
            self._lat_lbl.grid_remove()
            self._lat_frame.grid_remove()
            self._lon_lbl.grid_remove()
            self._lon_frame.grid_remove()
            self._rto_lbl.grid(row=1, column=0, sticky="w", pady=6)
            self._rto_container.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=6)
            self._interval_lbl.grid(row=2, column=0, sticky="w", pady=6)
            self._interval_box.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)
            self._auto_sos_cb.pack(side="left", padx=(16, 0))
            self._emg_frame.pack(fill="x", padx=16, pady=(0, 12))
            self._hmac_frame.pack_forget()
            self._debug_btns_frame.pack(fill="x", pady=(4, 8))

        elif profile == "GPCB":
            self._rto_lbl.grid_remove()
            self._rto_container.grid_remove()
            self._vreg_lbl.grid(row=1, column=0, sticky="w", pady=6)
            self._vreg.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=6)
            self._lat_lbl.grid(row=2, column=0, sticky="w", pady=6)
            self._lat_frame.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)
            self._lon_lbl.grid(row=3, column=0, sticky="w", pady=6)
            self._lon_frame.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=6)
            self._interval_lbl.grid(row=4, column=0, sticky="w", pady=6)
            self._interval_box.grid(row=4, column=1, sticky="w", padx=(12, 0), pady=6)
            self._auto_sos_cb.pack_forget()
            self._emg_frame.pack_forget()
            self._hmac_frame.pack_forget()
            self._debug_btns_frame.pack_forget()

        elif profile == "CGM":
            self._vreg_lbl.grid_remove()
            self._vreg.grid_remove()
            self._rto_lbl.grid_remove()
            self._rto_container.grid_remove()
            self._lat_lbl.grid(row=1, column=0, sticky="w", pady=6)
            self._lat_frame.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=6)
            self._lon_lbl.grid(row=2, column=0, sticky="w", pady=6)
            self._lon_frame.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)
            self._interval_lbl.grid(row=3, column=0, sticky="w", pady=6)
            self._interval_box.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=6)
            self._auto_sos_cb.pack_forget()
            self._emg_frame.pack_forget()
            self._hmac_frame.pack(anchor="w", pady=(0, 6))
            self._debug_btns_frame.pack_forget()

    # ------------------------------------------------------------------ #
    #  Debug Mode Toggle                                                 #
    # ------------------------------------------------------------------ #

    def set_debug_mode(self, enabled: bool) -> None:
        """Show or hide the technical diagnostics drawer."""
        self._debug_mode = enabled
        if enabled:
            self._debug_drawer.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        else:
            self._debug_drawer.pack_forget()

    # ------------------------------------------------------------------ #
    #  Button & Action Handlers                                          #
    # ------------------------------------------------------------------ #

    def _toggle_start_stop(self) -> None:
        if not self._running:
            self._on_start_click()
        else:
            self._on_stop_click()

    def _on_start_click(self) -> None:
        cfg = self._collect_config()
        if cfg is None:
            return
        self._running = True
        self._start_stop_btn.config(
            text="■  STOP SIMULATOR", bg=COLORS["danger"], activebackground=COLORS["danger_hover"]
        )
        self._set_fields_state("disabled")
        if self._profile_var.get() == "VLTD":
            self._sos_on_btn.config(state="normal")
            self._sos_off_btn.config(state="normal")
        self._on_start(cfg)

    def _on_stop_click(self) -> None:
        self._running = False
        self._start_stop_btn.config(
            text="▶  START SIMULATOR", bg=COLORS["success"], activebackground=COLORS["success_hover"]
        )
        self._sos_on_btn.config(state="disabled")
        self._sos_off_btn.config(state="disabled")
        self._set_fields_state("normal")
        self._on_stop()

    def _trigger_sos(self, mode: str) -> None:
        if not self._running:
            return
        cfg = self._collect_config()
        if cfg and self._on_sos:
            if mode == "EMR":
                self._sos_on_btn.config(text="🚨 ACTIVE", relief="sunken")
                self._sos_off_btn.config(text="🛡️ SOS OFF", relief="flat")
            else:
                self._sos_on_btn.config(text="🚨 SOS ON", relief="flat")
                self._sos_off_btn.config(text="🛡️ CLEARED", relief="sunken")
                self.after(2000, lambda: self._sos_off_btn.config(text="🛡️ SOS OFF", relief="flat"))
            self._on_sos(self._dev_num, cfg, mode)

    def _on_manual_push(self, ptype: str) -> None:
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
            rto_code, lat, lon = self._rto_input.get_rto()
            vreg = "GJ01AC0000"
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
            "hmac_key":       self._hmac_var.get().strip().encode("ascii") if profile == "CGM" else None,
        }

    def _set_fields_state(self, state: str) -> None:
        profile = self._profile_var.get()
        self._imei.config(state=state)
        self._interval.config(state=state)
        self._profile_cb.config(state="disabled" if state == "disabled" else "readonly")
        if profile == "GPCB":
            self._vreg.config(state=state)
        if profile in ("CGM", "GPCB"):
            self._lat.config(state=state)
            self._lon.config(state=state)
        if profile == "VLTD":
            self._rto_input.config(state=state)
            self._auto_sos_cb.config(state=state)

    def get_profile(self) -> str:
        return self._profile_var.get()

    def get_imei_suffix(self) -> str:
        imei = self._imei.get().strip()
        return imei[-6:] if len(imei) >= 6 else imei

    # ------------------------------------------------------------------ #
    #  Public State Updates (called from GUI thread)                     #
    # ------------------------------------------------------------------ #

    def set_status(self, status: str, count: int) -> None:
        self._count_var.set(str(count))
        self._status_badge.config(text=status.upper())

        if status == "Sending":
            self._status_dot.config(fg=COLORS["success"])
            self._status_badge.config(fg=COLORS["success"])
        elif status in ("Connecting", "Connected"):
            self._status_dot.config(fg=COLORS["warning"])
            self._status_badge.config(fg=COLORS["warning"])
        else:
            self._status_dot.config(fg=COLORS["stopped"])
            self._status_badge.config(fg=COLORS["text_secondary"])

        if status == "Stopped":
            self._running = False
            self._start_stop_btn.config(
                text="▶  START SIMULATOR", bg=COLORS["success"], activebackground=COLORS["success_hover"]
            )
            self._sos_on_btn.config(state="disabled", text="🚨 SOS ON")
            self._sos_off_btn.config(state="disabled", text="🛡️ SOS OFF")
            self._set_fields_state("normal")

    def append_log(self, msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.config(state="normal")
        self._log.insert("end", f"[{ts}] {msg}\n")
        self._log.see("end")
        self._log.config(state="disabled")

    def clear_log(self) -> None:
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _export_log(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"device_{self._dev_num}_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if path:
            content = self._log.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Exported", f"Log saved to:\n{path}")

    def apply_coordinates(self, lat: float, lon: float) -> None:
        """Apply extracted GPS coordinates and automatically select nearest RTO."""
        best_code, rto_name, dist = find_nearest_rto(lat, lon)
        self._rto_input.set_rto(best_code, trigger_callback=False)
        self._rto_coord_lbl.config(
            text=f"GPS Extracted: {lat:.6f}°N, {lon:.6f}°E  ({rto_name} ~{dist:.1f}km away)"
        )
        self._lat.delete(0, "end")
        self._lat.insert(0, f"{lat:.6f}")
        self._lon.delete(0, "end")
        self._lon.insert(0, f"{lon:.6f}")
        self.append_log(f"📍 Location Loaded: {lat:.6f}, {lon:.6f} -> Nearest RTO: {best_code} ({rto_name})")

