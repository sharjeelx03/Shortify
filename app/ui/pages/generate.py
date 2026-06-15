from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
import customtkinter as ctk

from app.core.pipeline import run_shortify_pipeline, validate_youtube_url
from app.core.providers import provider_ready
from app.core.settings import (
    CROP_MODE_KEYS, CROP_MODE_OPTIONS,
    FONT_BODY, FONT_H2, FONT_MONO, FONT_SMALL,
    OUTPUT_DIR, PROVIDER_FROM_LABEL, PROVIDER_LABELS,
    RESOLUTION_OPTIONS, THEME,
    check_ffmpeg, save_settings,
)
from app.ui.components import make_card, open_path, status_dot


class GeneratePageMixin:
    def _make_generate_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=0)
        page.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(page, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)

        right = ctk.CTkFrame(page, fg_color="transparent", width=320)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._make_generate_controls(left)
        self._make_duration_card(left)
        self._make_action_card(left)
        self._make_results_panel(left)
        self._make_system_card(right).grid(row=0, column=0, sticky="ew")
        self._make_activity_card(right).grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        return page

    # ── Controls card ───────────────────────────────────────────────────────

    def _make_generate_controls(self, parent):
        card = make_card(parent)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Video URL", text_color=THEME["muted"],
            font=("Segoe UI", 13, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 6))

        self.url_var   = tk.StringVar()
        self.url_entry = ctk.CTkEntry(
            card, textvariable=self.url_var,
            height=52, fg_color=THEME["bg"],
            border_color=THEME["border"], border_width=1,
            corner_radius=14,
            placeholder_text="Paste YouTube URL here…",
            placeholder_text_color=THEME["dim"],
            text_color=THEME["text"], font=("Segoe UI", 15),
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))

        self.recent_urls_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.recent_urls_frame.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        self.recent_urls_frame.grid_columnconfigure(0, weight=1)
        self.render_recent_url_chips()

        # Row: compilation controls + provider + resolution + crop
        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 10))
        controls.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Final videos
        self.num_final_videos_var = tk.IntVar(value=int(self.settings.get("num_final_videos", 3)))
        fv_menu = ctk.CTkOptionMenu(
            controls, values=["1","2","3","4","5"],
            variable=tk.StringVar(value=str(self.num_final_videos_var.get())),
            height=42, **self._om_style(),
            command=lambda v: self._compilation_value_changed("num_final_videos", v),
        )
        self._labeled_control(controls, "Final Videos", fv_menu, 0, 0)

        # Clips per video
        self.clips_per_video_var = tk.IntVar(value=int(self.settings.get("clips_per_video", 6)))
        cpv_menu = ctk.CTkOptionMenu(
            controls, values=[str(i) for i in range(1, 11)],
            variable=tk.StringVar(value=str(self.clips_per_video_var.get())),
            height=42, **self._om_style(),
            command=lambda v: self._compilation_value_changed("clips_per_video", v),
        )
        self._labeled_control(controls, "Clips / Video", cpv_menu, 0, 1)

        # Moment length slider
        self.segment_duration_var = tk.IntVar(value=int(self.settings.get("segment_duration", 8)))
        dur_frame = ctk.CTkFrame(controls, fg_color="transparent")
        dur_frame.grid_columnconfigure(0, weight=1)
        self.segment_duration_label = ctk.CTkLabel(
            dur_frame, text=f"{self.segment_duration_var.get()} sec",
            text_color=THEME["text"], font=FONT_SMALL, anchor="e",
        )
        self.segment_duration_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkSlider(
            dur_frame, from_=3, to=60, number_of_steps=57,
            command=self._duration_slider_changed,
            progress_color=THEME["accent"],
            button_color=THEME["accent"],
            button_hover_color=THEME["accent_hover"],
            fg_color=THEME["border"],
        ).set(self.segment_duration_var.get()) or None
        _slider = ctk.CTkSlider(
            dur_frame, from_=3, to=60, number_of_steps=57,
            command=self._duration_slider_changed,
            progress_color=THEME["accent"],
            button_color=THEME["accent"],
            button_hover_color=THEME["accent_hover"],
            fg_color=THEME["border"],
        )
        _slider.set(self.segment_duration_var.get())
        _slider.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self._labeled_control(controls, "Moment Length", dur_frame, 0, 2)

        # AI provider
        self.provider_menu_var = tk.StringVar(
            value=PROVIDER_LABELS.get(self.settings["ai_provider"], "Ollama Local")
        )
        provider_menu = ctk.CTkOptionMenu(
            controls, values=list(PROVIDER_LABELS.values()),
            variable=self.provider_menu_var,
            height=42, **self._om_style(),
            command=self.quick_provider_changed,
        )
        self._labeled_control(controls, "AI Provider", provider_menu, 0, 3)

        # Resolution
        current_res = self.settings.get("download_resolution", "720p")
        self.resolution_var = tk.StringVar(value=current_res)
        res_menu = ctk.CTkOptionMenu(
            controls, values=RESOLUTION_OPTIONS,
            variable=self.resolution_var,
            height=42, **self._om_style(),
            command=self.quick_resolution_changed,
        )
        self._labeled_control(controls, "Resolution", res_menu, 0, 4)

        # Crop mode
        from app.core.settings import CROP_MODE_KEYS
        inv_crop = {v: k for k, v in CROP_MODE_KEYS.items()}
        current_crop_key   = self.settings.get("crop_mode", "auto")
        current_crop_label = inv_crop.get(current_crop_key, "Auto-detect (smart)")
        self.crop_mode_var = tk.StringVar(value=current_crop_label)
        crop_menu = ctk.CTkOptionMenu(
            controls, values=CROP_MODE_OPTIONS,
            variable=self.crop_mode_var,
            height=42, **self._om_style(),
            command=lambda v: self.quick_crop_changed(),
        )
        self._labeled_control(controls, "Crop Mode", crop_menu, 0, 5)

        # Bottom toggles
        format_row = ctk.CTkFrame(card, fg_color="transparent")
        format_row.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
        format_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.burn_subtitles_var = tk.BooleanVar(value=bool(self.settings.get("burn_subtitles", False)))
        ctk.CTkSwitch(
            format_row, text="Burn hook subtitles",
            variable=self.burn_subtitles_var,
            progress_color=THEME["accent"],
            button_color=THEME["text"],
            button_hover_color=THEME["accent_hover"],
            text_color=THEME["text"],
            command=self.quick_subtitles_changed,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            format_row, text="Open Output Folder",
            height=42, **self._btn_style_ghost(),
            command=self.open_output_root,
        ).grid(row=0, column=2, sticky="e")

    def _om_style(self) -> dict:
        return dict(
            fg_color=THEME["card_2"], button_color=THEME["card_2"],
            button_hover_color=THEME["border"],
            text_color=THEME["text"],
            dropdown_fg_color=THEME["card"],
            dropdown_hover_color=THEME["card_2"],
        )

    def _btn_style_ghost(self) -> dict:
        return dict(
            fg_color=THEME["card_2"], hover_color=THEME["border"],
            text_color=THEME["text"], corner_radius=12,
        )

    def render_recent_url_chips(self):
        if not hasattr(self, "recent_urls_frame"):
            return
        for child in self.recent_urls_frame.winfo_children():
            child.destroy()
        recent = [u for u in self.settings.get("recent_urls", []) if isinstance(u, str) and u.strip()]
        if not recent:
            ctk.CTkLabel(
                self.recent_urls_frame,
                text="Recent URLs will appear here after your first run.",
                text_color=THEME["dim"], font=FONT_SMALL, anchor="w",
            ).pack(anchor="w")
            return
        ctk.CTkLabel(self.recent_urls_frame, text="Recent:", text_color=THEME["dim"], font=FONT_SMALL).pack(side="left", padx=(0, 8))
        for url in recent[:5]:
            text = url.replace("https://", "").replace("http://", "").replace("www.", "")
            label = text[:28] + ("…" if len(text) > 28 else "")
            ctk.CTkButton(
                self.recent_urls_frame, text=label,
                width=110, height=28, corner_radius=999,
                fg_color=THEME["card_2"], hover_color=THEME["border"],
                text_color=THEME["muted"], font=FONT_SMALL,
                command=lambda u=url: self.url_var.set(u),
            ).pack(side="left", padx=(0, 6))

    def remember_recent_url(self, url: str):
        url = url.strip()
        if not url:
            return
        recent = [u for u in self.settings.get("recent_urls", []) if u != url]
        recent.insert(0, url)
        self.settings["recent_urls"] = recent[:8]
        save_settings(self.settings)
        self.render_recent_url_chips()

    def _labeled_control(self, parent, label: str, widget, row: int, col: int):
        padx = (0 if col == 0 else 6, 6)
        ctk.CTkLabel(
            parent, text=label, text_color=THEME["muted"], font=FONT_SMALL, anchor="w",
        ).grid(row=row * 2, column=col, sticky="ew", padx=padx, pady=(0, 4))
        widget.grid(row=row * 2 + 1, column=col, sticky="ew", padx=padx, pady=(0, 8))

    # ── Duration / compilation card ─────────────────────────────────────────

    def _duration_slider_changed(self, value: float):
        secs = max(3, min(60, int(round(float(value)))))
        self.segment_duration_var.set(secs)
        if hasattr(self, "segment_duration_label"):
            self.segment_duration_label.configure(text=f"{secs} sec")
        self.update_compilation_preview()

    def _compilation_value_changed(self, key: str, value: str):
        try:
            n = int(value)
        except ValueError:
            return
        if key == "num_final_videos":
            self.num_final_videos_var.set(max(1, min(5, n)))
        elif key == "clips_per_video":
            self.clips_per_video_var.set(max(1, min(10, n)))
        elif key == "segment_duration":
            self.segment_duration_var.set(max(3, min(60, n)))
            if hasattr(self, "segment_duration_label"):
                self.segment_duration_label.configure(text=f"{self.segment_duration_var.get()} sec")
        self.update_compilation_preview()

    def _make_duration_card(self, parent):
        card = make_card(parent)
        card.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Compilation Export", text_color=THEME["text"],
                     font=FONT_H2, anchor="w").grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 2))
        ctk.CTkLabel(
            card,
            text="Shortify stitches multiple viral moments into final MP4 videos ready for upload.",
            text_color=THEME["muted"], font=FONT_SMALL, anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22)
        self.compilation_preview_label = ctk.CTkLabel(
            card, text="", text_color=THEME["accent"],
            font=("Segoe UI", 15, "bold"), anchor="w",
        )
        self.compilation_preview_label.grid(row=2, column=0, sticky="ew", padx=22, pady=(12, 6))
        ctk.CTkLabel(
            card,
            text="Example: 3 videos × 6 moments × 8s = ~48s per final video.",
            text_color=THEME["dim"], font=FONT_SMALL, anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        self.update_compilation_preview()

    def update_compilation_preview(self):
        if not hasattr(self, "compilation_preview_label"):
            return
        fv   = int(self.num_final_videos_var.get()) if hasattr(self, "num_final_videos_var") else int(self.settings.get("num_final_videos", 3))
        cpv  = int(self.clips_per_video_var.get())  if hasattr(self, "clips_per_video_var")  else int(self.settings.get("clips_per_video",  6))
        sd   = int(self.segment_duration_var.get()) if hasattr(self, "segment_duration_var") else int(self.settings.get("segment_duration", 8))
        total = fv * cpv
        est   = cpv * sd
        res   = self.resolution_var.get() if hasattr(self, "resolution_var") else self.settings.get("download_resolution", "720p")
        crop  = self.crop_mode_var.get()  if hasattr(self, "crop_mode_var")  else "Auto-detect (smart)"
        self.compilation_preview_label.configure(
            text=f"Output: {fv} MP4(s) · {cpv} moments each · ~{est}s · {total} total · {res} · {crop}"
        )

    # ── Action card ─────────────────────────────────────────────────────────

    def _make_action_card(self, parent):
        card = make_card(parent)
        card.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)

        self.generate_button = ctk.CTkButton(
            card, text="Generate Compilation Videos",
            height=56, corner_radius=16,
            fg_color=THEME["accent"], hover_color=THEME["accent_hover"],
            text_color=THEME["bg"], font=("Segoe UI", 16, "bold"),
            command=self.start_pipeline,
        )
        self.generate_button.grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 10))

        self.stop_button = ctk.CTkButton(
            card, text="Stop Current Job",
            height=42, corner_radius=12,
            fg_color=THEME["card_2"], hover_color=THEME["border"],
            text_color=THEME["muted"], state="disabled",
            command=self.stop_pipeline,
        )
        self.stop_button.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 14))

        self.progress = ctk.CTkProgressBar(
            card, height=12, corner_radius=999,
            progress_color=THEME["accent"], fg_color=THEME["border"],
        )
        self.progress.set(0)
        self.progress.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 6))
        self.progress_label = ctk.CTkLabel(
            card, text="Ready", text_color=THEME["muted"],
            font=FONT_SMALL, anchor="w",
        )
        self.progress_label.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))

    # ── Results panel ────────────────────────────────────────────────────────

    def _make_results_panel(self, parent):
        card = make_card(parent)
        card.grid(row=3, column=0, sticky="nsew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Final Video Results", text_color=THEME["text"],
                     font=FONT_H2, anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        self.results_scroll = ctk.CTkScrollableFrame(card, fg_color=THEME["bg"], corner_radius=14)
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.results_scroll.grid_columnconfigure(0, weight=1)
        self.show_empty_results()

    def show_empty_results(self):
        for child in self.results_scroll.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.results_scroll,
            text="No final videos yet. Paste a YouTube link, choose your settings, then click Generate.",
            text_color=THEME["muted"], font=FONT_BODY, wraplength=560,
        ).grid(row=0, column=0, padx=18, pady=24)

    def render_clip_results(self, results: List[Dict[str, Any]], output_dir: Optional[Path]):
        for child in self.results_scroll.winfo_children():
            child.destroy()
        if not results:
            self.show_empty_results()
            return
        for idx, item in enumerate(results):
            clip  = item.get("clip", {})
            path  = Path(item.get("path", ""))
            title = str(clip.get("title", f"Clip {idx + 1}"))
            hook  = str(clip.get("hook", ""))
            why   = str(clip.get("why_viral", ""))
            tags  = " ".join(clip.get("hashtags", [])) if isinstance(clip.get("hashtags"), list) else str(clip.get("hashtags", ""))
            start = clip.get("start_seconds", "?")
            end   = clip.get("end_seconds",   "?")

            card = ctk.CTkFrame(
                self.results_scroll, fg_color=THEME["card"],
                corner_radius=14, border_width=1, border_color=THEME["border"],
            )
            card.grid(row=idx, column=0, sticky="ew", padx=8, pady=(8 if idx == 0 else 4, 4))
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=title, text_color=THEME["text"],
                         font=("Segoe UI", 16, "bold"), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
            ctk.CTkLabel(card, text=f"{start}s → {end}s  •  {path.name}",
                         text_color=THEME["dim"], font=FONT_SMALL, anchor="w").grid(
                row=1, column=0, sticky="ew", padx=16)
            ctk.CTkLabel(card, text=f"Hook: {hook}", text_color=THEME["accent"],
                         font=FONT_SMALL, anchor="w", wraplength=560).grid(
                row=2, column=0, sticky="ew", padx=16, pady=(8, 0))
            ctk.CTkLabel(card, text=f"Why viral: {why}", text_color=THEME["muted"],
                         font=FONT_SMALL, anchor="w", wraplength=560).grid(
                row=3, column=0, sticky="ew", padx=16, pady=(4, 0))
            ctk.CTkLabel(card, text=tags or "#shorts #reels", text_color=THEME["blue"],
                         font=FONT_SMALL, anchor="w", wraplength=560).grid(
                row=4, column=0, sticky="ew", padx=16, pady=(4, 14))

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.grid(row=0, column=1, rowspan=5, sticky="ns", padx=16, pady=14)
            ctk.CTkButton(btns, text="▶  Play", width=96, height=34, corner_radius=10,
                          fg_color=THEME["accent"], hover_color=THEME["accent_hover"],
                          text_color=THEME["bg"],
                          command=lambda p=path: open_path(p)).pack(pady=(0, 8))
            ctk.CTkButton(btns, text="Folder", width=96, height=34, corner_radius=10,
                          **dict(fg_color=THEME["card_2"], hover_color=THEME["border"],
                                 text_color=THEME["text"]),
                          command=lambda p=output_dir or path.parent: open_path(Path(p))).pack()

    # ── System / Activity cards ──────────────────────────────────────────────

    def _make_system_card(self, parent):
        card = make_card(parent)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="System Status", text_color=THEME["text"],
                     font=FONT_H2, anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        for i, key in enumerate(["ffmpeg", "ai", "output", "updates"], 1):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=18, pady=5)
            row.grid_columnconfigure(1, weight=1)
            dot = status_dot(row, THEME["dim"])
            dot.grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text=key.title(), text_color=THEME["text"],
                         font=FONT_BODY, anchor="w").grid(row=0, column=1, sticky="ew", padx=(8, 0))
            val = ctk.CTkLabel(row, text="Checking", text_color=THEME["muted"],
                               font=FONT_SMALL, anchor="e")
            val.grid(row=0, column=2, sticky="e")
            self.system_rows[key] = (dot, val)
        ctk.CTkButton(
            card, text="Refresh Status", height=38,
            **dict(fg_color=THEME["card_2"], hover_color=THEME["border"],
                   text_color=THEME["text"], corner_radius=12),
            command=self.refresh_status,
        ).grid(row=5, column=0, sticky="ew", padx=18, pady=(12, 18))
        return card

    def _make_activity_card(self, parent):
        card = make_card(parent)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Activity", text_color=THEME["text"],
                     font=FONT_H2, anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        self.activity = ctk.CTkTextbox(
            card, fg_color=THEME["bg"], text_color=THEME["muted"],
            border_width=0, corner_radius=12, font=FONT_MONO, wrap="word",
        )
        self.activity.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.activity.insert("end", "Ready. Paste a YouTube URL and generate your first clips.\n")
        self.activity.configure(state="disabled")
        return card

    # ── Logging / progress ──────────────────────────────────────────────────

    def log(self, message: str, tag: str = "dim"):
        symbols = {"ok": "✓", "err": "✕", "warn": "!", "accent": "→", "dim": "•"}
        prefix  = f"{symbols.get(tag, '•')} "
        def apply():
            self.activity.configure(state="normal")
            self.activity.insert("end", prefix + message + "\n")
            self.activity.see("end")
            self.activity.configure(state="disabled")
        self.after(0, apply)

    def clear_activity(self):
        self.activity.configure(state="normal")
        self.activity.delete("1.0", "end")
        self.activity.configure(state="disabled")

    def _fmt_sec(self, s: float) -> str:
        s = max(0, int(s))
        m, sec = divmod(s, 60)
        return f"{m}m {sec}s" if m else f"{sec}s"

    def set_progress(self, value: float, text: str):
        def apply():
            clipped = max(0, min(1, value))
            self.progress.set(clipped)
            label = text
            started = getattr(self, "job_started_at", None)
            if started and 0 < clipped < 1:
                elapsed = time.time() - started
                if clipped >= 0.08:
                    remaining = (elapsed / clipped) - elapsed
                    label = f"{text} · {self._fmt_sec(elapsed)} elapsed · ~{self._fmt_sec(remaining)} left"
                else:
                    label = f"{text} · {self._fmt_sec(elapsed)} elapsed"
            self.progress_label.configure(text=label)
            # Also update the loading overlay
            if hasattr(self, "loading_overlay"):
                self.loading_overlay.update(clipped, text)
        self.after(0, apply)

    def set_running(self, running: bool):
        self.running = running
        self.generate_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(
            state="normal" if running else "disabled",
            text_color=THEME["danger"] if running else THEME["muted"],
        )

    def open_output_root(self):
        open_path(Path(self.settings.get("output_dir", str(OUTPUT_DIR))))

    # ── Validation ──────────────────────────────────────────────────────────

    def validate_inputs(self) -> Optional[Tuple[str, int, List[int]]]:
        url = self.url_var.get().strip()
        if not url:
            self.show_toast("Paste a YouTube URL first.", "warning")
            return None
        try:
            validate_youtube_url(url)
        except Exception as exc:
            self.show_toast(str(exc), "error")
            return None
        if not check_ffmpeg():
            self.show_toast("ffmpeg not found. Run setup_ffmpeg.bat or place ffmpeg.exe in /bin.", "error")
            return None
        ready, _msg = provider_ready(self.settings)
        if not ready:
            prov = PROVIDER_LABELS.get(self.settings.get("ai_provider"), "AI provider")
            self.show_toast(f"{prov} not ready. Check Settings.", "error")
            return None

        fv  = max(1, min(5,  int(self.num_final_videos_var.get())))
        cpv = max(1, min(10, int(self.clips_per_video_var.get())))
        sd  = max(3, min(60, int(self.segment_duration_var.get())))

        total     = fv * cpv
        durations = [sd] * total

        self.settings["export_mode"]      = "compilation"
        self.settings["num_final_videos"] = fv
        self.settings["clips_per_video"]  = cpv
        self.settings["segment_duration"] = sd
        self.settings["num_clips"]        = total
        self.settings["durations"]        = durations[:5]
        self.settings["burn_subtitles"]   = bool(self.burn_subtitles_var.get()) if hasattr(self, "burn_subtitles_var") else False
        self.settings["download_resolution"] = self.resolution_var.get() if hasattr(self, "resolution_var") else self.settings.get("download_resolution", "720p")

        from app.core.settings import CROP_MODE_KEYS
        if hasattr(self, "crop_mode_var"):
            self.settings["crop_mode"] = CROP_MODE_KEYS.get(self.crop_mode_var.get(), "auto")

        save_settings(self.settings)
        self.update_compilation_preview()
        return url, total, durations

    # ── Pipeline ────────────────────────────────────────────────────────────

    def start_pipeline(self):
        valid = self.validate_inputs()
        if not valid:
            return
        url, num_clips, durations = valid
        self.remember_recent_url(url)
        self.job_started_at = time.time()
        self.clear_activity()
        self.show_empty_results()
        self.set_progress(0.03, "Starting…")
        self.set_running(True)
        self.loading_overlay.show()

        settings    = dict(self.settings)
        output_root = Path(settings["output_dir"])
        threading.Thread(
            target=self.pipeline_thread,
            args=(url, num_clips, durations, settings, output_root),
            daemon=True,
        ).start()

    def stop_pipeline(self):
        self.running       = False
        self.job_started_at = None
        self.log("Stopped by user.", "warn")
        self.set_running(False)
        self.set_progress(0, "Stopped")
        self.show_toast("Current job stopped.", "warning")
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.hide()

    def pipeline_thread(
        self, url: str, num_clips: int, durations: List[int],
        settings: Dict[str, Any], output_root: Path,
    ):
        try:
            result     = run_shortify_pipeline(
                url=url, num_clips=num_clips, durations=durations,
                settings=settings, output_root=output_root,
                log=self.log, progress=self.set_progress,
                should_continue=lambda: self.running,
            )
            output_dir = result.get("output_dir")
            results    = result.get("results", [])
            self.current_output_dir = Path(output_dir) if output_dir else None
            self.after(0, lambda: self.render_clip_results(results, self.current_output_dir))
            self.after(0, self.refresh_library)
            if results:
                self.after(0, lambda: self.show_toast(f"Generated {len(results)} video(s) ✓", "success"))
        except Exception as exc:
            self.set_progress(0, "Failed")
            self.log(str(exc), "err")
            self.after(0, lambda: self.show_toast(f"Error: {exc}", "error", 5200))
        finally:
            self.job_started_at = None
            self.after(0, lambda: self.set_running(False))
            self.after(0, self.loading_overlay.hide)
