from __future__ import annotations

import threading
import webbrowser

import customtkinter as ctk
from tkinter import messagebox

from core.settings import APP_VERSION, FONT_BODY, FONT_H2, GITHUB_API_LATEST, GITHUB_RELEASES_URL, GITHUB_URL, THEME, version_tuple
from ui.components import make_card


class UpdatesPageMixin:
    def _make_updates_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        card = make_card(page)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="GitHub Updates", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=22, pady=(20, 8)
        )
        ctk.CTkLabel(
            card,
            text=f"Current version: v{APP_VERSION}\nRepository: {GITHUB_URL}",
            text_color=THEME["muted"],
            font=FONT_BODY,
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 14))
        self.update_result_label = ctk.CTkLabel(
            card, text="No update check yet.", text_color=THEME["dim"], font=FONT_BODY, anchor="w", justify="left"
        )
        self.update_result_label.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        ctk.CTkButton(
            card,
            text="Check Updates",
            height=42,
            corner_radius=12,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["bg"],
            command=self.check_updates_manual,
        ).grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 10))
        ctk.CTkButton(
            card,
            text="Open Releases Page",
            height=42,
            corner_radius=12,
            fg_color=THEME["card_2"],
            hover_color=THEME["border"],
            text_color=THEME["text"],
            command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
        ).grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 20))
        return page

    def check_updates_silent(self):
        self.check_updates(show_no_update=False)

    def check_updates_manual(self):
        self.check_updates(show_no_update=True)

    def check_updates(self, show_no_update: bool):
        if hasattr(self, "update_result_label"):
            self.update_result_label.configure(text="Checking GitHub releases...", text_color=THEME["muted"])

        def run():
            try:
                import requests

                response = requests.get(GITHUB_API_LATEST, timeout=8)
                if response.status_code == 404:
                    text = "No GitHub release has been published yet."
                    self._update_status_text(text, THEME["warning"])
                    if show_no_update:
                        self.after(0, lambda: self.show_toast(text, "warning"))
                    return
                response.raise_for_status()
                data = response.json()
                latest = str(data.get("tag_name", "")).strip() or str(data.get("name", "")).strip()
                html_url = data.get("html_url", GITHUB_RELEASES_URL)
                if latest and version_tuple(latest) > version_tuple(APP_VERSION):
                    text = f"Update available: {latest}\nCurrent version: v{APP_VERSION}"
                    self._update_status_text(text, THEME["accent"])
                    if show_no_update:
                        self.after(0, lambda: self.ask_open_update(latest, html_url))
                else:
                    text = f"You are up to date. Current version: v{APP_VERSION}"
                    self._update_status_text(text, THEME["success"])
                    if show_no_update:
                        self.after(0, lambda: self.show_toast(text, "success"))
            except Exception as exc:
                text = f"Update check failed: {exc}"
                self._update_status_text(text, THEME["danger"])
                if show_no_update:
                    self.after(0, lambda: self.show_toast(str(exc), "error"))

        threading.Thread(target=run, daemon=True).start()

    def _update_status_text(self, text: str, color: str):
        if hasattr(self, "update_result_label"):
            self.after(0, lambda: self.update_result_label.configure(text=text, text_color=color))

    def ask_open_update(self, latest: str, url: str):
        if messagebox.askyesno(
            "Update available",
            f"New Shortify version available: {latest}\nCurrent version: v{APP_VERSION}\n\nOpen download page?",
        ):
            webbrowser.open(url)
