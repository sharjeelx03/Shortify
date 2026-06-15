from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

APP_NAME = "Shortify"
APP_VERSION = "0.6.3"
GITHUB_REPO = "sharjeelx03/Shortify"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"
GITHUB_RELEASES_URL = f"{GITHUB_URL}/releases/latest"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

THEME = {
    "bg": "#09090B",
    "sidebar": "#0D0D10",
    "card": "#111113",
    "card_2": "#161618",
    "border": "#262626",
    "accent": "#C8FF00",
    "accent_hover": "#B8EB00",
    "text": "#F5F5F5",
    "muted": "#A1A1AA",
    "dim": "#52525B",
    "success": "#22C55E",
    "warning": "#EAB308",
    "danger": "#EF4444",
    "blue": "#38BDF8",
}

FONT_TITLE = ("Segoe UI", 30, "bold")
FONT_H1 = ("Segoe UI", 23, "bold")
FONT_H2 = ("Segoe UI", 17, "bold")
FONT_BODY = ("Segoe UI", 14)
FONT_SMALL = ("Segoe UI", 12)
FONT_MONO = ("Consolas", 12)

PROVIDER_LABELS = {
    "ollama": "Ollama Local",
    "claude": "Claude API",
    "openai": "OpenAI / GPT",
    "gemini": "Gemini API",
}
PROVIDER_FROM_LABEL = {v: k for k, v in PROVIDER_LABELS.items()}


def resource_path(relative: str) -> Path:
    """Return a PyInstaller-safe resource path."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / relative


def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


SETTINGS_FILE = app_data_dir() / "settings.json"
OUTPUT_DIR = Path.home() / "Shortify_Output"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "ai_provider": "ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2:3b",
    "claude_api_key": "",
    "claude_model": "claude-sonnet-4-6",
    "openai_api_key": "",
    "openai_model": "gpt-4.1-mini",
    "gemini_api_key": "",
    "gemini_model": "gemini-1.5-flash",
    "output_dir": str(OUTPUT_DIR),
    "num_clips": 3,
    "durations": [60, 45, 30, 30, 30],
    "export_mode": "compilation",
    "num_final_videos": 3,
    "clips_per_video": 6,
    "segment_duration": 8,
    "vertical_crop": True,
    "burn_subtitles": False,
    "transcript_char_limit": 20000,
    "auto_check_updates": True,
    "recent_urls": [],
}


def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            user_settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**DEFAULT_SETTINGS, **user_settings}
            durations = list(merged.get("durations", [60, 45, 30, 30, 30]))
            while len(durations) < 5:
                durations.append(30)
            merged["durations"] = durations[:5]
            return merged
        except Exception:
            return dict(DEFAULT_SETTINGS)
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: Dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def version_tuple(version: str) -> Tuple[int, ...]:
    version = version.lower().lstrip("v").split("-")[0]
    parts = []
    for piece in version.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def bundled_binary(name: str) -> str:
    exe_name = name + (".exe" if os.name == "nt" else "")
    candidates = [
        resource_path(f"bin/{exe_name}"),
        Path(__file__).resolve().parents[2] / "bin" / exe_name,
        Path.cwd() / "bin" / exe_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return exe_name


def check_ffmpeg() -> bool:
    try:
        return subprocess.run(
            [bundled_binary("ffmpeg"), "-version"],
            capture_output=True,
            text=True,
            timeout=6,
        ).returncode == 0
    except Exception:
        return False
