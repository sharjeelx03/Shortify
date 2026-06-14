from __future__ import annotations

import threading
from typing import Any, Dict

import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

from core.providers import test_provider_connection
from core.settings import (
    DEFAULT_SETTINGS,
    FONT_H2,
    FONT_SMALL,
    OUTPUT_DIR,
    PROVIDER_FROM_LABEL,
    PROVIDER_LABELS,
    THEME,
    save_settings,
)
from ui.components import make_card


class SettingsPageMixin:
    def _make_settings_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        provider_card = make_card(scroll)
        provider_card.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        provider_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(provider_card, text="AI Provider", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=22, pady=(18, 4)
        )
        ctk.CTkLabel(
            provider_card,
            text="Only the selected provider fields appear here.",
            text_color=THEME["muted"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22)

        self.settings_provider_var = tk.StringVar(value=PROVIDER_LABELS.get(self.settings["ai_provider"], "Ollama Local"))
        provider_menu = ctk.CTkOptionMenu(
            provider_card,
            values=list(PROVIDER_LABELS.values()),
            variable=self.settings_provider_var,
            height=42,
            fg_color=THEME["card_2"],
            button_color=THEME["card_2"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card"],
            dropdown_hover_color=THEME["card_2"],
            command=lambda _value: self.render_provider_fields(),
        )
        provider_menu.grid(row=2, column=0, sticky="ew", padx=22, pady=(14, 12))

        self.provider_dynamic = ctk.CTkFrame(provider_card, fg_color="transparent")
        self.provider_dynamic.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 12))
        self.provider_dynamic.grid_columnconfigure(0, weight=1)

        self.test_result_label = ctk.CTkLabel(provider_card, text="", text_color=THEME["muted"], font=FONT_SMALL, anchor="w")
        self.test_result_label.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 12))

        button_row = ctk.CTkFrame(provider_card, fg_color="transparent")
        button_row.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 20))
        button_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            button_row,
            text="Test Connection",
            height=42,
            corner_radius=12,
            fg_color=THEME["card_2"],
            hover_color=THEME["border"],
            text_color=THEME["text"],
            command=self.test_selected_provider,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            button_row,
            text="Save Provider Settings",
            height=42,
            corner_radius=12,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["bg"],
            command=self.save_settings_from_ui,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        app_card = make_card(scroll)
        app_card.grid(row=1, column=0, sticky="ew")
        app_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(app_card, text="App Settings", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=22, pady=(18, 8)
        )
        self.output_dir_var = tk.StringVar(value=str(self.settings.get("output_dir", OUTPUT_DIR)))
        self._settings_entry(app_card, "Output Folder", self.output_dir_var, 1, browse=True)
        self.auto_updates_var = tk.BooleanVar(value=bool(self.settings.get("auto_check_updates", True)))
        self.settings_vertical_crop_var = tk.BooleanVar(value=bool(self.settings.get("vertical_crop", True)))
        ctk.CTkSwitch(
            app_card,
            text="Auto-check for GitHub updates on startup",
            variable=self.auto_updates_var,
            progress_color=THEME["accent"],
            text_color=THEME["text"],
        ).grid(row=3, column=0, sticky="w", padx=22, pady=(10, 4))
        ctk.CTkSwitch(
            app_card,
            text="Export clips as vertical 9:16 Shorts by default",
            variable=self.settings_vertical_crop_var,
            progress_color=THEME["accent"],
            text_color=THEME["text"],
            command=lambda: self.set_vertical_crop(bool(self.settings_vertical_crop_var.get()), save=False),
        ).grid(row=4, column=0, sticky="w", padx=22, pady=(4, 12))
        ctk.CTkButton(
            app_card,
            text="Save App Settings",
            height=42,
            corner_radius=12,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["bg"],
            command=self.save_settings_from_ui,
        ).grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 20))

        self._init_provider_vars()
        self.render_provider_fields()
        return page

    def _init_provider_vars(self):
        for key, default in DEFAULT_SETTINGS.items():
            if key.endswith("_url") or key.endswith("_model") or key.endswith("_api_key"):
                self.provider_field_vars[key] = tk.StringVar(value=str(self.settings.get(key, default)))

    def _settings_entry(self, parent, label: str, variable: tk.StringVar, row: int, browse: bool = False, secret: bool = False):
        ctk.CTkLabel(parent, text=label, text_color=THEME["muted"], font=FONT_SMALL, anchor="w").grid(
            row=row * 2 - 1, column=0, sticky="ew", padx=22, pady=(10, 4)
        )
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.grid(row=row * 2, column=0, sticky="ew", padx=22, pady=(0, 6))
        wrapper.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(
            wrapper,
            textvariable=variable,
            show="•" if secret else "",
            height=42,
            fg_color=THEME["bg"],
            border_color=THEME["border"],
            corner_radius=12,
            text_color=THEME["text"],
        )
        entry.grid(row=0, column=0, sticky="ew")
        if browse:
            ctk.CTkButton(
                wrapper,
                text="Browse",
                width=90,
                height=42,
                corner_radius=12,
                fg_color=THEME["card_2"],
                hover_color=THEME["border"],
                command=self.browse_output_dir,
            ).grid(row=0, column=1, padx=(8, 0))

    def render_provider_fields(self):
        if not hasattr(self, "provider_dynamic"):
            return
        for child in self.provider_dynamic.winfo_children():
            child.destroy()

        provider = PROVIDER_FROM_LABEL.get(self.settings_provider_var.get(), "ollama")
        fields = {
            "ollama": [("Ollama URL", "ollama_url", False), ("Model", "ollama_model", False)],
            "claude": [("Claude API Key", "claude_api_key", True), ("Claude Model", "claude_model", False)],
            "openai": [("OpenAI API Key", "openai_api_key", True), ("OpenAI Model", "openai_model", False)],
            "gemini": [("Gemini API Key", "gemini_api_key", True), ("Gemini Model", "gemini_model", False)],
        }[provider]

        for idx, (label, key, secret) in enumerate(fields):
            ctk.CTkLabel(self.provider_dynamic, text=label, text_color=THEME["muted"], font=FONT_SMALL, anchor="w").grid(
                row=idx * 2, column=0, sticky="ew", pady=(4 if idx == 0 else 10, 4)
            )
            ctk.CTkEntry(
                self.provider_dynamic,
                textvariable=self.provider_field_vars[key],
                show="•" if secret else "",
                height=42,
                fg_color=THEME["bg"],
                border_color=THEME["border"],
                corner_radius=12,
                text_color=THEME["text"],
            ).grid(row=idx * 2 + 1, column=0, sticky="ew")
        self.test_result_label.configure(text="")

    def sync_settings_fields(self):
        if not hasattr(self, "settings_provider_var"):
            return
        self.settings_provider_var.set(PROVIDER_LABELS.get(self.settings.get("ai_provider", "ollama"), "Ollama Local"))
        self.output_dir_var.set(str(self.settings.get("output_dir", OUTPUT_DIR)))
        self.auto_updates_var.set(bool(self.settings.get("auto_check_updates", True)))
        self.set_vertical_crop(bool(self.settings.get("vertical_crop", True)), save=False)
        for key, var in self.provider_field_vars.items():
            var.set(str(self.settings.get(key, DEFAULT_SETTINGS.get(key, ""))))

    def collect_settings_from_ui(self) -> Dict[str, Any]:
        settings = dict(self.settings)
        if hasattr(self, "settings_provider_var"):
            settings["ai_provider"] = PROVIDER_FROM_LABEL.get(self.settings_provider_var.get(), settings.get("ai_provider", "ollama"))
        for key, var in self.provider_field_vars.items():
            settings[key] = var.get().strip()
        if hasattr(self, "output_dir_var"):
            settings["output_dir"] = self.output_dir_var.get().strip() or str(OUTPUT_DIR)
        if hasattr(self, "auto_updates_var"):
            settings["auto_check_updates"] = bool(self.auto_updates_var.get())
        settings["vertical_crop"] = bool(self.settings.get("vertical_crop", True))
        return settings

    def save_settings_from_ui(self):
        self.settings = self.collect_settings_from_ui()
        save_settings(self.settings)
        self.provider_menu_var.set(PROVIDER_LABELS.get(self.settings["ai_provider"], "Ollama Local"))
        self.set_vertical_crop(bool(self.settings.get("vertical_crop", True)), save=False)
        self.refresh_status()
        self.show_toast("Settings saved locally.", "success")

    def browse_output_dir(self):
        folder = filedialog.askdirectory(title="Choose Shortify output folder")
        if folder:
            self.output_dir_var.set(folder)

    def test_selected_provider(self):
        settings = self.collect_settings_from_ui()
        self.test_result_label.configure(text="Testing connection...", text_color=THEME["muted"])

        def run():
            ok, message = test_provider_connection(settings)
            self.after(
                0,
                lambda: self.test_result_label.configure(
                    text=message,
                    text_color=THEME["success"] if ok else THEME["danger"],
                ),
            )
            self.after(0, lambda: self.show_toast(message, "success" if ok else "error"))

        threading.Thread(target=run, daemon=True).start()
