# Google-style Autocomplete / Search Recommendation Dropdown for RTO Selection
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from ..rto_data import RTO_TABLE, search_rto, resolve_rto
from .styles import COLORS, FONTS


class AutocompleteRTO(tk.Frame):
    """
    Google-style instant search & recommendation widget.
    Typing 'bh' immediately displays recommendations like:
      - GJ-16 – Bharuch
      - GJ-04 – Bhavnagar
      - GJ-12 – Bhuj (Kutch)
    Supports arrow key navigation, hover highlight, and instant click selection.
    """

    def __init__(
        self,
        parent,
        on_select: Optional[Callable[[str, float, float], None]] = None,
        default_rto: str = "GJ-16",
        **kwargs,
    ):
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)
        self._on_select = on_select
        self._selected_code = default_rto if default_rto in RTO_TABLE else "GJ-16"
        self._matches: list[str] = []
        self._popup: Optional[tk.Toplevel] = None
        self._listbox: Optional[tk.Listbox] = None
        self._is_selecting = False

        self._build_ui()
        self.set_rto(self._selected_code, trigger_callback=False)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        # ---------------- Search Input Container ---------------- #
        self._box_frame = tk.Frame(
            self, bg=COLORS["bg_input"],
            highlightbackground=COLORS["border"], highlightthickness=1
        )
        self._box_frame.grid(row=0, column=0, sticky="ew")
        self._box_frame.columnconfigure(1, weight=1)

        # Search Icon
        self._icon_lbl = tk.Label(
            self._box_frame, text="🔍", font=("Segoe UI", 10),
            fg=COLORS["text_secondary"], bg=COLORS["bg_input"]
        )
        self._icon_lbl.grid(row=0, column=0, padx=(8, 4), pady=4)

        # Main Search Entry
        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self._box_frame, textvariable=self._var, font=FONTS["input"],
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"], relief="flat", bd=0
        )
        self._entry.grid(row=0, column=1, sticky="ew", pady=5)

        # Clear "✕" Button
        self._clear_btn = tk.Label(
            self._box_frame, text="✕", font=("Segoe UI", 9, "bold"),
            fg=COLORS["text_muted"], bg=COLORS["bg_input"], cursor="hand2"
        )
        self._clear_btn.grid(row=0, column=2, padx=(4, 8), pady=4)
        self._clear_btn.bind("<Button-1>", lambda e: self.clear_and_focus())
        self._clear_btn.bind("<Enter>", lambda e: self._clear_btn.config(fg=COLORS["danger"]))
        self._clear_btn.bind("<Leave>", lambda e: self._clear_btn.config(fg=COLORS["text_muted"]))

        # Event bindings on entry
        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Down>", self._on_arrow_down)
        self._entry.bind("<Up>", self._on_arrow_up)
        self._entry.bind("<Return>", self._on_enter_pressed)
        self._entry.bind("<Escape>", lambda e: self._hide_popup())

        # Close popup if root window moves or user clicks outside
        self.winfo_toplevel().bind("<Configure>", lambda e: self._hide_popup(), add="+")
        self.winfo_toplevel().bind("<Button-1>", self._on_global_click, add="+")

    # ------------------------------------------------------------------ #
    #  Recommendation Popup Management                                    #
    # ------------------------------------------------------------------ #

    def _ensure_popup(self) -> None:
        if self._popup and self._popup.winfo_exists():
            return

        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)
        self._popup.config(bg=COLORS["border"], padx=1, pady=1)

        # Recommendation Listbox
        self._listbox = tk.Listbox(
            self._popup, font=FONTS["input"],
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            selectbackground=COLORS["text_accent"], selectforeground="#0b0f19",
            activestyle="none", relief="flat", bd=0, highlightthickness=0,
            cursor="hand2"
        )
        self._listbox.pack(fill="both", expand=True)

        self._listbox.bind("<Motion>", self._on_listbox_hover)
        self._listbox.bind("<ButtonRelease-1>", self._on_listbox_click)
        self._listbox.bind("<Return>", self._on_listbox_click)

    def _show_recommendations(self, items: list[str]) -> None:
        if not items:
            self._hide_popup()
            return

        self._ensure_popup()
        self._matches = items

        # Populate recommendations
        self._listbox.delete(0, tk.END)
        for item in items:
            self._listbox.insert(tk.END, f"  {item}")

        # Position popup directly below search box
        self.update_idletasks()
        x = self._box_frame.winfo_rootx()
        y = self._box_frame.winfo_rooty() + self._box_frame.winfo_height() + 2
        width = max(self._box_frame.winfo_width(), 260)
        height = min(len(items) * 26 + 4, 210)

        self._popup.geometry(f"{width}x{height}+{x}+{y}")
        self._popup.deiconify()
        self._popup.lift()

    def _hide_popup(self) -> None:
        if self._popup and self._popup.winfo_exists():
            self._popup.withdraw()

    # ------------------------------------------------------------------ #
    #  Event Handlers                                                    #
    # ------------------------------------------------------------------ #

    def _on_key_release(self, event) -> None:
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return

        query = self._var.get().strip()
        self._highlight_border(active=True)

        if not query:
            # Show top recommended RTOs
            matches = search_rto("")[:7]
        else:
            matches = search_rto(query)[:8]

        self._show_recommendations(matches)

    def _on_focus_in(self, event) -> None:
        self._highlight_border(active=True)
        query = self._var.get().strip()
        matches = search_rto(query)[:8]
        self._show_recommendations(matches)

    def _on_focus_out(self, event) -> None:
        # Hide after short delay to allow listbox click events to process
        self._highlight_border(active=False)
        self.after(200, self._hide_popup)

    def _on_global_click(self, event) -> None:
        # If click was outside both entry and popup, hide
        if not self._popup or not self._popup.winfo_exists():
            return
        widget = event.widget
        if widget not in (self._entry, self._listbox, self._box_frame, self._icon_lbl, self._clear_btn):
            self._hide_popup()

    def _on_arrow_down(self, event) -> str:
        if not self._listbox or not self._matches:
            return "break"
        cur = self._listbox.curselection()
        next_idx = 0 if not cur else min(cur[0] + 1, len(self._matches) - 1)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(next_idx)
        self._listbox.activate(next_idx)
        self._listbox.see(next_idx)
        return "break"

    def _on_arrow_up(self, event) -> str:
        if not self._listbox or not self._matches:
            return "break"
        cur = self._listbox.curselection()
        prev_idx = len(self._matches) - 1 if not cur else max(cur[0] - 1, 0)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(prev_idx)
        self._listbox.activate(prev_idx)
        self._listbox.see(prev_idx)
        return "break"

    def _on_enter_pressed(self, event) -> str:
        if self._listbox and self._matches:
            cur = self._listbox.curselection()
            if cur:
                self._select_index(cur[0])
                return "break"
        # If no item selected from list, resolve whatever was typed
        query = self._var.get().strip()
        if query:
            code, lat, lon = resolve_rto(query)
            self.set_rto(code)
            self._hide_popup()
        return "break"

    def _on_listbox_hover(self, event) -> None:
        if not self._listbox:
            return
        idx = self._listbox.nearest(event.y)
        if 0 <= idx < len(self._matches):
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(idx)
            self._listbox.activate(idx)

    def _on_listbox_click(self, event=None) -> None:
        if not self._listbox:
            return
        cur = self._listbox.curselection()
        if cur:
            self._select_index(cur[0])

    def _select_index(self, index: int) -> None:
        if 0 <= index < len(self._matches):
            selected_str = self._matches[index]
            code, lat, lon = resolve_rto(selected_str)
            self.set_rto(code)
            self._hide_popup()

    def _highlight_border(self, active: bool) -> None:
        color = COLORS["text_accent"] if active else COLORS["border"]
        self._box_frame.config(highlightbackground=color)

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def set_rto(self, code: str, trigger_callback: bool = True) -> None:
        """Programmatically select an RTO by code (e.g. 'GJ-16', 'GJ-05')."""
        target_code = code.upper().strip()
        if target_code not in RTO_TABLE:
            target_code = "GJ-01"
        self._selected_code = target_code
        info = RTO_TABLE[target_code]
        display_text = f"{target_code} – {info['name']}"
        self._var.set(display_text)

        if trigger_callback and self._on_select:
            self._on_select(target_code, info["lat"], info["lon"])

    def get_rto(self) -> tuple[str, float, float]:
        """Return currently selected (code, lat, lon)."""
        query = self._var.get().strip()
        if query:
            code, lat, lon = resolve_rto(query)
            return code, lat, lon
        code = self._selected_code or "GJ-01"
        return code, RTO_TABLE[code]["lat"], RTO_TABLE[code]["lon"]

    def clear_and_focus(self) -> None:
        """Clear search field and pop open recommendation list."""
        self._var.set("")
        self._entry.focus_set()
        matches = search_rto("")[:8]
        self._show_recommendations(matches)

    def config(self, **kwargs) -> None:
        """Proxy config calls like state='disabled'."""
        if "state" in kwargs:
            st = kwargs.pop("state")
            self._entry.config(state=st)
            if st == "disabled":
                self._clear_btn.unbind("<Button-1>")
                self._clear_btn.config(fg=COLORS["border"])
            else:
                self._clear_btn.bind("<Button-1>", lambda e: self.clear_and_focus())
                self._clear_btn.config(fg=COLORS["text_muted"])
        if kwargs:
            super().config(**kwargs)

    configure = config
