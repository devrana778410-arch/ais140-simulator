# Main application window — Modern Minimalist Sidebar Layout with Toggleable Debug Mode
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
from .device_tab import DeviceTab, PROFILE_SERVER
from .styles import COLORS, FONTS, apply_theme
from ..client import DeviceClient
from ..geo_link import extract_coordinates
from ..rto_data import get_rto_coords, resolve_rto
from ..packet import build_packet as build_cgm_packet
from ..gpcb_packet import build_packet as build_gpcb_packet
from ..vltd_packet import build_packet as build_vltd_packet
from ..psdn_packet import build_packet as build_psdn_packet

PACKET_BUILDERS = {
    "CGM":         build_cgm_packet,
    "GPCB":        build_gpcb_packet,
    "VLTD":        build_vltd_packet,
    "GPCB (PSDN)": build_psdn_packet,
    "PSDN":        build_psdn_packet,
}

PROFILE_BADGE_COLORS = {
    "VLTD":        ("#38bdf8", "#082f49"),  # Sky text on deep sky
    "CGM":         ("#a78bfa", "#2e1065"),  # Violet text on deep violet
    "GPCB":        ("#34d399", "#064e3b"),  # Emerald text on deep emerald
    "GPCB (PSDN)": ("#f59e0b", "#451a03"),  # Amber text on deep amber
    "PSDN":        ("#f59e0b", "#451a03"),  # Amber text on deep amber
}


