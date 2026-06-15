# Changelog

## v0.7.0

### Performance & Stability
- All ffmpeg and ffprobe subprocess calls now use `CREATE_NO_WINDOW` on Windows — no more console flash or UI freeze from blocking subprocesses.
- All `subprocess.run()` calls now have a `timeout=600` so a stuck ffmpeg can never hang the app forever.
- Default download resolution changed from "best" to **720p** — saves 2–4x memory and download time on low-end PCs.
- Resolution is fully configurable: Auto, 4K, 2K, 1080p, 720p, 480p, 360p — picked right in the Generate page.

### Smart Crop System (replaces old vertical_crop toggle)
- New **crop_mode** setting with 4 options:
  - **Auto-detect (smart)**: inspects source video dimensions with ffprobe — vertical source stays vertical, horizontal stays horizontal.
  - **Always vertical 9:16**: letterbox/pillarbox fit (black bars) — NO destructive zoom crop.
  - **Always horizontal 16:9**: pad to 16:9 with black bars.
  - **Keep original**: no filter applied.
- Horizontal-into-vertical now uses `scale + pad` (black bars) instead of crop-zoom — nothing gets cut off.

### Animated Loading Overlay
- Full-window spinning arc overlay appears during every job.
- Shows: animated lime spinner, current stage label, elapsed time + ETA countdown.
- Cancel button wired to stop_pipeline() — dismisses overlay immediately.

### Social Links in Sidebar
- GitHub, YouTube, and Instagram footer links added to the sidebar.
- Opens in default browser via `webbrowser.open()`.

### ETA & Time Estimation
- Progress label now shows: `[stage] · Xs elapsed · ~Ys left` during jobs.
- LoadingOverlay also updates ETA in real time.

### Settings
- `download_resolution` and `crop_mode` added to DEFAULT_SETTINGS with safe defaults.
- Segment duration slider extended from 30s max → 60s max.
- `SOCIAL_LINKS` dict in settings.py — update your handles once, reflects everywhere.

## v0.6.3
[previous entries unchanged]
