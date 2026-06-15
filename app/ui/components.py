from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import tkinter as tk

try:
    import customtkinter as ctk
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False

from app.core.settings import THEME, resource_path


def make_card(parent, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=THEME["card"], corner_radius=18,
                        border_width=1, border_color=THEME["border"], **kwargs)


def status_dot(parent, color: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text="●", text_color=color, font=("Segoe UI", 10), width=14)


def open_path(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


def load_sidebar_logo(max_size: int = 64) -> Optional[object]:
    logo_path = resource_path("assets/logo.png")
    if not logo_path.exists():
        return None
    try:
        if _PIL:
            img = Image.open(logo_path)
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            return ctk.CTkImage(img, size=(img.width, img.height))
        photo = tk.PhotoImage(file=str(logo_path))
        factor = max(1, photo.width() // max_size)
        return photo.subsample(factor, factor)
    except Exception:
        return None


class ToastManager:
    COLORS = {
        "success": ("#22C55E", "#09090B"),
        "error":   ("#EF4444", "#F5F5F5"),
        "warning": ("#EAB308", "#09090B"),
        "info":    ("#38BDF8", "#09090B"),
    }

    def __init__(self, root: ctk.CTk):
        self._root    = root
        self._queue   = []
        self._showing = False

    def show(self, message: str, kind: str = "info", duration_ms: int = 3400):
        self._queue.append((message, kind, duration_ms))
        if not self._showing:
            self._show_next()

    def _show_next(self):
        if not self._queue:
            self._showing = False
            return
        self._showing = True
        message, kind, duration_ms = self._queue.pop(0)
        bg, fg = self.COLORS.get(kind, self.COLORS["info"])
        frame = ctk.CTkFrame(self._root, fg_color=bg, corner_radius=12)
        ctk.CTkLabel(frame, text=message, text_color=fg, font=("Segoe UI", 13, "bold"),
                     wraplength=340, justify="left").pack(padx=18, pady=12)
        frame.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self._root.after(duration_ms, lambda: self._dismiss(frame))

    def _dismiss(self, frame):
        try:
            frame.place_forget()
            frame.destroy()
        except Exception:
            pass
        self._root.after(200, self._show_next)


class LoadingOverlay:
    def __init__(self, root: ctk.CTk, on_cancel):
        self._root      = root
        self._on_cancel = on_cancel
        self._frame     = None
        self._stage_label   = None
        self._eta_label     = None
        self._progress_bar  = None
        self._spin_canvas   = None
        self._spin_job      = None
        self._spin_angle    = 0
        self._start_time    = 0.0
        self._alive         = False

    def show(self):
        if self._frame is not None:
            return
        self._alive      = True
        self._start_time = time.time()

        overlay = ctk.CTkFrame(self._root, fg_color="#09090B", corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._frame = overlay

        card = ctk.CTkFrame(overlay, fg_color=THEME["card"], corner_radius=22,
                            border_width=1, border_color=THEME["border"], width=400, height=290)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        self._spin_canvas = tk.Canvas(card, width=64, height=64, bg=THEME["card"], highlightthickness=0)
        self._spin_canvas.pack(pady=(32, 8))

        self._stage_label = ctk.CTkLabel(card, text="Starting…",
                                         text_color=THEME["text"], font=("Segoe UI", 14, "bold"))
        self._stage_label.pack(pady=(0, 4))

        self._eta_label = ctk.CTkLabel(card, text="Estimating time…",
                                       text_color=THEME["muted"], font=("Segoe UI", 12))
        self._eta_label.pack(pady=(0, 12))

        self._progress_bar = ctk.CTkProgressBar(card, height=8, corner_radius=999,
                                                 progress_color=THEME["accent"],
                                                 fg_color=THEME["border"], width=320)
        self._progress_bar.set(0)
        self._progress_bar.pack(pady=(0, 16))

        ctk.CTkButton(card, text="Cancel Job", height=38, width=180, corner_radius=10,
                      fg_color=THEME["card_2"], hover_color=THEME["border"],
                      text_color=THEME["danger"], font=("Segoe UI", 13, "bold"),
                      command=self._cancel).pack()

        self._tick_spinner()

    def update(self, progress: float, stage_text: str):
        if not self._alive or self._frame is None:
            return
        elapsed = time.time() - self._start_time
        def _apply():
            if self._stage_label:
                self._stage_label.configure(text=stage_text)
            if self._progress_bar:
                self._progress_bar.set(max(0, min(1, progress)))
            if self._eta_label:
                if progress > 0.05 and elapsed > 2:
                    remaining = (elapsed / progress) - elapsed
                    m, s = divmod(int(remaining), 60)
                    eta = f"{m}m {s}s remaining" if m else f"{s}s remaining"
                    self._eta_label.configure(text=f"Elapsed {int(elapsed)}s · ~{eta}")
                else:
                    self._eta_label.configure(text=f"Elapsed {int(elapsed)}s…")
        self._root.after(0, _apply)

    def hide(self):
        self._alive = False
        if self._spin_job:
            try:
                self._root.after_cancel(self._spin_job)
            except Exception:
                pass
            self._spin_job = None
        if self._frame:
            try:
                self._frame.place_forget()
                self._frame.destroy()
            except Exception:
                pass
            self._frame = None

    def _cancel(self):
        self._on_cancel()
        self.hide()

    def _tick_spinner(self):
        if not self._alive or self._spin_canvas is None:
            return
        try:
            c = self._spin_canvas
            c.delete("arc")
            c.create_arc(8, 8, 56, 56, start=self._spin_angle, extent=270,
                         style="arc", outline=THEME["accent"], width=5, tags="arc")
            self._spin_angle = (self._spin_angle + 12) % 360
            self._spin_job = self._root.after(40, self._tick_spinner)
        except tk.TclError:
            pass