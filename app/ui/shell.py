#!/usr/bin/env python3
from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("CustomTkinter missing. Run: pip install -r requirements.txt") from exc

from app.core.providers import provider_ready
from app.core.settings import (
    APP_NAME, APP_VERSION, FONT_SMALL,
    GITHUB_URL, OUTPUT_DIR,
    PROVIDER_FROM_LABEL, PROVIDER_LABELS,
    SOCIAL_LINKS, THEME,
    check_ffmpeg, load_settings, resource_path, save_settings,
)
from app.ui.components import LoadingOverlay, ToastManager, load_sidebar_logo
from app.ui.pages.generate      import GeneratePageMixin
from app.ui.pages.library       import LibraryPageMixin
from app.ui.pages.settings_page import SettingsPageMixin
from app.ui.pages.updates       import UpdatesPageMixin

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ShortifyApp(GeneratePageMixin, LibraryPageMixin, SettingsPageMixin, UpdatesPageMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1260x820")
        self.minsize(1080, 720)
        self.configure(fg_color=THEME["bg"])

        icon = resource_path("assets/icon.ico")
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

        self.settings:            Dict[str, Any]  = load_settings()
        self.running:             bool             = False
        self.current_output_dir:  Optional[Path]  = None
        self.nav_buttons:         Dict[str, ctk.CTkButton] = {}
        self.system_rows:         Dict[str, Tuple] = {}
        self.provider_field_vars: Dict[str, tk.StringVar]  = {}
        self.result_cards:        List[Dict[str, Any]] = []
        self.sidebar_logo_image   = None

        self.toast_manager   = ToastManager(self)
        self.loading_overlay = LoadingOverlay(self, on_cancel=self.stop_pipeline)

        self._build_shell()
        self.show_page("generate")
        self.refresh_status()
        self.refresh_library()

        if self.settings.get("auto_check_updates", True):
            self.after(1600, self.check_updates_silent)

    # ── Shell ───────────────────────────────────────────────────────────────

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, fg_color=THEME["sidebar"], corner_radius=0, width=224)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(7, weight=1)

        self.main = ctk.CTkFrame(self, fg_color=THEME["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_header()

        self.pages = ctk.CTkFrame(self.main, fg_color="transparent")
        self.pages.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.pages.grid_columnconfigure(0, weight=1)
        self.pages.grid_rowconfigure(0, weight=1)

        self.generate_page = self._make_generate_page(self.pages)
        self.library_page  = self._make_library_page(self.pages)
        self.settings_page = self._make_settings_page(self.pages)
        self.updates_page  = self._make_updates_page(self.pages)

    def _build_sidebar(self):
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 20))
        brand.grid_columnconfigure(0, weight=1)

        self.sidebar_logo_image = load_sidebar_logo(max_size=56)
        if self.sidebar_logo_image is not None:
            ctk.CTkLabel(brand, text="", image=self.sidebar_logo_image).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ctk.CTkLabel(brand, text="Shortify", text_color=THEME["accent"],
                     font=("Segoe UI", 26, "bold")).grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(brand, text="Local AI Shorts Generator", text_color=THEME["dim"],
                     font=FONT_SMALL).grid(row=2, column=0, sticky="w")

        ctk.CTkFrame(self.sidebar, fg_color=THEME["border"], height=1).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        nav_items = [
            ("generate", "⚡  Generate"),
            ("library",  "📁  Library"),
            ("settings", "⚙  Settings"),
            ("updates",  "↑  Updates"),
        ]
        for i, (key, label) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w", height=44, corner_radius=10,
                fg_color="transparent", hover_color=THEME["card_2"],
                text_color=THEME["muted"], font=("Segoe UI", 14),
                command=lambda k=key: self.show_page(k),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=12, pady=2)
            self.nav_buttons[key] = btn

        # row 7 = spacer (weight=1 set above)

        ctk.CTkFrame(self.sidebar, fg_color=THEME["border"], height=1).grid(
            row=8, column=0, sticky="ew", padx=16, pady=(8, 8))

        social_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        social_frame.grid(row=9, column=0, sticky="ew", padx=12, pady=(0, 16))
        social_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(social_frame, text="Follow & Support", text_color=THEME["dim"],
                     font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=6, pady=(0, 4))

        icons = {"GitHub": "🐙", "YouTube": "▶", "Instagram": "📸"}
        for name, url in SOCIAL_LINKS.items():
            ctk.CTkButton(
                social_frame, text=f"{icons.get(name, '•')}  {name}",
                height=32, anchor="w", corner_radius=8,
                fg_color="transparent", hover_color=THEME["card_2"],
                text_color=THEME["muted"], font=("Segoe UI", 12),
                command=lambda u=url: webbrowser.open(u),
            ).pack(fill="x", pady=1)

    def _build_header(self):
        header = ctk.CTkFrame(self.main, fg_color=THEME["sidebar"], corner_radius=0, height=54)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)
        self.header_title = ctk.CTkLabel(header, text="Generate", anchor="w",
                                         text_color=THEME["text"], font=("Segoe UI", 18, "bold"))
        self.header_title.grid(row=0, column=0, sticky="ew", padx=28, pady=14)
        ctk.CTkLabel(header, text=f"v{APP_VERSION}", anchor="e",
                     text_color=THEME["dim"], font=FONT_SMALL).grid(row=0, column=1, sticky="e", padx=20)

    # ── Navigation ──────────────────────────────────────────────────────────

    def show_page(self, key: str):
        pages  = {"generate": self.generate_page, "library": self.library_page,
                  "settings": self.settings_page, "updates":  self.updates_page}
        titles = {"generate": "Generate", "library": "Library",
                  "settings": "Settings", "updates":  "Updates"}
        for page in pages.values():
            page.grid_remove()
        if key in pages:
            pages[key].grid(row=0, column=0, sticky="nsew")
        if hasattr(self, "header_title"):
            self.header_title.configure(text=titles.get(key, key.title()))
        for nav_key, btn in self.nav_buttons.items():
            btn.configure(fg_color=THEME["card"] if nav_key == key else "transparent",
                          text_color=THEME["accent"] if nav_key == key else THEME["muted"])

    # ── Status ──────────────────────────────────────────────────────────────

    def refresh_status(self):
        def _run():
            ffmpeg_ok = check_ffmpeg()
            ready, ai_msg = provider_ready(self.settings)
            output_ok = Path(self.settings.get("output_dir", str(OUTPUT_DIR))).exists()
            self.after(0, lambda: self._apply_status(ffmpeg_ok, ready, ai_msg, output_ok))
        threading.Thread(target=_run, daemon=True).start()

    def _apply_status(self, ffmpeg_ok, ai_ok, ai_msg, output_ok):
        col = {True: THEME["success"], False: THEME["danger"]}
        txt = {True: "Ready", False: "Not found"}
        for key, ok, msg in [
            ("ffmpeg", ffmpeg_ok, txt[ffmpeg_ok]),
            ("ai",     ai_ok,     (ai_msg or ("Ready" if ai_ok else "Not configured"))[:28]),
            ("output", output_ok, "Set" if output_ok else "Missing"),
        ]:
            if key in self.system_rows:
                dot, val = self.system_rows[key]
                dot.configure(text_color=col[ok])
                val.configure(text=msg)
        if "updates" in self.system_rows:
            self.system_rows["updates"][0].configure(text_color=THEME["muted"])
            self.system_rows["updates"][1].configure(text="See Updates tab")

    # ── Settings sync ────────────────────────────────────────────────────────

    def quick_provider_changed(self, label: str):
        self.settings["ai_provider"] = PROVIDER_FROM_LABEL.get(label, "ollama")
        save_settings(self.settings)
        self.refresh_status()

    def quick_crop_changed(self):
        if hasattr(self, "crop_mode_var"):
            from app.core.settings import CROP_MODE_KEYS
            self.settings["crop_mode"] = CROP_MODE_KEYS.get(self.crop_mode_var.get(), "auto")
            save_settings(self.settings)

    def quick_resolution_changed(self, label: str):
        self.settings["download_resolution"] = label
        save_settings(self.settings)

    def quick_subtitles_changed(self):
        if hasattr(self, "burn_subtitles_var"):
            self.settings["burn_subtitles"] = bool(self.burn_subtitles_var.get())
            save_settings(self.settings)

    def set_vertical_crop(self, value: bool, save: bool = True):
        """Legacy compat — old settings_page calls this."""
        self.settings["crop_mode"] = "force_vertical" if value else "auto"
        if save:
            save_settings(self.settings)

    def set_burn_subtitles(self, value: bool, save: bool = True):
        self.settings["burn_subtitles"] = value
        if save:
            save_settings(self.settings)

    # ── Toast ────────────────────────────────────────────────────────────────

    def show_toast(self, message: str, kind: str = "info", duration_ms: int = 3400):
        self.toast_manager.show(message, kind, duration_ms)