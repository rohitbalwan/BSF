"""
BackScatter Factor (BSF) Calculation Tool 
Developed for RPAD, Bhabha Atomic Research Centre, India
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
import threading
import os
import sys
import csv
import ctypes
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import AutoMinorLocator
from scipy.interpolate import PchipInterpolator
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS   # PyInstaller temp folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

BEAM_TYPES = [
    "Narrow_Series", "High_Air_Kerma_Rate_Series", "Wide_Series",
    "Low_Air_Kerma_Rate_Series", "Unfiltered_Xrays", "Diagnostic_Beams",
    "Therapy_Beams", "Custom_Spectra",
]

BEAM_OPTIONS_BY_TYPE: dict[str, list[str]] = {
    "Narrow_Series": [
        "N_10","N_15","N_20","N_25","N_30","N_40","N_60","N_80",
        "N_100","N_120","N_150","N_200","N_250","N_300",
    ],
    "High_Air_Kerma_Rate_Series": [
        "H_20","H_30","H_60","H_80","H_100","H_150","H_200","H_250","H_280","H_300",
    ],
    "Wide_Series": [
        "W_30","W_40","W_60","W_80","W_110","W_150","W_200","W_250","W_300",
    ],
    "Low_Air_Kerma_Rate_Series": [
        "L_10","L_20","L_30","L_35","L_55","L_70","L_100","L_125","L_170","L_210","L_240",
    ],
    "Unfiltered_Xrays": [
        "15kVp","20kVp","25kVp","30kVp","35kVp","40kVp","50kVp","55kVp",
        "60kVp","70kVp","80kVp","90kVp","100kVp","110kVp","120kVp",
    ],
    "Diagnostic_Beams": [
        "RQA2","RQA3","RQA4","RQA5","RQA6","RQA7","RQA8","RQA9","RQA10",
        "RQR2","RQR3","RQR4","RQR5","RQR6","RQR7","RQR8","RQR9","RQR10","RQT",
    ],
    "Therapy_Beams": [
        "SH50","SH70","TH70","TH100","TH120","TH140","TW15","TW20","TW30","TW40","TW50","TW75",
    ],
    "Custom_Spectra": ["Custom_Spectra"],
}

BEAM_SIZE_BY_PHANTOM: dict[str, list[str]] = {
    "Slab Phantom":         ["10x10cm", "20x20cm", "30x30cm"],
    "Cylindrical Phantom": ["10x10cm", "20x20cm"],
    "Pillar Phantom":       ["10x10cm", "20x20cm", "30x30cm"],
    "Rod Phantom":          ["10x10cm", "30x30cm"],
}

PHANTOMS = list(BEAM_SIZE_BY_PHANTOM.keys())

COLORS = {
    "bg":       "#0d0d0d",
    "panel":    "#141414",
    "accent":   "#c7ff0f",
    "accent2":  "#fda117",
    "text":     "#e8e8e8",
    "success":  "#c7ff0f",
    "warning":  "#fda117",
    "error":    "#ff4f4f",
    "info":     "#4faaff",
    "border":   "#2a2a2a",
    "plot_bg":  "#0a0a0a",
}

BASE_WINDOW_WIDTH = 1080
BASE_WINDOW_HEIGHT = 700


# ──────────────────────────────────────────────
# Tooltip helper
# ──────────────────────────────────────────────

class Tooltip:
    """Simple, self-contained tooltip."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<Button-1>", self._hide)

    def _show(self, _event=None) -> None:
        if self._tip:
            return
        x = self._widget.winfo_rootx() + 24
        y = self._widget.winfo_rooty() + 24
        self._tip = tk.Toplevel(self._widget)
        self._tip.overrideredirect(True)
        self._tip.geometry(f"+{x}+{y}")
        tk.Label(
            self._tip, text=self._text,
            background="#ffffcc", relief="solid", borderwidth=1,
            font=("Segoe UI", 9), padx=4, pady=2,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ──────────────────────────────────────────────
# Main Application Class
# ──────────────────────────────────────────────

class BSFApp:
    """BackScatter Factor calculation application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._resize_job: str | None = None
        self._is_stacked_layout = False
        self._is_closing = False
        self._configure_root()

        # State
        self.beam_df: pd.DataFrame | None = None
        self.phantom_df: pd.DataFrame | None = None
        self.bsf_value: float | None = None
        self.plot_canvas: FigureCanvasTkAgg | None = None
        self.history: list[dict] = []          # in-session log
        self._calc_thread: threading.Thread | None = None

        self._build_styles()
        self._build_layout()

    # ── Setup ──────────────────────────────────

    def _configure_root(self) -> None:
        self.root.title("BackScatter Factor (BSF) Calculation Tool  |  BARC · RPAD")         # Start in maximized mode (recommended over hard fullscreen)
        self.is_fullscreen = False
        self.root.configure(bg=COLORS["bg"])
        self.root.geometry(f"{BASE_WINDOW_WIDTH}x{BASE_WINDOW_HEIGHT}")
        self.root.minsize(320, 600)
        self._configure_app_icon()
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Configure>", self._on_root_resize)
        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)

    def _configure_app_icon(self) -> None:
        icon_path = resource_path("logo.ico")
        if not os.path.exists(icon_path):
            return

        if sys.platform.startswith("win"):
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "barc.rpad.bsf_tool"
                )
            except Exception:
                pass

            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        if PIL_AVAILABLE:
            try:
                icon_image = Image.open(icon_path)
                self._app_icon = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, self._app_icon)
            except Exception:
                pass

    def _build_styles(self) -> None:
        self.fonts = {
            "header": tkfont.Font(family="Segoe UI Symbol", size=10, weight="bold"),
            "header_meta": tkfont.Font(family="Segoe UI", size=8),
            "label": tkfont.Font(family="Segoe UI", size=8),
            "section": tkfont.Font(family="Segoe UI", size=8, weight="bold"),
            "subheading": tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            "button": tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            "button_small": tkfont.Font(family="Segoe UI", size=8),
            "result": tkfont.Font(family="Segoe UI", size=18, weight="bold"),
            "small": tkfont.Font(family="Segoe UI", size=7),
            "small_link": tkfont.Font(family="Segoe UI", size=7, underline=True),
            "footer": tkfont.Font(family="Segoe UI", size=8, weight="bold"),
        }
        style = ttk.Style()
        style.theme_use("clam")

        combo_cfg = dict(
            fieldbackground=COLORS["bg"],
            background="#1e1e1e",
            foreground=COLORS["text"],
            borderwidth=1,
            relief="flat",
            padding=6,
            font=self.fonts["label"],
        )
        style.configure("BSF.TCombobox", **combo_cfg)
        style.map("BSF.TCombobox",
            fieldbackground=[("readonly", COLORS["bg"])],
            background=[("readonly", "#1e1e1e")],
            foreground=[("readonly", COLORS["text"])],
            arrowcolor=[("active", COLORS["accent"]), ("!disabled", "#888")],
        )

        style.configure("BSF.TFrame", background=COLORS["bg"])
        style.configure("BSF.TLabel",
            background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 12))
        style.configure("Accent.TLabel",
            background=COLORS["bg"], foreground=COLORS["accent"], font=("Segoe UI", 12, "bold"))

    # ── Layout ─────────────────────────────────

    def _build_layout(self) -> None:
        # ── Header ──
        self.hdr = tk.Frame(self.root, bg=COLORS["accent"], height=38)
        self.hdr.pack(fill=tk.X, side=tk.TOP)
        self.header_title = tk.Label(
            self.hdr, text="⚛  BackScatter Factor (BSF) Calculation Tool",
            font=self.fonts["header"], bg=COLORS["accent"], fg=COLORS["bg"],
        )
        self.header_title.pack(side=tk.LEFT, padx=8, pady=6)

        self.fullscreen_btn = tk.Button(
            self.hdr,
            text="Full Screen",
            command=self._toggle_fullscreen,
            font=self.fonts["small"],
            bg=COLORS["bg"],
            fg=COLORS["accent"],
            activebackground="#1a1a1a",
            activeforeground=COLORS["accent"],
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2,
        )
        self.fullscreen_btn.pack(side=tk.RIGHT, padx=(6, 8), pady=4)

        self.header_meta = tk.Label(
            self.hdr, text="BARC · RPAD",
            font=self.fonts["header_meta"], bg=COLORS["accent"], fg=COLORS["bg"],
        )
        self.header_meta.pack(side=tk.RIGHT, padx=(6, 0))

        # ── Main body ──
        self.body = tk.Frame(self.root, bg=COLORS["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 0))

        self._build_left_panel(self.body)
        self._build_right_panel(self.body)
        self._apply_responsive_layout(BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT)

        # ── Status bar ──
        self._status_var = tk.StringVar(value="Ready — select beam parameters and click Calculate.")
        self._status_color = tk.StringVar(value=COLORS["info"])
        sb = tk.Frame(self.root, bg="#0a0a0a", height=28)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_lbl = tk.Label(
            sb, textvariable=self._status_var,
            bg="#0a0a0a", fg=COLORS["info"],
            font=self.fonts["small"], anchor="w", padx=6,
        )
        self._status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._progress = ttk.Progressbar(sb, mode="indeterminate", length=120)
        self._progress.pack(side=tk.RIGHT, padx=8, pady=4)

    def _build_left_panel(self, parent: tk.Frame) -> None:
        lf = tk.Frame(
            parent,
            bg=COLORS["panel"],
            bd=0,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        self.left_panel = lf
        self.left_content = lf

        R = 0  # row counter

        def section_header(text: str, row: int, color=COLORS["accent"]) -> None:
            tk.Label(lf, text=text, fg=color, bg=COLORS["panel"],
                     font=self.fonts["section"]).grid(
                row=row, column=0, sticky="w", padx=10, pady=(6, 1))

        def combo_row(label: str, values: list[str]) -> tuple[ttk.Combobox, int]:
            nonlocal R
            tk.Label(lf, text=label, fg="white", bg=COLORS["panel"],
                     font=self.fonts["label"]).grid(
                row=R, column=0, sticky="w", padx=12, pady=(2, 0)); R += 1
            cb = ttk.Combobox(lf, state="readonly",
                              style="BSF.TCombobox", values=values)
            cb.grid(row=R, column=0, padx=12, pady=(0, 3), sticky="ew"); R += 1
            return cb

        # ── Section heading ──
        tk.Label(lf, text="Beam Parameters", fg=COLORS["accent"],
                 bg=COLORS["panel"], font=self.fonts["subheading"]).grid(
            row=R, column=0, padx=10, pady=(8, 3), sticky="w"); R += 1

        # ── Beam selection group ──
        section_header("① Beam Selection", R); R += 1
        self.combo_type = combo_row("Type of Beam", BEAM_TYPES)
        self.combo_beam = combo_row("Beam", [])

        ttk.Separator(lf, orient="horizontal").grid(
            row=R, column=0, sticky="ew", padx=8, pady=4); R += 1

        # ── Phantom selection group ──
        section_header("② Phantom Selection", R); R += 1
        self.combo_phantom = combo_row("ISO Phantom", PHANTOMS)
        self.combo_size    = combo_row("Beam Size", [])

        # Custom beam section
        tk.Label(lf, text="Custom Beam File", fg=COLORS["accent2"],
                 bg=COLORS["panel"], font=self.fonts["subheading"]).grid(
            row=R, column=0, padx=10, pady=(3, 1), sticky="w"); R += 1
        tk.Label(lf,
            text="(Required only when Custom_Spectra is selected.\n See Readme for file format.)",
            fg="white", bg=COLORS["panel"], font=self.fonts["small"], justify="left",
        ).grid(row=R, column=0, padx=10, sticky="w"); R += 1

        browse_frame = tk.Frame(lf, bg=COLORS["panel"])
        browse_frame.grid(row=R, column=0, padx=10, pady=4, sticky="ew"); R += 1
        self.browse_entry = tk.Entry(
            browse_frame, width=18, font=self.fonts["label"],
            bg=COLORS["bg"], fg=COLORS["text"], insertbackground=COLORS["text"],
            state="disabled", relief="flat",
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        self.browse_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.browse_btn = tk.Button(
            browse_frame, text="…", width=3, font=self.fonts["label"],
            bg="#1e1e1e", fg=COLORS["text"],
            activebackground=COLORS["accent"], activeforeground=COLORS["bg"],
            relief="flat", cursor="hand2", state="disabled",
            command=self._browse_file,
        )
        self.browse_btn.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(self.browse_btn, "Browse for a custom beam fluence file (.FL or .txt)")

        ttk.Separator(lf, orient="horizontal").grid(
            row=R, column=0, sticky="ew", padx=8, pady=6); R += 1

        # Calculate button
        self.calc_btn = tk.Button(
            lf, text="▶  Calculate BSF",
            command=self._on_submit,
            bg=COLORS["accent"], fg=COLORS["bg"],
            activebackground="#dfff4f", activeforeground=COLORS["bg"],
            relief="flat", font=self.fonts["button"],
            cursor="hand2", pady=6,
        )
        self.calc_btn.grid(row=R, column=0, padx=10, pady=3, sticky="ew"); R += 1

        # Save Plot button (disabled until a result exists)
        self.export_plot_btn = self._small_btn(lf, "💾  Save Plot",
                                               self._export_plot, COLORS["info"], state="disabled")
        self.export_plot_btn.grid(row=R, column=0, padx=10, pady=(2, 1), sticky="ew"); R += 1

        history_btn = self._small_btn(lf, "📋 View History", self._show_history, "white")
        history_btn.grid(row=R, column=0, padx=10, pady=(2, 5), sticky="ew"); R += 1

        # ── BSF result display ──
        tk.Label(lf, text="BSF Result", fg=COLORS["accent"],
                 bg=COLORS["panel"], font=self.fonts["section"]).grid(
            row=R, column=0, padx=10, pady=(4, 1), sticky="w"); R += 1
        self.result_var = tk.StringVar(value="—")
        tk.Label(
            lf, textvariable=self.result_var,
            fg=COLORS["accent"], bg=COLORS["panel"],
            font=self.fonts["result"],
        ).grid(row=R, column=0, padx=10, pady=(0, 3), sticky="w"); R += 1

        self.result_detail_var = tk.StringVar(value="")
        self.result_detail_label = tk.Label(
            lf, textvariable=self.result_detail_var,
            fg="white", bg=COLORS["panel"],
            font=self.fonts["small"], justify="left", wraplength=220,
        )
        self.result_detail_label.grid(row=R, column=0, padx=10, pady=(0, 4), sticky="w"); R += 1

        # ── Logo / Footer ──
        footer = tk.Frame(lf, bg=COLORS["panel"])
        footer.grid(row=R, column=0, padx=10, pady=(6, 6), sticky="sw"); R += 1

        if PIL_AVAILABLE:
            try:
                img = Image.open(resource_path("barc_logo.png"))
                img=img.resize((34, 34), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(footer, image=photo, bg=COLORS["panel"])
                logo_lbl.image = photo
                logo_lbl.pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                pass

        org_block = tk.Frame(footer, bg=COLORS["panel"])
        org_block.pack(side=tk.LEFT)

        tk.Label(
            org_block,
            text="Bhabha Atomic Research Centre\nRadiological Physics & Advisory Division",
            fg="white", bg=COLORS["panel"], font=self.fonts["footer"], justify="left",
        ).pack(anchor="w")

        query_frame = tk.Frame(org_block, bg=COLORS["panel"])
        query_frame.pack(anchor="w", pady=(4, 0))

        tk.Label(
            query_frame, text="Query: ",
            fg="white", bg=COLORS["panel"], font=self.fonts["label"],
        ).pack(side=tk.LEFT)

        email_lbl = tk.Label(
            query_frame, text="rohityadav@barc.gov.in",
            fg="#2F6AE7", bg=COLORS["panel"],
            font=self.fonts["small_link"], cursor="hand2",
        )
        email_lbl.pack(side=tk.LEFT)

        def _open_mail(_event=None):
            import webbrowser
            webbrowser.open("mailto:rohityadav@barc.gov.in")

        email_lbl.bind("<Button-1>", _open_mail)
        Tooltip(email_lbl, "Click to send an email query")

        # ── Bind events ──
        self.combo_type.bind("<<ComboboxSelected>>",    self._on_type_changed)
        self.combo_beam.bind("<<ComboboxSelected>>",    self._on_beam_changed)
        self.combo_phantom.bind("<<ComboboxSelected>>", self._on_phantom_changed)

    def _build_right_panel(self, parent: tk.Frame) -> None:
        rf = tk.Frame(parent, bg=COLORS["bg"])
        self.right_panel = rf
        rf.rowconfigure(0, weight=1)
        rf.columnconfigure(0, weight=1)

        # Plot area
        plot_border = tk.Frame(
            rf, bg=COLORS["plot_bg"],
            highlightbackground=COLORS["accent"], highlightthickness=1,
        )
        plot_border.grid(row=0, column=0, sticky="nsew")
        plot_border.rowconfigure(0, weight=1)
        plot_border.columnconfigure(0, weight=1)

        self.plot_frame = tk.Frame(plot_border, bg=COLORS["plot_bg"])
        self.plot_frame.grid(row=0, column=0, sticky="nsew")

        # Placeholder label shown before first calculation
        self.placeholder_lbl = tk.Label(
            self.plot_frame,
            text="Select beam parameters and click\n▶ Calculate BSF\nto display the spectrum.",
            fg="white", bg=COLORS["plot_bg"],
            font=self.fonts["subheading"],
        )
        self.placeholder_lbl.pack(expand=True)

    # ── Helpers ────────────────────────────────

    def _small_btn(self, parent: tk.Frame, text: str,
                   cmd, color: str, state="normal") -> tk.Button:
        return tk.Button(
            parent, text=text, command=cmd,
            bg="#1a1a1a", fg=color,
            activebackground="#262626", activeforeground=color,
            relief="flat", font=self.fonts["button_small"],
            cursor="hand2", pady=4, state=state,
        )

    def _on_root_resize(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(80, self._update_responsive_ui)

    def _update_responsive_ui(self) -> None:
        self._resize_job = None
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        self._apply_responsive_layout(width, height)
        self._apply_font_scaling(width, height)
        self.result_detail_label.config(wraplength=max(180, self.left_content.winfo_width() - 40))

    def _apply_responsive_layout(self, width: int, height: int) -> None:
        stacked = width < 900
        if stacked != self._is_stacked_layout:
            self.left_panel.grid_forget()
            self.right_panel.grid_forget()
            for col in range(2):
                self.body.columnconfigure(col, weight=0)
            for row in range(2):
                self.body.rowconfigure(row, weight=0)

            if stacked:
                self.left_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
                self.right_panel.grid(row=1, column=0, sticky="nsew")
                self.body.columnconfigure(0, weight=1)
                self.body.rowconfigure(0, weight=1)
                self.body.rowconfigure(1, weight=0)
            else:
                self.left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 8), pady=2)
                self.right_panel.grid(row=0, column=1, sticky="nsew", pady=2)
                self.body.columnconfigure(0, weight=0)
                self.body.columnconfigure(1, weight=1)
                self.body.rowconfigure(0, weight=1)

            self._is_stacked_layout = stacked

        plot_height = max(130, int(height * (0.23 if stacked else 0.65)))
        self.plot_frame.configure(height=plot_height)
        self.fullscreen_btn.config(text="Windowed" if self.is_fullscreen else "Full Screen")

    def _apply_font_scaling(self, width: int, height: int) -> None:
        scale = min(width / BASE_WINDOW_WIDTH, height / BASE_WINDOW_HEIGHT)
        clamped = max(0.8, min(scale, 1.25))
        sizes = {
            "header": max(9, round(10 * clamped)),
            "header_meta": max(7, round(8 * clamped)),
            "label": max(7, round(8 * clamped)),
            "section": max(7, round(8 * clamped)),
            "subheading": max(9, round(10 * clamped)),
            "button": max(9, round(10 * clamped)),
            "button_small": max(7, round(8 * clamped)),
            "result": max(16, round(18 * clamped)),
            "small": max(6, round(7 * clamped)),
            "small_link": max(6, round(7 * clamped)),
            "footer": max(7, round(8 * clamped)),
        }
        for key, size in sizes.items():
            self.fonts[key].configure(size=size)

    def _set_status(self, msg: str, kind: str = "info") -> None:
        """Thread-safe status bar update."""
        if self._is_closing or not self.root.winfo_exists():
            return
        color_map = {
            "info":    COLORS["info"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error":   COLORS["error"],
        }
        color = color_map.get(kind, COLORS["info"])
        self.root.after(0, lambda: (
            self._status_var.set(msg),
            self._status_lbl.config(fg=color),
        ))

    # ── Combo event handlers ────────────────────

    def _on_type_changed(self, _event=None) -> None:
        t = self.combo_type.get()
        opts = BEAM_OPTIONS_BY_TYPE.get(t, [])
        self.combo_beam["values"] = opts
        self.combo_beam.set(opts[0] if opts else "")
        self._on_beam_changed()

    def _on_beam_changed(self, _event=None) -> None:
        is_custom = self.combo_beam.get() == "Custom_Spectra"
        state = "normal" if is_custom else "disabled"
        self.browse_entry.config(state=state)
        self.browse_btn.config(state=state)
        if not is_custom:
            self.browse_entry.config(state="normal")
            self.browse_entry.delete(0, tk.END)
            self.browse_entry.config(state="disabled")

    def _on_phantom_changed(self, _event=None) -> None:
        p = self.combo_phantom.get()
        opts = BEAM_SIZE_BY_PHANTOM.get(p, [])
        self.combo_size["values"] = opts
        self.combo_size.set(opts[0] if opts else "")

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select custom beam fluence file",
            filetypes=[("Beam files", "*.FL *.txt *.dat"), ("All files", "*.*")],
        )
        if path:
            self.browse_entry.config(state="normal")
            self.browse_entry.delete(0, tk.END)
            self.browse_entry.insert(0, path)
            self.browse_entry.config(state="readonly")

    # ── Validation ─────────────────────────────

    def _validate_inputs(self) -> tuple[bool, str]:
        """Return (ok, error_message)."""
        for label, cb in [
            ("Type of Beam", self.combo_type),
            ("Beam", self.combo_beam),
            ("ISO Phantom", self.combo_phantom),
            ("Beam Size", self.combo_size),
        ]:
            if not cb.get():
                return False, f"Please select a value for: {label}"

        if self.combo_beam.get() == "Custom_Spectra":
            path = self.browse_entry.get()
            if not path:
                return False, "Please browse and select a custom beam file."
            if not os.path.exists(path):
                return False, f"Custom beam file not found:\n{path}"

        return True, ""

    def _resolve_file_paths(self) -> tuple[str, str]:
        """Return (beam_file_path, phantom_file_path)."""
        beam_type = self.combo_type.get()
        beam      = self.combo_beam.get()
        phantom   = self.combo_phantom.get()
        size      = self.combo_size.get()

        sanitized_phantom = phantom.replace(" ", "_")

        if beam == "Custom_Spectra":
            beam_path = self.browse_entry.get()
        else:
            beam_path = resource_path(os.path.join("beam_data", beam_type, f"{beam}.FL"))

        phantom_path = resource_path(os.path.join("bsf_data", sanitized_phantom, f"{size}.txt"))
        return beam_path, phantom_path

    # ── Calculation (runs in thread) ────────────

    def _on_submit(self) -> None:
        ok, msg = self._validate_inputs()
        if not ok:
            self._set_status(f"⚠  {msg}", "warning")
            return

        # Prevent double-click during run
        if self._calc_thread and self._calc_thread.is_alive():
            return

        self.calc_btn.config(state="disabled")
        self._progress.start(12)
        self._set_status("Loading and processing files…", "info")

        self._calc_thread = threading.Thread(target=self._calculate, daemon=True)
        self._calc_thread.start()

    def _calculate(self) -> None:
        """Runs in background thread — post results back via root.after()."""
        try:
            beam_path, phantom_path = self._resolve_file_paths()

            missing = []
            if not os.path.exists(beam_path):
                missing.append(f"Beam file: {beam_path}")
            if not os.path.exists(phantom_path):
                missing.append(f"Phantom file: {phantom_path}")
            if missing:
                self._queue_on_main(lambda m=missing: self._on_error(
                    "Missing files:\n" + "\n".join(m)))
                return

            # ── Read files ──
            beam_df = pd.read_csv(
                beam_path, sep=r"\s+", comment="#",
                header=None, dtype=str,
            ).apply(pd.to_numeric, errors="coerce").dropna()

            phantom_df = pd.read_csv(
                phantom_path, sep=r"\s+", comment="#",
                header=None, dtype=str,
            ).apply(pd.to_numeric, errors="coerce").dropna()

            if beam_df.shape[1] < 2:
                self._queue_on_main(lambda: self._on_error(
                    "Beam file must have at least 2 columns: Energy, Fluence."))
                return

            if phantom_df.shape[1] < 2:
                self._queue_on_main(lambda: self._on_error(
                    "Phantom file must have at least 2 columns: Energy, BSF."))
                return

            # ── Compute BSF ──
            total = beam_df[1].sum()
            if total == 0:
                raise ValueError("Beam fluence sum is zero. Cannot normalize.")
            
            beam_df["norm"] = beam_df[1] / beam_df[1].sum()
            interp = PchipInterpolator(phantom_df[0], phantom_df[1], extrapolate=True)
            beam_df["bsf"]   = interp(beam_df[0])
            beam_df["final"] = beam_df["bsf"] * beam_df["norm"]
            bsf_value        = float(beam_df["final"].sum())

            # Store state
            self.beam_df    = beam_df
            self.phantom_df = phantom_df
            self.bsf_value  = bsf_value

            # Schedule UI update on main thread
            self._queue_on_main(self._on_success)

        except Exception as exc:
            self._queue_on_main(lambda e=exc: self._on_error(f"Calculation error:\n{e}"))

    # ── Post-calculation UI updates (main thread) ──

    def _on_success(self) -> None:
        beam    = self.combo_beam.get()
        phantom = self.combo_phantom.get()
        size    = self.combo_size.get()

        self.result_var.set(f"{self.bsf_value:.4f}")
        self.result_detail_var.set(
            f"Beam: {beam}\nPhantom: {phantom}  |  Size: {size}"
        )

        # Add to history
        self.history.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "beam":      beam,
            "phantom":   phantom,
            "size":      size,
            "bsf":       f"{self.bsf_value:.4f}",
        })

        self._draw_plot()
        self._set_status(
            f"✔  BSF calculated successfully for {beam} — BSF = {self.bsf_value:.4f}",
            "success",
        )
        self.export_plot_btn.config(state="normal")
        self._reset_controls()

    def _on_error(self, msg: str) -> None:
        if self._is_closing or not self.root.winfo_exists():
            return
        self._progress.stop()   # <-- ADD THIS LINE (fix crash)
        self._set_status(f"✖  {msg.splitlines()[0]}", "error")
        messagebox.showerror("Error", msg, parent=self.root)
        self._reset_controls()

    def _reset_controls(self) -> None:
        if self._is_closing or not self.root.winfo_exists():
            return
        self._progress.stop()
        self.calc_btn.config(state="normal")

    def _queue_on_main(self, callback) -> None:
        if self._is_closing:
            return
        try:
            if self.root.winfo_exists():
                self.root.after(0, callback)
        except tk.TclError:
            pass

    def _shutdown(self) -> None:
        if self._is_closing:
            return
        self._is_closing = True

        try:
            self._progress.stop()
        except Exception:
            pass

        try:
            if self._resize_job is not None and self.root.winfo_exists():
                self.root.after_cancel(self._resize_job)
                self._resize_job = None
        except tk.TclError:
            pass

        try:
            plt.close("all")
        except Exception:
            pass

        try:
            for child in list(self.root.winfo_children()):
                if isinstance(child, tk.Toplevel):
                    child.destroy()
        except tk.TclError:
            pass

        try:
            self.root.quit()
        except tk.TclError:
            pass

        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ── Plot ────────────────────────────────────

    def _draw_plot(self) -> None:
        assert self.beam_df is not None

        # Clear previous
        if self.plot_canvas:
            self.plot_canvas.get_tk_widget().destroy()
            self.plot_canvas = None
        if hasattr(self, "fig") and self.fig:
            plt.close(self.fig)
            self.fig = None
        self.placeholder_lbl.pack_forget()

        # constrained_layout ensures axis labels / tick labels never get clipped
        fig, ax = plt.subplots(figsize=(8, 4.8), dpi=100,
                               constrained_layout=True)
        self.fig = fig                          # keep reference for saving
        fig.patch.set_facecolor(COLORS["plot_bg"])
        ax.set_facecolor(COLORS["plot_bg"])

        ax.plot(
            self.beam_df[0], self.beam_df["norm"],
            marker="o", color=COLORS["accent"],
            linestyle="-", linewidth=2, markersize=4,
            label="Normalised Fluence",
        )


        beam_label = self.combo_beam.get()
        ax.set_title(f"{beam_label} — Normalised Fluence Spectrum",
                     fontsize=13, color="white", pad=10)
        ax.set_xlabel("Energy (keV)", fontsize=12, color="white", labelpad=8)
        ax.set_ylabel("Normalised Fluence", fontsize=12, color=COLORS["accent"],
                      labelpad=8)
        ax.tick_params(axis="both", colors="white", direction="in", length=6, which="major")
        ax.tick_params(axis="both", colors="white", direction="in", length=3, which="minor")
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.minorticks_on()
        ax.grid(which="major", linestyle="--", alpha=0.35, color="#444")
        ax.grid(which="minor", linestyle=":", alpha=0.2, color="#333")

        for spine in ax.spines.values():
            spine.set_edgecolor("#3a3a1a")
            spine.set_linewidth(1.5)

        # Legend combining both axes
        ax.legend(
         loc="upper right", fontsize=9,
         facecolor="#111", edgecolor="#333", labelcolor="white",
         )

        # BSF annotation
        ax.annotate(
            f"  BSF = {self.bsf_value:.4f}",
            xy=(0.02, 0.95), xycoords="axes fraction",
            fontsize=12, color=COLORS["accent"],
            fontweight="bold",
        )

        self.plot_canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # Note: fig is intentionally NOT closed here so it can be saved later

    # ── Export ──────────────────────────────────

    def _export_plot(self) -> None:
        """Open an advanced plot-export dialog with format, DPI, background and transparency options."""
        if not self.plot_canvas:
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Save Plot — Options")
        dlg.configure(bg=COLORS["bg"])
        dlg.resizable(False, False)
        dlg.grab_set()

        # ── centre on parent ──
        dlg.update_idletasks()
        px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
        dlg.geometry(f"380x420+{px+180}+{py+140}")

        def row_label(parent, text, r):
            tk.Label(parent, text=text, fg="white", bg=COLORS["bg"],
                     font=("Segoe UI", 10)).grid(row=r, column=0, sticky="w",
                                                  padx=18, pady=(10, 2))

        f = tk.Frame(dlg, bg=COLORS["bg"])
        f.pack(fill=tk.BOTH, expand=True)

        tk.Label(f, text="Plot Export Options", fg=COLORS["accent"],
                 bg=COLORS["bg"], font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=2, padx=18, pady=(14, 4), sticky="w")

        # Format
        row_label(f, "File Format", 1)
        fmt_var = tk.StringVar(value="PNG")
        fmt_frame = tk.Frame(f, bg=COLORS["bg"])
        fmt_frame.grid(row=2, column=0, columnspan=2, padx=18, sticky="w")
        for fmt in ["PNG", "PDF", "SVG", "EPS", "TIFF"]:
            tk.Radiobutton(fmt_frame, text=fmt, variable=fmt_var, value=fmt,
                           bg=COLORS["bg"], fg="white", selectcolor="#1e1e1e",
                           activebackground=COLORS["bg"], activeforeground=COLORS["accent"],
                           font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))

        # DPI
        row_label(f, "Resolution (DPI)", 3)
        dpi_var = tk.StringVar(value="150")
        dpi_frame = tk.Frame(f, bg=COLORS["bg"])
        dpi_frame.grid(row=4, column=0, columnspan=2, padx=18, sticky="w")
        for dpi in ["72", "100", "150", "300", "600"]:
            tk.Radiobutton(dpi_frame, text=dpi, variable=dpi_var, value=dpi,
                           bg=COLORS["bg"], fg="white", selectcolor="#1e1e1e",
                           activebackground=COLORS["bg"], activeforeground=COLORS["accent"],
                           font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))

        # Background
        row_label(f, "Background", 5)
        bg_var = tk.StringVar(value="dark")
        bg_frame = tk.Frame(f, bg=COLORS["bg"])
        bg_frame.grid(row=6, column=0, columnspan=2, padx=18, sticky="w")
        for label, val in [("Dark (default)", "dark"), ("White", "white"), ("Transparent", "transparent")]:
            tk.Radiobutton(bg_frame, text=label, variable=bg_var, value=val,
                           bg=COLORS["bg"], fg="white", selectcolor="#1e1e1e",
                           activebackground=COLORS["bg"], activeforeground=COLORS["accent"],
                           font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))

        # Add watermark
        watermark_var = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Add BARC·RPAD watermark text", variable=watermark_var,
                       bg=COLORS["bg"], fg="white", selectcolor="#1e1e1e",
                       activebackground=COLORS["bg"], activeforeground=COLORS["accent"],
                       font=("Segoe UI", 10)).grid(
            row=8, column=0, columnspan=2, padx=18, pady=(6, 0), sticky="w")

        def do_save():
            fmt = fmt_var.get().lower()
            ext_map = {"tiff": "tif"}
            ext = ext_map.get(fmt, fmt)
            path = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                filetypes=[(f"{fmt.upper()} file", f"*.{ext}"), ("All files", "*.*")],
                title="Save Plot",
                parent=dlg,
            )
            if not path:
                return
            try:
                fig = self.fig
                bg_choice = bg_var.get()
                fc = {"dark": COLORS["plot_bg"], "white": "white", "transparent": "none"}[bg_choice]
                transparent = bg_choice == "transparent"

                wm = None
                if watermark_var.get():
                    wm = fig.text(0.99, 0.01, "BARC · RPAD",
                                  ha="right", va="bottom", fontsize=8,
                                  color="#888", alpha=0.6)

                fig.savefig(
                    path,
                    dpi=int(dpi_var.get()),
                    facecolor=fc,
                    transparent=transparent,
                    format=fmt,
                    bbox_inches="tight",   # always tight — ensures all labels fully visible
                    pad_inches=0.15,       # small padding so labels don't touch the edge
                )

                if wm is not None:
                    wm.remove()
                    self.plot_canvas.draw()

                dlg.destroy()
                self._set_status(
                    f"✔  Plot saved → {os.path.basename(path)}  "
                    f"({fmt.upper()}, {dpi_var.get()} DPI)", "success")
            except Exception as e:
                messagebox.showerror("Export Error", str(e), parent=dlg)

        btn_row = tk.Frame(f, bg=COLORS["bg"])
        btn_row.grid(row=9, column=0, columnspan=2, pady=18)
        tk.Button(btn_row, text="💾  Save", command=do_save,
                  bg=COLORS["accent"], fg=COLORS["bg"],
                  font=("Segoe UI", 11, "bold"), relief="flat",
                  cursor="hand2", padx=20, pady=6).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_row, text="Cancel", command=dlg.destroy,
                  bg="#1e1e1e", fg="white",
                  font=("Segoe UI", 11), relief="flat",
                  cursor="hand2", padx=14, pady=6).pack(side=tk.LEFT)

    # ── History window ──────────────────────────

    def _show_history(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Calculation History (this session)")
        win.geometry("640x360")
        win.configure(bg=COLORS["bg"])

        cols = ("Time", "Beam", "Phantom", "Size", "BSF")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")

        style = ttk.Style()
        style.configure("Treeview",
            background=COLORS["panel"], foreground=COLORS["text"],
            fieldbackground=COLORS["panel"], rowheight=24,
        )
        style.configure("Treeview.Heading",
            background="#1e1e1e", foreground=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
        )

        for row in self.history:
            tree.insert("", tk.END, values=(
                row["timestamp"], row["beam"], row["phantom"], row["size"], row["bsf"],
            ))

        sb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=10, padx=(0, 10))

        if not self.history:
            tk.Label(
                win, text="No calculations yet.",
                fg="white", bg=COLORS["bg"], font=("Segoe UI", 12),
            ).place(relx=0.5, rely=0.5, anchor="center")

        # Export history button
        def export_history():
            p = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV file", "*.csv")],
                parent=win,
            )
            if p:
                with open(p, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["timestamp","beam","phantom","size","bsf"])
                    w.writeheader()
                    w.writerows(self.history)

        tk.Button(
            win, text="Export history as CSV", command=export_history,
            bg=COLORS["accent"], fg=COLORS["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat",
            cursor="hand2", padx=8, pady=4,
        ).pack(pady=(0, 10))

    def _toggle_fullscreen(self, event=None):
        """Toggle between fullscreen and normal window."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            if sys.platform.startswith("win"):
                self.root.state("zoomed")
            else:
                self.root.attributes("-zoomed", True)
        else:
            if not sys.platform.startswith("win"):
                self.root.attributes("-zoomed", False)
            self.root.state("normal")
            self.root.geometry(f"{BASE_WINDOW_WIDTH}x{BASE_WINDOW_HEIGHT}")
        self._update_responsive_ui()


    def _exit_fullscreen(self, event=None):
        """Exit fullscreen (ESC key)."""
        self.is_fullscreen = False
        if not sys.platform.startswith("win"):
            self.root.attributes("-zoomed", False)
        self.root.state("normal")
        self.root.geometry(f"{BASE_WINDOW_WIDTH}x{BASE_WINDOW_HEIGHT}")
        self._update_responsive_ui()

# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main() -> None:
    root = tk.Tk()
    app = BSFApp(root)
    # Centre window on screen
    root.update_idletasks()
    w, h = BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    root.mainloop()


if __name__ == "__main__":
    main()
