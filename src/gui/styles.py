# Design tokens, color palette, and ttk styling for AIS-140 Simulator
import tkinter as tk
from tkinter import ttk

# Modern Slate Dark Palette
COLORS = {
    # Backgrounds
    "bg_app":       "#0b0f19",   # Darkest canvas background
    "bg_sidebar":   "#111827",   # Deep slate for left navigation
    "bg_card":      "#1e293b",   # Card / panel surface
    "bg_card_hover":"#243248",   # Subtle hover for card / list items
    "bg_input":     "#0f172a",   # Input background
    "bg_selected":  "#1d4ed8",   # Selected device tile background

    # Borders & Dividers
    "border":       "#334155",   # Crisp subtle border
    "border_light": "#475569",   # Lighter border for active elements

    # Typography
    "text_primary":   "#f8fafc", # Brightest white
    "text_secondary": "#94a3b8", # Muted slate for captions/labels
    "text_muted":     "#64748b", # Faint helper text
    "text_accent":    "#38bdf8", # Sky blue accent text

    # Status & Accents
    "success":      "#10b981",   # Emerald green (live / running)
    "success_hover":"#059669",
    "danger":       "#ef4444",   # Rose red (stop / alert / remove)
    "danger_hover": "#dc2626",
    "warning":      "#f59e0b",   # Amber (connecting)
    "info":         "#3b82f6",   # Blue (primary accent / debug)
    "info_hover":   "#2563eb",
    "stopped":      "#64748b",   # Neutral slate
}

FONTS = {
    "brand_title": ("Segoe UI", 13, "bold"),
    "brand_sub":   ("Segoe UI", 8),
    "section_h":   ("Segoe UI", 9, "bold"),
    "device_name": ("Segoe UI", 10, "bold"),
    "caption":     ("Segoe UI", 8),
    "body":        ("Segoe UI", 9),
    "body_bold":   ("Segoe UI", 9, "bold"),
    "input":       ("Segoe UI", 10),
    "stat_num":    ("Segoe UI", 26, "bold"),
    "stat_lbl":    ("Segoe UI", 8, "bold"),
    "btn_large":   ("Segoe UI", 11, "bold"),
    "btn_normal":  ("Segoe UI", 9, "bold"),
    "badge":       ("Segoe UI", 8, "bold"),
    "code":        ("Consolas", 8),
}


def apply_theme(root: tk.Tk) -> ttk.Style:
    """Apply global dark slate theme to ttk style registry."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=COLORS["bg_app"])

    # Global Frame
    style.configure("TFrame", background=COLORS["bg_app"])
    style.configure("Sidebar.TFrame", background=COLORS["bg_sidebar"])
    style.configure("Card.TFrame", background=COLORS["bg_card"])

    # Global Labels
    style.configure(
        "TLabel",
        background=COLORS["bg_app"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )
    style.configure(
        "Sidebar.TLabel",
        background=COLORS["bg_sidebar"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )
    style.configure(
        "SidebarMuted.TLabel",
        background=COLORS["bg_sidebar"],
        foreground=COLORS["text_secondary"],
        font=FONTS["caption"],
    )
    style.configure(
        "Card.TLabel",
        background=COLORS["bg_card"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )
    style.configure(
        "CardMuted.TLabel",
        background=COLORS["bg_card"],
        foreground=COLORS["text_secondary"],
        font=FONTS["caption"],
    )
    style.configure(
        "CardBold.TLabel",
        background=COLORS["bg_card"],
        foreground=COLORS["text_primary"],
        font=FONTS["body_bold"],
    )

    # LabelFrames
    style.configure(
        "Card.TLabelframe",
        background=COLORS["bg_card"],
        foreground=COLORS["text_accent"],
        font=FONTS["section_h"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=COLORS["bg_card"],
        foreground=COLORS["text_accent"],
        font=FONTS["section_h"],
    )

    style.configure(
        "Debug.TLabelframe",
        background=COLORS["bg_input"],
        foreground="#f59e0b",
        font=FONTS["section_h"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Debug.TLabelframe.Label",
        background=COLORS["bg_input"],
        foreground="#f59e0b",
        font=FONTS["section_h"],
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["bg_input"],
        background=COLORS["bg_card"],
        foreground=COLORS["text_primary"],
        arrowcolor=COLORS["text_primary"],
        insertcolor=COLORS["text_primary"],
        font=FONTS["input"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["bg_input"])],
        selectbackground=[("readonly", COLORS["bg_selected"])],
        selectforeground=[("readonly", COLORS["text_primary"])],
    )

    # Checkbutton
    style.configure(
        "Card.TCheckbutton",
        background=COLORS["bg_card"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )
    style.map(
        "Card.TCheckbutton",
        foreground=[("active", COLORS["text_accent"])],
        background=[("active", COLORS["bg_card"])],
    )

    # Buttons
    style.configure(
        "Action.TButton",
        font=FONTS["btn_normal"],
        padding=(10, 5),
    )

    return style
