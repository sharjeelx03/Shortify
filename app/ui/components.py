from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import tkinter as tk

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("CustomTkinter is missing. Run: pip install -r requirements.txt") from exc

from app.core.settings import FONT_BODY, FONT_SMALL, THEME, resource_path


def make_card(parent, **kwargs):
    return ctk.CTkFrame(
        parent,
        fg_color=THEME["card"],
        corner_radius=18,
        border_width=1,
        border_color=THEME["border"],
        **kwargs,
    )


def status_dot(parent, color: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text="●", text_color=color, font=("Segoe UI", 18, "bold"), width=18)


def open_path(path: Path) -> None:
    path = Path(path)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def load_sidebar_logo(max_size: int = 64):
    logo = resource_path("assets/logo.png")
    if not logo.exists():
        return None
    try:
        from PIL import Image

        image = Image.open(logo)
        image.thumbnail((max_size, max_size))
        return ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
    except Exception:
        try:
            # Fallback only; CTkImage is preferred for HighDPI scaling.
            image = tk.PhotoImage(file=str(logo))
            factor = max(1, int(max(image.width(), image.height()) / max_size))
            if factor > 1:
                image = image.subsample(factor, factor)
            return image
        except Exception:
            return None


class ToastManager:
    """Tiny in-app snackbar/toast helper for polished non-blocking feedback."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.toast: Optional[ctk.CTkFrame] = None
        self.hide_job: Optional[str] = None

    def show(self, message: str, kind: str = "info", duration_ms: int = 3200) -> None:
        if self.toast is not None:
            self.toast.destroy()
            self.toast = None
        if self.hide_job is not None:
            try:
                self.root.after_cancel(self.hide_job)
            except Exception:
                pass
            self.hide_job = None

        colors = {
            "success": THEME["success"],
            "error": THEME["danger"],
            "warning": THEME["warning"],
            "info": THEME["accent"],
        }
        border = colors.get(kind, THEME["accent"])
        frame = ctk.CTkFrame(
            self.root,
            fg_color=THEME["card"],
            corner_radius=14,
            border_width=1,
            border_color=border,
        )
        frame.place(relx=1.0, rely=1.0, x=-26, y=-26, anchor="se")
        ctk.CTkLabel(
            frame,
            text=message,
            text_color=THEME["text"],
            font=FONT_BODY,
            justify="left",
            wraplength=430,
        ).pack(padx=16, pady=(12, 2), anchor="w")
        ctk.CTkLabel(
            frame,
            text="Shortify",
            text_color=THEME["dim"],
            font=FONT_SMALL,
        ).pack(padx=16, pady=(0, 12), anchor="w")
        self.toast = frame
        self.hide_job = self.root.after(duration_ms, self.hide)

    def hide(self) -> None:
        if self.toast is not None:
            self.toast.destroy()
            self.toast = None
        self.hide_job = None