class SimulatorApp:
    """
    Modern AIS-140 Simulator Window.
    Sidebar + Viewport layout:
      - Left sidebar lists active devices with real-time status and packet counts.
      - Right viewport renders the active device's clean, minimalist interface.
      - Debug Mode toggle switch reveals technical diagnostics on-demand.
    """

    APP_TITLE   = "AIS-140 Simulator"
    APP_VERSION = "v2.0"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{self.APP_TITLE} {self.APP_VERSION}")
        self.root.minsize(880, 620)
        self.root.geometry("980x680")
        self.root.resizable(True, True)

        apply_theme(self.root)

        # device_id -> { "tab": DeviceTab, "client": DeviceClient | None, "tile": dict }
        self._devices: dict[int, dict] = {}
        self._selected_id: int | None = None
        self._next_id = 1
        self._debug_mode = False

        self._build_ui()
        self._setup_shortcuts()
        self._add_device()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    #  UI Construction                                                   #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # Two-column grid: col 0 = Sidebar (fixed width), col 1 = Content (expands)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ---------------- Left Sidebar ---------------- #
        self._sidebar = tk.Frame(
            self.root, bg=COLORS["bg_sidebar"], width=230,
            highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.pack_propagate(False)

        # Brand header
        brand_frame = tk.Frame(self._sidebar, bg=COLORS["bg_sidebar"])
        brand_frame.pack(fill="x", padx=14, pady=(16, 14))

        brand_row = tk.Frame(brand_frame, bg=COLORS["bg_sidebar"])
        brand_row.pack(anchor="w")

        tk.Label(
            brand_row, text="🛰️", font=("Segoe UI", 14), bg=COLORS["bg_sidebar"]
        ).pack(side="left", padx=(0, 6))

        tk.Label(
            brand_row, text=self.APP_TITLE, font=FONTS["brand_title"],
            fg=COLORS["text_primary"], bg=COLORS["bg_sidebar"]
        ).pack(side="left")

        tk.Label(
            brand_frame, text=f"Multi-Profile Simulator • {self.APP_VERSION}",
            font=FONTS["caption"], fg=COLORS["text_secondary"], bg=COLORS["bg_sidebar"]
        ).pack(anchor="w", padx=(26, 0), pady=(2, 0))

        # Devices Section Header with "＋ Add" Button
        dev_header = tk.Frame(self._sidebar, bg=COLORS["bg_sidebar"])
        dev_header.pack(fill="x", padx=14, pady=(6, 6))

        tk.Label(
            dev_header, text="DEVICES", font=FONTS["section_h"],
            fg=COLORS["text_muted"], bg=COLORS["bg_sidebar"]
        ).pack(side="left")

        add_btn = tk.Button(
            dev_header, text="＋ Add", font=FONTS["caption"],
            bg=COLORS["bg_card"], fg=COLORS["text_accent"],
            activebackground=COLORS["info"], activeforeground="#ffffff",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._add_device
        )
        add_btn.pack(side="right")

        import_btn = tk.Button(
            dev_header, text="📂 CSV", font=FONTS["caption"],
            bg=COLORS["bg_card"], fg="#38bdf8",
            activebackground=COLORS["info"], activeforeground="#ffffff",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._import_csv
        )
        import_btn.pack(side="right", padx=(0, 4))

        # Scrollable Device Tiles Container
        self._tiles_canvas = tk.Canvas(
            self._sidebar, bg=COLORS["bg_sidebar"], highlightthickness=0, bd=0
        )
        self._tiles_canvas.pack(fill="both", expand=True, padx=8, pady=2)

        self._tiles_frame = tk.Frame(self._tiles_canvas, bg=COLORS["bg_sidebar"])
        self._tiles_canvas.create_window((0, 0), window=self._tiles_frame, anchor="nw", width=214)

        self._tiles_frame.bind(
            "<Configure>",
            lambda e: self._tiles_canvas.configure(scrollregion=self._tiles_canvas.bbox("all"))
        )

        # Sidebar Footer: Debug Mode Toggle & Hotkey hint
        footer_frame = tk.Frame(
            self._sidebar, bg=COLORS["bg_sidebar"],
            highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10
        )
        footer_frame.pack(fill="x", side="bottom")

        debug_row = tk.Frame(footer_frame, bg=COLORS["bg_sidebar"])
        debug_row.pack(fill="x")

        tk.Label(
            debug_row, text="⚙️ Debug Mode", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_sidebar"]
        ).pack(side="left")

        self._debug_btn = tk.Button(
            debug_row, text="OFF", font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["text_muted"],
            activebackground=COLORS["warning"], activeforeground="#000000",
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._toggle_debug_mode
        )
        self._debug_btn.pack(side="right")

        tk.Label(
            footer_frame, text="Shortcut: F12 or Ctrl+D", font=("Segoe UI", 7),
            fg=COLORS["text_muted"], bg=COLORS["bg_sidebar"]
        ).pack(anchor="w", pady=(4, 0))

        # ---------------- Right Main Viewport ---------------- #
        self._main_viewport = tk.Frame(self.root, bg=COLORS["bg_app"])
        self._main_viewport.grid(row=0, column=1, sticky="nsew")

        # ---------------- Top Bar: Location Link Extraction ---------------- #
        link_card = tk.Frame(
            self._main_viewport, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            padx=14, pady=10
        )
        link_card.pack(fill="x", padx=16, pady=(14, 6))
        link_card.columnconfigure(1, weight=1)

        tk.Label(
            link_card, text="📍 Location Link:", font=FONTS["body_bold"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_card"]
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._link_entry = tk.Entry(
            link_card, font=FONTS["input"], bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"],
            relief="flat", highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._link_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self._link_entry.bind("<Return>", lambda e: self._on_extract_and_add())

        extract_add_btn = tk.Button(
            link_card, text="＋ Add Device", font=FONTS["btn_normal"],
            bg=COLORS["info"], fg="#ffffff", activebackground="#2563eb",
            activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=5,
            cursor="hand2", command=self._on_extract_and_add
        )
        extract_add_btn.grid(row=0, column=2, padx=(0, 6))

        extract_apply_btn = tk.Button(
            link_card, text="⚡ Apply to Active", font=FONTS["caption"],
            bg=COLORS["bg_sidebar"], fg=COLORS["text_accent"],
            activebackground=COLORS["bg_card_hover"], activeforeground="#ffffff",
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=self._on_extract_and_apply
        )
        extract_apply_btn.grid(row=0, column=3)

    def _setup_shortcuts(self) -> None:
        self.root.bind("<F12>", lambda e: self._toggle_debug_mode())
        self.root.bind("<Control-d>", lambda e: self._toggle_debug_mode())
        self.root.bind("<Control-D>", lambda e: self._toggle_debug_mode())

    # ------------------------------------------------------------------ #
    #  Device Management & Sidebar Synchronization                       #
    # ------------------------------------------------------------------ #

    def _add_device(self) -> int:
        dev_id = self._next_id
        self._next_id += 1

        tab = DeviceTab(
            self._main_viewport,
            device_num=dev_id,
            on_start=lambda cfg, did=dev_id: self._start_device(did, cfg),
            on_stop=lambda did=dev_id: self._stop_device(did),
            on_remove=lambda did=dev_id: self._remove_device(did),
            on_sos=lambda did, cfg, mode: self._handle_sos(did, cfg, mode),
            on_push_single=lambda did, cfg, ptype: self._handle_push_single(did, cfg, ptype),
            on_profile_change_cb=lambda did, prof: self._update_tile_profile(did, prof),
        )
        tab.set_debug_mode(self._debug_mode)

        # Create tile in sidebar
        tile = self._create_device_tile(dev_id, tab.get_profile())

        self._devices[dev_id] = {
            "tab": tab,
            "client": None,
            "tile": tile,
        }

        # Select this newly added device
        self._select_device(dev_id)
        return dev_id

    def _on_extract_and_add(self) -> None:
        raw = self._link_entry.get().strip()
        if not raw:
            messagebox.showwarning("Empty Link", "Please enter or paste a WhatsApp/Google Maps location link.")
            return
        coords = extract_coordinates(raw)
        if not coords:
            messagebox.showerror(
                "Invalid Location",
                "Could not extract coordinates from link.\nExample format:\nhttps://maps.google.com/maps?q=21.86664%2C73.1830466"
            )
            return
        lat, lon = coords
        dev_id = self._add_device()
        self._devices[dev_id]["tab"].apply_coordinates(lat, lon)
        self._link_entry.delete(0, "end")

    def _on_extract_and_apply(self) -> None:
        raw = self._link_entry.get().strip()
        if not raw:
            messagebox.showwarning("Empty Link", "Please enter or paste a WhatsApp/Google Maps location link.")
            return
        coords = extract_coordinates(raw)
        if not coords:
            messagebox.showerror(
                "Invalid Location",
                "Could not extract coordinates from link.\nExample format:\nhttps://maps.google.com/maps?q=21.86664%2C73.1830466"
            )
            return
        if self._selected_id and self._selected_id in self._devices:
            lat, lon = coords
            self._devices[self._selected_id]["tab"].apply_coordinates(lat, lon)
            self._link_entry.delete(0, "end")

    def _import_csv(self) -> None:
        """Batch import vehicles from a CSV spreadsheet (similar to base.apk batch feature)."""
        path = filedialog.askopenfilename(
            title="Import Vehicles from CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not path:
            return

        imported_count = 0
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                messagebox.showwarning("Empty File", "The selected CSV file contains no records.")
                return

            for row in rows:
                imei = row.get("imei") or row.get("IMEI") or ""
                imei = str(imei).strip()
                if not imei:
                    continue

                vreg = row.get("vehicle_no") or row.get("vehicleNumber") or row.get("vreg") or "GJ01AC0000"
                vreg = str(vreg).strip()

                rto = row.get("rto") or row.get("RTO") or ""
                rto = str(rto).strip()

                lat_str = row.get("latitude") or row.get("lat") or ""
                lon_str = row.get("longitude") or row.get("lon") or ""

                if lat_str and lon_str:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                    except ValueError:
                        lat, lon = get_rto_coords(rto) if rto else (21.7051, 72.9959)
                elif rto:
                    lat, lon = get_rto_coords(rto)
                else:
                    lat, lon = (21.7051, 72.9959)

                profile = row.get("profile") or "GPCB (PSDN)"
                if profile not in PACKET_BUILDERS:
                    profile = "GPCB (PSDN)"

                # Reuse initial blank device if untouched
                if imported_count == 0 and len(self._devices) == 1 and 1 in self._devices:
                    first_tab = self._devices[1]["tab"]
                    if getattr(first_tab, "packet_count", 0) == 0 and not getattr(first_tab, "_running", False):
                        dev_id = 1
                    else:
                        dev_id = self._add_device()
                else:
                    dev_id = self._add_device()

                tab = self._devices[dev_id]["tab"]
                tab.load_vehicle_info(imei=imei, vreg=vreg, lat=lat, lon=lon, profile=profile)
                self._update_tile_profile(dev_id, profile)
                imported_count += 1

            messagebox.showinfo(
                "Import Successful",
                f"Successfully imported {imported_count} vehicle(s) from CSV!\nAll configured with profile GPCB (PSDN) on port 17003."
            )
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to parse CSV file:\n{e}")

    def open_location_link(self, raw_link: str) -> None:
        """Handle location link passed via CLI or Windows 'Open with'."""
        coords = extract_coordinates(raw_link)
        if coords:
            lat, lon = coords
            if self._selected_id and self._selected_id in self._devices:
                self._devices[self._selected_id]["tab"].apply_coordinates(lat, lon)
            else:
                dev_id = self._add_device()
                self._devices[dev_id]["tab"].apply_coordinates(lat, lon)

    def _create_device_tile(self, dev_id: int, profile: str) -> dict:
        tile_frame = tk.Frame(
            self._tiles_frame, bg=COLORS["bg_sidebar"],
            highlightbackground=COLORS["border"], highlightthickness=1,
            cursor="hand2", padx=10, pady=8
        )
        tile_frame.pack(fill="x", pady=3)

        # Row 1: status dot + Device Name + profile pill
        row1 = tk.Frame(tile_frame, bg=COLORS["bg_sidebar"])
        row1.pack(fill="x")

        status_dot = tk.Label(
            row1, text="●", font=("Segoe UI", 10),
            fg=COLORS["stopped"], bg=COLORS["bg_sidebar"]
        )
        status_dot.pack(side="left", padx=(0, 6))

        title_lbl = tk.Label(
            row1, text=f"Device {dev_id}", font=FONTS["device_name"],
            fg=COLORS["text_primary"], bg=COLORS["bg_sidebar"]
        )
        title_lbl.pack(side="left")

        fg_badge, bg_badge = PROFILE_BADGE_COLORS.get(profile, ("#ffffff", COLORS["bg_card"]))
        badge_lbl = tk.Label(
            row1, text=profile, font=FONTS["badge"],
            fg=fg_badge, bg=bg_badge, padx=5, pady=1
        )
        badge_lbl.pack(side="right")

        # Row 2: packet count pill
        row2 = tk.Frame(tile_frame, bg=COLORS["bg_sidebar"])
        row2.pack(fill="x", pady=(4, 0))

        count_lbl = tk.Label(
            row2, text="0 pkts", font=FONTS["caption"],
            fg=COLORS["text_secondary"], bg=COLORS["bg_sidebar"]
        )
        count_lbl.pack(side="left", padx=(16, 0))

        tile_dict = {
            "frame":      tile_frame,
            "status_dot": status_dot,
            "title_lbl":  title_lbl,
            "badge_lbl":  badge_lbl,
            "count_lbl":  count_lbl,
            "row1":       row1,
            "row2":       row2,
        }

        # Bind clicks to select
        for widget in (tile_frame, status_dot, title_lbl, badge_lbl, count_lbl, row1, row2):
            widget.bind("<Button-1>", lambda e, did=dev_id: self._select_device(did))

        return tile_dict

    def _select_device(self, dev_id: int) -> None:
        if dev_id not in self._devices:
            return

        # Deselect old
        if self._selected_id and self._selected_id in self._devices:
            old_tile = self._devices[self._selected_id]["tile"]
            self._set_tile_selected(old_tile, False)
            self._devices[self._selected_id]["tab"].pack_forget()

        # Select new
        self._selected_id = dev_id
        new_entry = self._devices[dev_id]
        self._set_tile_selected(new_entry["tile"], True)
        new_entry["tab"].pack(fill="both", expand=True)

    def _set_tile_selected(self, tile: dict, is_sel: bool) -> None:
        bg = COLORS["bg_card_hover"] if is_sel else COLORS["bg_sidebar"]
        border = COLORS["info"] if is_sel else COLORS["border"]
        tile["frame"].config(bg=bg, highlightbackground=border)
        tile["row1"].config(bg=bg)
        tile["row2"].config(bg=bg)
        tile["status_dot"].config(bg=bg)
        tile["title_lbl"].config(bg=bg, fg=COLORS["text_primary"] if is_sel else COLORS["text_secondary"])
        tile["count_lbl"].config(bg=bg)

    def _update_tile_profile(self, dev_id: int, profile: str) -> None:
        if dev_id in self._devices:
            badge = self._devices[dev_id]["tile"]["badge_lbl"]
            fg_badge, bg_badge = PROFILE_BADGE_COLORS.get(profile, ("#ffffff", COLORS["bg_card"]))
            badge.config(text=profile, fg=fg_badge, bg=bg_badge)

    def _update_tile_state(self, dev_id: int, status: str, count: int) -> None:
        if dev_id not in self._devices:
            return
        tile = self._devices[dev_id]["tile"]
        tile["count_lbl"].config(text=f"{count} pkts")

        if status == "Sending":
            tile["status_dot"].config(fg=COLORS["success"])
        elif status in ("Connecting", "Connected"):
            tile["status_dot"].config(fg=COLORS["warning"])
        else:
            tile["status_dot"].config(fg=COLORS["stopped"])

    def _remove_device(self, dev_id: int) -> None:
        if dev_id not in self._devices:
            return
        if len(self._devices) <= 1:
            messagebox.showinfo("Action Denied", "At least one device must remain active.")
            return

        entry = self._devices[dev_id]
        if entry["client"]:
            entry["client"].stop()

        entry["tab"].pack_forget()
        entry["tab"].destroy()
        entry["tile"]["frame"].destroy()

        del self._devices[dev_id]

        # Select next available device
        remaining_ids = list(self._devices.keys())
        if remaining_ids:
            self._select_device(remaining_ids[0])

    # ------------------------------------------------------------------ #
    #  Debug Mode Switch                                                 #
    # ------------------------------------------------------------------ #

    def _toggle_debug_mode(self) -> None:
        self._debug_mode = not self._debug_mode
        if self._debug_mode:
            self._debug_btn.config(text="ON", bg=COLORS["warning"], fg="#000000")
        else:
            self._debug_btn.config(text="OFF", bg=COLORS["bg_card"], fg=COLORS["text_muted"])

        # Update all device tabs
        for entry in self._devices.values():
            entry["tab"].set_debug_mode(self._debug_mode)

    # ------------------------------------------------------------------ #
    #  Device Execution Engine                                           #
    # ------------------------------------------------------------------ #

    def _start_device(self, dev_id: int, cfg: dict) -> None:
        if dev_id not in self._devices:
            return

        profile = cfg.get("profile", "VLTD")
        srv = PROFILE_SERVER.get(profile, PROFILE_SERVER["VLTD"])
        host = srv["host"]
        port = srv["port"]
        emergency_port = srv.get("emergency_port")
        builder = PACKET_BUILDERS.get(profile, build_vltd_packet)

        entry = self._devices[dev_id]
        if entry["client"]:
            entry["client"].stop()

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
        entry["client"] = client
        client.start()

    def _stop_device(self, dev_id: int) -> None:
        if dev_id not in self._devices:
            return
        entry = self._devices[dev_id]
        if entry["client"]:
            entry["client"].stop()

    def _handle_sos(self, dev_id: int, cfg: dict, mode: str) -> None:
        if dev_id not in self._devices:
            return
        client = self._devices[dev_id]["client"]
        if client:
            client.set_emergency(mode if mode == "EMR" else None)
            ptype = "EMR" if mode == "EMR" else "SEM"
            client.send_packet_type(ptype)

    def _handle_push_single(self, dev_id: int, cfg: dict, ptype: str) -> None:
        if dev_id not in self._devices:
            return
        entry = self._devices[dev_id]
        client = entry["client"]

        profile = cfg.get("profile", "VLTD")
        srv = PROFILE_SERVER.get(profile, PROFILE_SERVER["VLTD"])
        builder = PACKET_BUILDERS.get(profile, build_vltd_packet)

        if client is None:
            client = DeviceClient(
                host=srv["host"],
                port=srv["port"],
                device_config=cfg,
                packet_builder=builder,
                on_log=lambda msg, did=dev_id: self._device_log(did, msg),
                on_status=lambda status, count, did=dev_id: self._device_status(did, status, count),
                connect_timeout=srv.get("connect_timeout", 10),
                retry_delay=srv.get("retry_delay", 2),
                emergency_port=srv.get("emergency_port"),
            )
            entry["client"] = client
        else:
            client.update_config(cfg)

        client.send_packet_type(ptype)

    # ------------------------------------------------------------------ #
    #  Client Callbacks (Worker thread -> UI thread via root.after)      #
    # ------------------------------------------------------------------ #

    def _device_log(self, dev_id: int, msg: str) -> None:
        def _update():
            if dev_id in self._devices:
                self._devices[dev_id]["tab"].append_log(msg)
        self.root.after(0, _update)

    def _device_status(self, dev_id: int, status: str, count: int) -> None:
        def _update():
            if dev_id in self._devices:
                self._devices[dev_id]["tab"].set_status(status, count)
                self._update_tile_state(dev_id, status, count)
        self.root.after(0, _update)

    def _on_close(self) -> None:
        for entry in self._devices.values():
            if entry["client"]:
                entry["client"].stop()
        self.root.destroy()
