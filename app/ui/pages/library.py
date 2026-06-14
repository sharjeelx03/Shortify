from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import customtkinter as ctk

from app.core.settings import FONT_BODY, FONT_H2, FONT_SMALL, OUTPUT_DIR, THEME
from app.ui.components import make_card, open_path


def _fmt_size(bytes_count: int) -> str:
    if bytes_count >= 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024 * 1024):.1f} GB"
    if bytes_count >= 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f} MB"
    if bytes_count >= 1024:
        return f"{bytes_count / 1024:.1f} KB"
    return f"{bytes_count} B"


def _fmt_date(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d %b %Y, %I:%M %p")


def _load_results(folder: Path) -> Dict[str, Any]:
    path = folder / "results.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _clip_titles(manifest: Dict[str, Any], limit: int = 3) -> str:
    titles: List[str] = []
    for item in manifest.get("results", [])[:limit]:
        clip = item.get("clip", {}) if isinstance(item, dict) else {}
        title = str(clip.get("title", "")).strip()
        if title:
            titles.append(title)
    return " • ".join(titles)


class LibraryPageMixin:
    def _make_library_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        top = make_card(page)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        top.grid_columnconfigure(0, weight=1)
        self.library_path_label = ctk.CTkLabel(top, text="Output folder", text_color=THEME["muted"], font=FONT_BODY, anchor="w")
        self.library_path_label.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            top,
            text="Generated folders appear here after successful jobs. Cards use results.json metadata when available.",
            text_color=THEME["dim"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))
        ctk.CTkButton(
            top,
            text="Open Output Folder",
            width=170,
            height=40,
            corner_radius=12,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["bg"],
            command=self.open_output_root,
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=20)

        self.library_scroll = ctk.CTkScrollableFrame(
            page, fg_color=THEME["card"], corner_radius=18, border_width=1, border_color=THEME["border"]
        )
        self.library_scroll.grid(row=1, column=0, sticky="nsew")
        self.library_scroll.grid_columnconfigure(0, weight=1)
        return page

    def refresh_library(self):
        if not hasattr(self, "library_scroll"):
            return
        for child in self.library_scroll.winfo_children():
            child.destroy()

        root = Path(self.settings.get("output_dir", str(OUTPUT_DIR)))
        self.library_path_label.configure(text=f"Output folder: {root}")
        root.mkdir(parents=True, exist_ok=True)

        folders = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
        if not folders:
            ctk.CTkLabel(self.library_scroll, text="No generated clips yet.", text_color=THEME["muted"], font=FONT_BODY).grid(
                row=0, column=0, pady=28
            )
            return

        for idx, folder in enumerate(folders[:30]):
            manifest = _load_results(folder)
            mp4s = sorted([p for p in folder.glob("*.mp4") if p.name.lower() != "source.mp4"])
            total_size = sum(p.stat().st_size for p in mp4s if p.exists())
            modified = _fmt_date(folder.stat().st_mtime)
            vertical = manifest.get("vertical_crop")
            vertical_text = "9:16 Shorts" if vertical is True else "Original ratio" if vertical is False else "Format unknown"
            clip_count = len(manifest.get("results", [])) if manifest else len(mp4s)
            titles = _clip_titles(manifest)

            row = ctk.CTkFrame(
                self.library_scroll, fg_color=THEME["bg"], corner_radius=14, border_width=1, border_color=THEME["border"]
            )
            row.grid(row=idx, column=0, sticky="ew", padx=12, pady=(12 if idx == 0 else 6, 6))
            row.grid_columnconfigure(0, weight=1)

            heading = f"{folder.name}  •  {clip_count} clips"
            ctk.CTkLabel(row, text=heading, text_color=THEME["text"], font=("Segoe UI", 15, "bold"), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=16, pady=(12, 0)
            )
            ctk.CTkLabel(
                row,
                text=f"{modified} • {vertical_text} • {len(mp4s)} videos • {_fmt_size(total_size)}",
                text_color=THEME["muted"],
                font=FONT_SMALL,
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 0))
            ctk.CTkLabel(
                row,
                text=titles or "No clip metadata found yet.",
                text_color=THEME["blue"] if titles else THEME["dim"],
                font=FONT_SMALL,
                anchor="w",
                wraplength=760,
            ).grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 12))

            buttons = ctk.CTkFrame(row, fg_color="transparent")
            buttons.grid(row=0, column=1, rowspan=3, sticky="e", padx=16, pady=12)
            ctk.CTkButton(
                buttons,
                text="Open",
                width=88,
                height=34,
                corner_radius=10,
                fg_color=THEME["card_2"],
                hover_color=THEME["border"],
                command=lambda p=folder: open_path(p),
            ).pack(pady=(0, 8))
            first_mp4 = mp4s[0] if mp4s else folder
            ctk.CTkButton(
                buttons,
                text="Play",
                width=88,
                height=34,
                corner_radius=10,
                fg_color=THEME["accent"] if mp4s else THEME["card_2"],
                hover_color=THEME["accent_hover"] if mp4s else THEME["border"],
                text_color=THEME["bg"] if mp4s else THEME["muted"],
                state="normal" if mp4s else "disabled",
                command=lambda p=first_mp4: open_path(p),
            ).pack()
