from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
import customtkinter as ctk

from core.pipeline import run_shortify_pipeline
from core.providers import provider_ready
from core.settings import (
    FONT_BODY,
    FONT_H2,
    FONT_MONO,
    FONT_SMALL,
    OUTPUT_DIR,
    PROVIDER_FROM_LABEL,
    PROVIDER_LABELS,
    THEME,
    check_ffmpeg,
    save_settings,
)
from ui.components import make_card, open_path, status_dot


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

    def _make_generate_controls(self, parent):
        card = make_card(parent)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Video URL", text_color=THEME["muted"], font=("Segoe UI", 13, "bold"), anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 6))
        self.url_var = tk.StringVar()
        self.url_entry = ctk.CTkEntry(
            card,
            textvariable=self.url_var,
            height=52,
            fg_color=THEME["bg"],
            border_color=THEME["border"],
            border_width=1,
            corner_radius=14,
            placeholder_text="Paste YouTube URL here...",
            placeholder_text_color=THEME["dim"],
            text_color=THEME["text"],
            font=("Segoe UI", 15),
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))

        self.recent_urls_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.recent_urls_frame.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 16))
        self.recent_urls_frame.grid_columnconfigure(0, weight=1)
        self.render_recent_url_chips()

        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 10))
        controls.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.num_final_videos_var = tk.IntVar(value=int(self.settings.get("num_final_videos", 3)))
        final_video_menu = ctk.CTkOptionMenu(
            controls,
            values=["1", "2", "3", "4", "5"],
            variable=tk.StringVar(value=str(self.num_final_videos_var.get())),
            height=42,
            fg_color=THEME["card_2"],
            button_color=THEME["card_2"],
            button_hover_color=THEME["border"],
            text_color=THEME["text"],
            dropdown_fg_color=THEME["card"],
            dropdown_hover_color=THEME["card_2"],
            command=lambda value: self._compilation_value_changed("num_final_videos", value),
        )
        self._labeled_control(controls, "Final Videos", final_video_menu, 0, 0)

        self.clips_per_video_var = tk.IntVar(value=int(self.settings.get("clips_per_video", 6)))
        clips_per_video_menu = ctk.CTkOptionMenu(
            controls,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            variable=tk.StringVar(value=str(self.clips_per_video_var.get())),
            height=42,
            fg_color=THEME["card_2"],
            button_color=THEME["card_2"],
            button_hover_color=THEME["border"],
            text_color=THEME["text"],
            dropdown_fg_color=THEME["card"],
            dropdown_hover_color=THEME["card_2"],
            command=lambda value: self._compilation_value_changed("clips_per_video", value),
        )
        self._labeled_control(controls, "Clips / Video", clips_per_video_menu, 0, 1)

        self.segment_duration_var = tk.IntVar(value=int(self.settings.get("segment_duration", 8)))
        segment_duration_menu = ctk.CTkOptionMenu(
            controls,
            values=["3", "5", "7", "8", "10", "12", "15", "20", "30"],
            variable=tk.StringVar(value=str(self.segment_duration_var.get())),
            height=42,
            fg_color=THEME["card_2"],
            button_color=THEME["card_2"],
            button_hover_color=THEME["border"],
            text_color=THEME["text"],
            dropdown_fg_color=THEME["card"],
            dropdown_hover_color=THEME["card_2"],
            command=lambda value: self._compilation_value_changed("segment_duration", value),
        )
        self._labeled_control(controls, "Moment Length", segment_duration_menu, 0, 2)

        self.provider_menu_var = tk.StringVar(value=PROVIDER_LABELS.get(self.settings["ai_provider"], "Ollama Local"))
        provider_menu = ctk.CTkOptionMenu(
            controls,
            values=list(PROVIDER_LABELS.values()),
            variable=self.provider_menu_var,
            height=42,
            fg_color=THEME["card_2"],
            button_color=THEME["card_2"],
            button_hover_color=THEME["border"],
            text_color=THEME["text"],
            dropdown_fg_color=THEME["card"],
            dropdown_hover_color=THEME["card_2"],
            command=self.quick_provider_changed,
        )
        self._labeled_control(controls, "AI Provider", provider_menu, 0, 3)

        format_row = ctk.CTkFrame(card, fg_color="transparent")
        format_row.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
        format_row.grid_columnconfigure((0, 1), weight=1)

        self.vertical_crop_var = tk.BooleanVar(value=bool(self.settings.get("vertical_crop", True)))
        crop_switch = ctk.CTkSwitch(
            format_row,
            text="9:16 vertical crop for every final video",
            variable=self.vertical_crop_var,
            progress_color=THEME["accent"],
            button_color=THEME["text"],
            button_hover_color=THEME["accent_hover"],
            text_color=THEME["text"],
            command=self.quick_crop_changed,
        )
        crop_switch.grid(row=0, column=0, sticky="w")

        output_button = ctk.CTkButton(
            format_row,
            text="Open Output Folder",
            height=42,
            fg_color=THEME["card_2"],
            hover_color=THEME["border"],
            text_color=THEME["text"],
            corner_radius=12,
            command=self.open_output_root,
        )
        output_button.grid(row=0, column=1, sticky="e")

    def render_recent_url_chips(self):
        if not hasattr(self, "recent_urls_frame"):
            return
        for child in self.recent_urls_frame.winfo_children():
            child.destroy()
        recent_urls = [u for u in self.settings.get("recent_urls", []) if isinstance(u, str) and u.strip()]
        if not recent_urls:
            ctk.CTkLabel(
                self.recent_urls_frame,
                text="Recent URLs will appear here after your first run.",
                text_color=THEME["dim"],
                font=FONT_SMALL,
                anchor="w",
            ).pack(anchor="w")
            return
        label = ctk.CTkLabel(self.recent_urls_frame, text="Recent:", text_color=THEME["dim"], font=FONT_SMALL)
        label.pack(side="left", padx=(0, 8))
        for url in recent_urls[:5]:
            chip_text = self._recent_url_label(url)
            ctk.CTkButton(
                self.recent_urls_frame,
                text=chip_text,
                width=110,
                height=28,
                corner_radius=999,
                fg_color=THEME["card_2"],
                hover_color=THEME["border"],
                text_color=THEME["muted"],
                font=FONT_SMALL,
                command=lambda u=url: self.url_var.set(u),
            ).pack(side="left", padx=(0, 6))

    def _recent_url_label(self, url: str) -> str:
        text = url.replace("https://", "").replace("http://", "")
        text = text.replace("www.", "")
        return text[:28] + ("..." if len(text) > 28 else "")

    def remember_recent_url(self, url: str):
        url = url.strip()
        if not url:
            return
        recent = [item for item in self.settings.get("recent_urls", []) if item != url]
        recent.insert(0, url)
        self.settings["recent_urls"] = recent[:8]
        save_settings(self.settings)
        self.render_recent_url_chips()

    def _labeled_control(self, parent, label: str, widget, row: int, column: int):
        # The widget is created with `parent` as its master, so keep everything
        # inside this grid-managed controls frame. Mixing pack() with grid() here
        # crashes CustomTkinter/Tk at startup.
        padx = (0 if column == 0 else 8, 0 if column == 3 else 8)
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=THEME["muted"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=row * 2, column=column, sticky="ew", padx=padx, pady=(0, 6))
        widget.grid(row=row * 2 + 1, column=column, sticky="ew", padx=padx, pady=(0, 8))

    def _compilation_value_changed(self, key: str, value: str):
        try:
            number = int(value)
        except ValueError:
            return
        if key == "num_final_videos":
            self.num_final_videos_var.set(max(1, min(5, number)))
        elif key == "clips_per_video":
            self.clips_per_video_var.set(max(1, min(10, number)))
        elif key == "segment_duration":
            self.segment_duration_var.set(max(3, min(30, number)))
        self.update_compilation_preview()

    def _make_duration_card(self, parent):
        card = make_card(parent)
        card.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Compilation Export", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=22, pady=(18, 2)
        )
        ctk.CTkLabel(
            card,
            text="Shortify now builds final videos by stitching multiple viral moments into one MP4.",
            text_color=THEME["muted"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22)
        self.compilation_preview_label = ctk.CTkLabel(
            card,
            text="",
            text_color=THEME["accent"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        )
        self.compilation_preview_label.grid(row=2, column=0, sticky="ew", padx=22, pady=(14, 6))
        ctk.CTkLabel(
            card,
            text="Example: 3 final videos × 6 moments × 8 seconds = around 48 seconds per final video.",
            text_color=THEME["dim"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))
        self.update_compilation_preview()

    def update_compilation_preview(self):
        if not hasattr(self, "compilation_preview_label"):
            return
        final_videos = int(self.num_final_videos_var.get()) if hasattr(self, "num_final_videos_var") else int(self.settings.get("num_final_videos", 3))
        clips_per_video = int(self.clips_per_video_var.get()) if hasattr(self, "clips_per_video_var") else int(self.settings.get("clips_per_video", 6))
        segment_duration = int(self.segment_duration_var.get()) if hasattr(self, "segment_duration_var") else int(self.settings.get("segment_duration", 8))
        total_moments = final_videos * clips_per_video
        estimated_length = clips_per_video * segment_duration
        self.compilation_preview_label.configure(
            text=f"Output: {final_videos} final MP4 video(s), each with {clips_per_video} viral moment(s) • ~{estimated_length}s each • {total_moments} total moments"
        )

    def _make_action_card(self, parent):
        card = make_card(parent)
        card.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)

        self.generate_button = ctk.CTkButton(
            card,
            text="Generate Compilation Videos",
            height=56,
            corner_radius=16,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["bg"],
            font=("Segoe UI", 16, "bold"),
            command=self.start_pipeline,
        )
        self.generate_button.grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 10))

        self.stop_button = ctk.CTkButton(
            card,
            text="Stop Current Job",
            height=42,
            corner_radius=12,
            fg_color=THEME["card_2"],
            hover_color=THEME["border"],
            text_color=THEME["muted"],
            state="disabled",
            command=self.stop_pipeline,
        )
        self.stop_button.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 14))

        self.progress = ctk.CTkProgressBar(
            card, height=12, corner_radius=999, progress_color=THEME["accent"], fg_color=THEME["border"]
        )
        self.progress.set(0)
        self.progress.grid(row=2, column=0, sticky="ew", padx=22, pady=(2, 10))
        self.progress_label = ctk.CTkLabel(card, text="Ready", text_color=THEME["muted"], font=FONT_SMALL, anchor="w")
        self.progress_label.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 18))

    def _make_results_panel(self, parent):
        card = make_card(parent)
        card.grid(row=3, column=0, sticky="nsew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Final Video Results", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(18, 8)
        )
        self.results_scroll = ctk.CTkScrollableFrame(card, fg_color=THEME["bg"], corner_radius=14)
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.results_scroll.grid_columnconfigure(0, weight=1)
        self.show_empty_results()

    def show_empty_results(self):
        for child in self.results_scroll.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.results_scroll,
            text="Final compilation videos will appear here. Each MP4 contains multiple viral moments stitched together.",
            text_color=THEME["muted"],
            font=FONT_BODY,
            wraplength=560,
        ).grid(row=0, column=0, padx=18, pady=24)

    def render_clip_results(self, results: List[Dict[str, Any]], output_dir: Optional[Path]):
        for child in self.results_scroll.winfo_children():
            child.destroy()
        if not results:
            self.show_empty_results()
            return

        for idx, item in enumerate(results):
            clip = item.get("clip", {})
            path = Path(item.get("path", ""))
            card = ctk.CTkFrame(
                self.results_scroll,
                fg_color=THEME["card"],
                corner_radius=14,
                border_width=1,
                border_color=THEME["border"],
            )
            card.grid(row=idx, column=0, sticky="ew", padx=8, pady=(8 if idx == 0 else 6, 6))
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)

            title = str(clip.get("title", f"Clip {idx + 1}"))
            hook = str(clip.get("hook", "No hook returned."))
            why = str(clip.get("why_viral", "No reason returned."))
            tags = " ".join(clip.get("hashtags", [])) if isinstance(clip.get("hashtags"), list) else str(clip.get("hashtags", ""))
            start = clip.get("start_seconds", "?")
            end = clip.get("end_seconds", "?")

            ctk.CTkLabel(card, text=title, text_color=THEME["text"], font=("Segoe UI", 16, "bold"), anchor="w").grid(
                row=0, column=0, sticky="ew", padx=16, pady=(14, 2)
            )
            ctk.CTkLabel(
                card,
                text=f"{start}s → {end}s  •  {path.name}",
                text_color=THEME["dim"],
                font=FONT_SMALL,
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=16)
            ctk.CTkLabel(card, text=f"Hook: {hook}", text_color=THEME["accent"], font=FONT_SMALL, anchor="w", wraplength=600).grid(
                row=2, column=0, sticky="ew", padx=16, pady=(8, 0)
            )
            ctk.CTkLabel(card, text=f"Why viral: {why}", text_color=THEME["muted"], font=FONT_SMALL, anchor="w", wraplength=600).grid(
                row=3, column=0, sticky="ew", padx=16, pady=(4, 0)
            )
            ctk.CTkLabel(card, text=tags or "#shorts #reels", text_color=THEME["blue"], font=FONT_SMALL, anchor="w", wraplength=600).grid(
                row=4, column=0, sticky="ew", padx=16, pady=(4, 14)
            )

            buttons = ctk.CTkFrame(card, fg_color="transparent")
            buttons.grid(row=0, column=1, rowspan=5, sticky="ns", padx=16, pady=14)
            ctk.CTkButton(
                buttons,
                text="Play",
                width=90,
                height=34,
                corner_radius=10,
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                text_color=THEME["bg"],
                command=lambda p=path: open_path(p),
            ).pack(pady=(0, 8))
            ctk.CTkButton(
                buttons,
                text="Folder",
                width=90,
                height=34,
                corner_radius=10,
                fg_color=THEME["card_2"],
                hover_color=THEME["border"],
                text_color=THEME["text"],
                command=lambda p=output_dir or path.parent: open_path(Path(p)),
            ).pack()

    def _make_system_card(self, parent):
        card = make_card(parent)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="System Status", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(18, 8)
        )
        for index, key in enumerate(["ffmpeg", "ai", "output", "updates"], start=1):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew", padx=18, pady=5)
            row.grid_columnconfigure(1, weight=1)
            dot = status_dot(row, THEME["dim"])
            dot.grid(row=0, column=0, sticky="w")
            label = ctk.CTkLabel(row, text=key.title(), text_color=THEME["text"], font=FONT_BODY, anchor="w")
            label.grid(row=0, column=1, sticky="ew", padx=(8, 0))
            value = ctk.CTkLabel(row, text="Checking", text_color=THEME["muted"], font=FONT_SMALL, anchor="e")
            value.grid(row=0, column=2, sticky="e")
            self.system_rows[key] = (dot, value)
        ctk.CTkButton(
            card,
            text="Refresh Status",
            height=38,
            fg_color=THEME["card_2"],
            hover_color=THEME["border"],
            text_color=THEME["text"],
            corner_radius=12,
            command=self.refresh_status,
        ).grid(row=5, column=0, sticky="ew", padx=18, pady=(12, 18))
        return card

    def _make_activity_card(self, parent):
        card = make_card(parent)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Activity", text_color=THEME["text"], font=FONT_H2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(18, 8)
        )
        self.activity = ctk.CTkTextbox(
            card,
            fg_color=THEME["bg"],
            text_color=THEME["muted"],
            border_width=0,
            corner_radius=12,
            font=FONT_MONO,
            wrap="word",
        )
        self.activity.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.activity.insert("end", "Ready. Paste a YouTube URL and generate your first clips.\n")
        self.activity.configure(state="disabled")
        return card

    def log(self, message: str, tag: str = "dim"):
        symbols = {"ok": "✓", "err": "✕", "warn": "!", "accent": "→", "dim": "•"}
        prefix = f"{symbols.get(tag, '•')} "

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

    def set_progress(self, value: float, text: str):
        def apply():
            self.progress.set(max(0, min(1, value)))
            self.progress_label.configure(text=text)

        self.after(0, apply)

    def set_running(self, running: bool):
        self.running = running
        self.generate_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled", text_color=THEME["danger"] if running else THEME["muted"])

    def open_output_root(self):
        open_path(Path(self.settings.get("output_dir", str(OUTPUT_DIR))))

    def validate_inputs(self) -> Optional[Tuple[str, int, List[int]]]:
        url = self.url_var.get().strip()
        if not url:
            self.show_toast("Paste a YouTube URL first.", "warning")
            return None
        if not check_ffmpeg():
            self.show_toast("ffmpeg was not found. Run setup_ffmpeg.bat or place ffmpeg.exe and ffprobe.exe inside bin.", "error")
            return None
        ready, _message = provider_ready(self.settings)
        if not ready:
            if self.settings.get("ai_provider") == "ollama":
                self.show_toast("Ollama is selected but not running. Start Ollama or choose an API provider in Settings.", "error")
            else:
                provider = PROVIDER_LABELS.get(self.settings.get("ai_provider"), "AI provider")
                self.show_toast(f"{provider} is selected but no API key is saved in Settings.", "error")
            return None
        try:
            final_videos = max(1, min(5, int(self.num_final_videos_var.get())))
            clips_per_video = max(1, min(10, int(self.clips_per_video_var.get())))
            segment_duration = max(3, min(30, int(self.segment_duration_var.get())))
        except ValueError:
            self.show_toast("Compilation values must be valid numbers.", "error")
            return None

        total_moments = final_videos * clips_per_video
        durations = [segment_duration] * total_moments
        self.settings["export_mode"] = "compilation"
        self.settings["num_final_videos"] = final_videos
        self.settings["clips_per_video"] = clips_per_video
        self.settings["segment_duration"] = segment_duration
        self.settings["num_clips"] = total_moments
        self.settings["durations"] = durations[:5]
        self.set_vertical_crop(bool(self.vertical_crop_var.get()), save=False)
        save_settings(self.settings)
        self.update_compilation_preview()
        return url, total_moments, durations

    def start_pipeline(self):
        valid = self.validate_inputs()
        if not valid:
            return
        url, num_clips, durations = valid
        self.remember_recent_url(url)
        self.clear_activity()
        self.show_empty_results()
        self.set_progress(0.03, "Starting...")
        self.set_running(True)
        settings = dict(self.settings)
        output_root = Path(settings["output_dir"])
        threading.Thread(
            target=self.pipeline_thread,
            args=(url, num_clips, durations, settings, output_root),
            daemon=True,
        ).start()

    def stop_pipeline(self):
        self.running = False
        self.log("Stopped by user.", "warn")
        self.set_running(False)
        self.set_progress(0, "Stopped")
        self.show_toast("Current job stopped.", "warning")

    def pipeline_thread(self, url: str, num_clips: int, durations: List[int], settings: Dict[str, Any], output_root: Path):
        try:
            result = run_shortify_pipeline(
                url=url,
                num_clips=num_clips,
                durations=durations,
                settings=settings,
                output_root=output_root,
                log=self.log,
                progress=self.set_progress,
                should_continue=lambda: self.running,
            )
            output_dir = result.get("output_dir")
            results = result.get("results", [])
            self.current_output_dir = Path(output_dir) if output_dir else None
            self.after(0, lambda: self.render_clip_results(results, self.current_output_dir))
            self.after(0, self.refresh_library)
            if results:
                self.after(0, lambda: self.show_toast(f"Generated {len(results)} final video(s) successfully.", "success"))
        except Exception as exc:
            self.set_progress(0, "Failed")
            self.log(str(exc), "err")
            self.after(0, lambda: self.show_toast(f"Shortify error: {exc}", "error", 5200))
        finally:
            self.after(0, lambda: self.set_running(False))
