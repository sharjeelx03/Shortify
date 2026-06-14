#!/usr/bin/env python3
"""Shortify — modern local-first desktop shell."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("CustomTkinter is missing. Run: pip install -r requirements.txt") from exc

from core.providers import provider_ready
from core.settings import (
    APP_NAME,
    APP_VERSION,
    FONT_BODY,
    FONT_SMALL,
    FONT_TITLE,
    GITHUB_URL,
    OUTPUT_DIR,
    PROVIDER_FROM_LABEL,
    PROVIDER_LABELS,
    THEME,
    check_ffmpeg,
    load_settings,
    resource_path,
    save_settings,
)
from ui.components import ToastManager, load_sidebar_logo
from ui.pages.generate import GeneratePageMixin
from ui.pages.library import LibraryPageMixin
from ui.pages.settings_page import SettingsPageMixin
from ui.pages.updates import UpdatesPageMixin

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ShortifyApp(GeneratePageMixin, LibraryPageMixin, SettingsPageMixin, UpdatesPageMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1240x800")
        self.minsize(1080, 720)
        self.configure(fg_color=THEME["bg"])

        icon = resource_path("assets/icon.ico")
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

        self.settings = load_settings()
        self.running = False
        self.current_output_dir: Optional[Path] = None
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self.system_rows: Dict[str, Tuple[ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.provider_field_vars: Dict[str, tk.StringVar] = {}
        self.result_cards: List[Dict[str, Any]] = []
        self.toast_manager = ToastManager(self)
        self.sidebar_logo_image = None

        self._build_shell()
        self.show_page("generate")
        self.refresh_status()
        self.refresh_library()

        if self.settings.get("auto_check_updates", True):
            self.after(1600, self.check_updates_silent)

    # Shell -----------------------------------------------------------------

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, fg_color=THEME["sidebar"], corner_radius=0, width=220)
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
        self.library_page = self._make_library_page(self.pages)
        self.settings_page = self._make_settings_page(self.pages)
        self.updates_page = self._make_updates_page(self.pages)

    def _build_sidebar(self):
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 20))
        brand.grid_columnconfigure(0, weight=1)

        self.sidebar_logo_image = load_sidebar_logo(max_size=64)
        if self.sidebar_logo_image is not None:
            ctk.CTkLabel(brand, text="", image=self.sidebar_logo_image).grid(row=0, column=0, sticky="w", pady=(0, 10))

        ctk.CTkLabel(
            brand,
            text="Shortify",
            text_color=THEME["accent"],
            font=("Segoe UI", 28, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            brand,
            text="Local AI Shorts Generator",
            text_color=THEME["muted"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(2, 0))

        nav_items = [
            ("generate", "Generate", "✦"),
            ("library", "Library", "▣"),
            ("settings", "Settings", "⚙"),
            ("updates", "Updates", "↻"),
        ]
        for row, (key, label, icon_text) in enumerate(nav_items, start=1):
            button = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon_text}  {label}",
                height=44,
                corner_radius=12,
                fg_color="transparent",
                hover_color=THEME["card_2"],
                text_color=THEME["muted"],
                font=("Segoe UI", 14, "bold"),
                anchor="w",
                command=lambda page=key: self.show_page(page),
            )
            button.grid(row=row, column=0, sticky="ew", padx=16, pady=4)
            self.nav_buttons[key] = button

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=8, column=0, sticky="sew", padx=18, pady=22)
        ctk.CTkLabel(footer, text=f"v{APP_VERSION}", text_color=THEME["dim"], font=FONT_SMALL).pack(anchor="w")
        ctk.CTkButton(
            footer,
            text="GitHub Repo",
            height=34,
            fg_color=THEME["card"],
            hover_color=THEME["card_2"],
            text_color=THEME["text"],
            corner_radius=10,
            command=lambda: webbrowser.open(GITHUB_URL),
        ).pack(fill="x", pady=(8, 0))

    def _build_header(self):
        self.header = ctk.CTkFrame(self.main, fg_color="transparent", height=86)
        self.header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))
        self.header.grid_columnconfigure(0, weight=1)

        self.page_title = ctk.CTkLabel(
            self.header, text="Generate Compilation Videos", text_color=THEME["text"], font=FONT_TITLE, anchor="w"
        )
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = ctk.CTkLabel(
            self.header,
            text="Paste a YouTube link and let AI stitch the best viral moments into final videos locally.",
            text_color=THEME["muted"],
            font=FONT_BODY,
            anchor="w",
        )
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.header_provider = ctk.CTkLabel(
            self.header, text="AI: Ollama Local", text_color=THEME["accent"], font=("Segoe UI", 13, "bold")
        )
        self.header_provider.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.header_status = ctk.CTkLabel(
            self.header, text="Checking system...", text_color=THEME["muted"], font=FONT_SMALL
        )
        self.header_status.grid(row=1, column=1, sticky="e", padx=(8, 0), pady=(4, 0))

    def show_page(self, page: str):
        titles = {
            "generate": ("Generate Compilation Videos", "Turn one YouTube video into multiple final MP4s, each stitched from viral moments."),
            "library": ("Library", "Open generated clips with dates, sizes, and saved metadata."),
            "settings": ("Settings", "Only the selected AI provider settings are shown."),
            "updates": ("Updates", "Check GitHub releases and manage app version."),
        }
        for frame in [self.generate_page, self.library_page, self.settings_page, self.updates_page]:
            frame.grid_forget()
        getattr(self, f"{page}_page").grid(row=0, column=0, sticky="nsew")

        for key, button in self.nav_buttons.items():
            if key == page:
                button.configure(fg_color=THEME["accent"], text_color=THEME["bg"], hover_color=THEME["accent_hover"])
            else:
                button.configure(fg_color="transparent", text_color=THEME["muted"], hover_color=THEME["card_2"])

        self.page_title.configure(text=titles[page][0])
        self.page_subtitle.configure(text=titles[page][1])
        if page == "library":
            self.refresh_library()
        if page == "settings":
            self.sync_settings_fields()
            self.render_provider_fields()
        self.refresh_status()

    # Shared state ----------------------------------------------------------

    def show_toast(self, message: str, kind: str = "info", duration_ms: int = 3200):
        self.toast_manager.show(message, kind, duration_ms)

    def set_vertical_crop(self, value: bool, save: bool = True):
        value = bool(value)
        self.settings["vertical_crop"] = value
        if hasattr(self, "vertical_crop_var"):
            self.vertical_crop_var.set(value)
        if hasattr(self, "settings_vertical_crop_var"):
            self.settings_vertical_crop_var.set(value)
        if save:
            save_settings(self.settings)

    def quick_provider_changed(self, label: str):
        provider = PROVIDER_FROM_LABEL.get(label, "ollama")
        self.settings["ai_provider"] = provider
        save_settings(self.settings)
        if hasattr(self, "settings_provider_var"):
            self.settings_provider_var.set(label)
            self.render_provider_fields()
        self.refresh_status()
        self.show_toast(f"AI provider set to {label}.", "info")

    def quick_crop_changed(self):
        self.set_vertical_crop(bool(self.vertical_crop_var.get()), save=True)

    def refresh_status(self):
        def run():
            ffmpeg_ok = check_ffmpeg()
            ready, provider_msg = provider_ready(self.settings)
            output = Path(self.settings.get("output_dir", str(OUTPUT_DIR)))
            output_ok = output.exists() or output.parent.exists()

            rows = {
                "ffmpeg": (ffmpeg_ok, "Ready" if ffmpeg_ok else "Missing"),
                "ai": (ready, provider_msg),
                "output": (output_ok, "Ready" if output_ok else "Missing"),
                "updates": (True, "GitHub"),
            }

            def apply():
                for key, (ok, text) in rows.items():
                    dot, value = self.system_rows[key]
                    dot.configure(text_color=THEME["success"] if ok else THEME["danger"])
                    value.configure(text=text, text_color=THEME["muted"])
                provider = PROVIDER_LABELS.get(self.settings.get("ai_provider", "ollama"), "Ollama Local")
                self.header_provider.configure(text=f"AI: {provider}")
                self.header_status.configure(text="Ready" if ffmpeg_ok and ready else "Needs setup")

            self.after(0, apply)

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = ShortifyApp()
    app.mainloop()
