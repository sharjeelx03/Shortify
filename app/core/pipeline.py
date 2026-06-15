from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .providers import analyze_with_provider, validate_clip_payload
from .settings import RESOLUTION_HEIGHT, bundled_binary

LogFn            = Callable[[str, str], None]
ProgressFn       = Callable[[float, str], None]
ShouldContinueFn = Callable[[], bool]

_WIN_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


# ── YouTube helpers ─────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str:
    for pattern in [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"shorts/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError("Could not find a YouTube video ID in that URL.")


def validate_youtube_url(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        raise ValueError("Paste a YouTube URL first.")
    if "youtube.com" not in url and "youtu.be" not in url:
        raise ValueError("Use a valid YouTube link, e.g. https://www.youtube.com/watch?v=VIDEO_ID")
    return extract_video_id(url)


# ── Transcript ───────────────────────────────────────────────────────────────

def _format_transcript_entries(entries: Any) -> str:
    if hasattr(entries, "to_raw_data"):
        entries = entries.to_raw_data()
    lines = []
    for item in entries:
        if isinstance(item, dict):
            start = int(float(item.get("start", 0)))
            text  = str(item.get("text", "")).strip()
        else:
            start = int(float(getattr(item, "start", 0)))
            text  = str(getattr(item, "text", "")).strip()
        if text:
            lines.append(f"[{start // 60:02d}:{start % 60:02d}] {text}")
    if not lines:
        raise ValueError("Transcript was found but it was empty.")
    return "\n".join(lines)


def get_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi
    langs  = ["en", "en-US", "en-GB"]
    errors: List[str] = []

    try:
        return _format_transcript_entries(YouTubeTranscriptApi().fetch(video_id, languages=langs))
    except Exception as exc:
        errors.append(str(exc))

    try:
        tl = YouTubeTranscriptApi().list(video_id)
        for finder in [tl.find_transcript, tl.find_generated_transcript, tl.find_manually_created_transcript]:
            try:
                return _format_transcript_entries(finder(langs).fetch())
            except Exception as exc:
                errors.append(str(exc))
        for t in tl:
            try:
                return _format_transcript_entries(t.fetch())
            except Exception as exc:
                errors.append(str(exc))
    except Exception as exc:
        errors.append(str(exc))

    for method in ["get_transcript", "list_transcripts"]:
        if hasattr(YouTubeTranscriptApi, method):
            try:
                if method == "get_transcript":
                    return _format_transcript_entries(
                        YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
                    )
                else:
                    ts = YouTubeTranscriptApi.list_transcripts(video_id)
                    for fn in ["find_transcript", "find_generated_transcript"]:
                        try:
                            return _format_transcript_entries(getattr(ts, fn)(langs).fetch())
                        except Exception as exc:
                            errors.append(str(exc))
            except Exception as exc:
                errors.append(str(exc))

    raise RuntimeError("Could not fetch transcript. " + (errors[-1] if errors else "No API succeeded."))


# ── Download ─────────────────────────────────────────────────────────────────

def _build_yt_format(resolution_label: str) -> str:
    height = RESOLUTION_HEIGHT.get(resolution_label)
    if height is None:
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    h = height
    return (
        f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={h}]+bestaudio"
        f"/best[height<={h}][ext=mp4]"
        f"/best[height<={h}]"
        f"/best"
    )


def get_video_dimensions(source: Path) -> Optional[tuple]:
    try:
        result = subprocess.run(
            [
                bundled_binary("ffprobe"), "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0", str(source),
            ],
            capture_output=True, text=True, timeout=15,
            creationflags=_WIN_FLAGS,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None


def download_video(url: str, out_dir: Path, log: LogFn, resolution_label: str = "720p") -> Path:
    import yt_dlp
    version     = getattr(yt_dlp, "version", None)
    version_txt = getattr(version, "__version__", "unknown")
    log(f"yt-dlp {version_txt} · resolution cap: {resolution_label}", "dim")
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = Path(bundled_binary("ffmpeg"))
    opts: Dict[str, Any] = {
        "format":              _build_yt_format(resolution_label),
        "outtmpl":             str(out_dir / "source.%(ext)s"),
        "merge_output_format": "mp4",
        "ffmpeg_location":     str(ffmpeg_path.parent) if ffmpeg_path.exists() else None,
        "quiet":               True,
        "no_warnings":         True,
    }
    opts = {k: v for k, v in opts.items() if v is not None}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        log(f"Downloaded: {info.get('title', '')[:58]}", "ok")
    for ext in ["mp4", "mkv", "webm"]:
        src = out_dir / f"source.{ext}"
        if src.exists():
            return src
    raise FileNotFoundError("Downloaded source file was not found.")


# ── Video filters ─────────────────────────────────────────────────────────────

def _resolve_crop_mode(crop_mode: str, source: Path) -> str:
    if crop_mode != "auto":
        return crop_mode
    dims = get_video_dimensions(source)
    if dims is None:
        return "original"
    w, h = dims
    return "force_vertical" if h > w else "original"


def _build_crop_filter(resolved_mode: str) -> Optional[str]:
    if resolved_mode == "force_vertical":
        return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    if resolved_mode == "force_horizontal":
        return "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    return None


def _escape_drawtext(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:120]
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _video_filter(crop_filter: Optional[str], burn_subtitles: bool, subtitle_text: str = "") -> Optional[str]:
    filters: List[str] = []
    if crop_filter:
        filters.append(crop_filter)
    if burn_subtitles and subtitle_text:
        caption = _escape_drawtext(subtitle_text)
        filters.append(
            "drawtext="
            f"text='{caption}':"
            "x=(w-text_w)/2:y=h-(text_h*4):"
            "fontsize=54:fontcolor=white:"
            "box=1:boxcolor=black@0.55:boxborderw=18"
        )
    return ",".join(filters) if filters else None


# ── ffmpeg ────────────────────────────────────────────────────────────────────

def _run_ffmpeg(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600, creationflags=_WIN_FLAGS)


def _run_ffmpeg_cut(source: Path, start: int, duration: int, output: Path, vf: Optional[str]) -> subprocess.CompletedProcess:
    cmd = [bundled_binary("ffmpeg"), "-y", "-ss", str(int(start)), "-i", str(source), "-t", str(duration)]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast", "-crf", "23", "-movflags", "+faststart", str(output)]
    return _run_ffmpeg(cmd)


def cut_clip(source: Path, start: int, end: int, output: Path, log: LogFn,
             crop_filter: Optional[str] = None, burn_subtitles: bool = False, subtitle_text: str = "") -> bool:
    duration = max(1, int(end) - int(start))
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = _video_filter(crop_filter, burn_subtitles, subtitle_text)
    result = _run_ffmpeg_cut(source, int(start), duration, output, vf)
    if result.returncode != 0 and burn_subtitles:
        log("Subtitle burn-in failed; retrying without subtitles.", "warn")
        result = _run_ffmpeg_cut(source, int(start), duration, output, crop_filter)
    if result.returncode == 0 and output.exists():
        mb = output.stat().st_size / 1048576
        log(f"Saved {output.name} ({mb:.1f} MB)", "ok")
        return True
    log(f"ffmpeg cut error: {result.stderr[-240:]}", "err")
    return False


def merge_clips(segments: List[Path], output: Path, log: LogFn) -> bool:
    if not segments:
        log("No segments to merge.", "err")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output.with_suffix(".concat.txt")
    concat_file.write_text("\n".join(f"file '{s.resolve().as_posix()}'" for s in segments), encoding="utf-8")
    base = [bundled_binary("ffmpeg"), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-movflags", "+faststart"]
    result = _run_ffmpeg(base + ["-c", "copy", str(output)])
    if result.returncode != 0:
        result = _run_ffmpeg(base + ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast", "-crf", "23", str(output)])
    try:
        concat_file.unlink(missing_ok=True)
    except Exception:
        pass
    if result.returncode == 0 and output.exists():
        mb = output.stat().st_size / 1048576
        log(f"Merged → {output.name} ({mb:.1f} MB)", "ok")
        return True
    log(f"ffmpeg merge error: {result.stderr[-240:]}", "err")
    return False


# ── Filename helpers ──────────────────────────────────────────────────────────

def safe_filename(title: str) -> str:
    return re.sub(r"[^\w\-]+", "_", title.lower()).strip("_")[:34] or "clip"


def unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 1000):
        c = path.with_name(f"{stem}_{i}{suffix}")
        if not c.exists():
            return c
    raise FileExistsError(f"Could not create unique filename for {path.name}")


def _unique_hashtags(segment_items: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    seen: List[str] = []
    for item in segment_items:
        tags = item.get("clip", {}).get("hashtags", [])
        if isinstance(tags, str):
            tags = tags.split()
        if not isinstance(tags, list):
            continue
        for tag in tags:
            tag = str(tag).strip()
            if tag and tag not in seen:
                seen.append(tag)
            if len(seen) >= limit:
                return seen
    return seen or ["#shorts", "#reels", "#viral"]


def _compilation_clip_metadata(group_number: int, segment_items: List[Dict[str, Any]], output: Path) -> Dict[str, Any]:
    first  = segment_items[0].get("clip", {}) if segment_items else {}
    hooks  = [str(i.get("clip", {}).get("hook",  "")).strip() for i in segment_items if i.get("clip", {}).get("hook")]
    titles = [str(i.get("clip", {}).get("title", "")).strip() for i in segment_items if i.get("clip", {}).get("title")]
    title  = f"Shortify Video {group_number}" + (f": {titles[0][:42]}" if titles else "")
    return {
        "clip_number":      group_number,
        "title":            title,
        "hook":             hooks[0] if hooks else str(first.get("hook", "Compilation.")),
        "start_seconds":    "multiple",
        "end_seconds":      "multiple",
        "duration_seconds": sum(max(1, int(i.get("duration", 0))) for i in segment_items),
        "why_viral":        f"Stitched compilation of {len(segment_items)} high-energy moments.",
        "hashtags":         _unique_hashtags(segment_items),
        "segments":         [i.get("clip", {}) for i in segment_items],
        "output_name":      output.name,
    }


def _slice_clips(clips: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [clips[i: i + size] for i in range(0, len(clips), size)]


# ── Export modes ──────────────────────────────────────────────────────────────

def _run_separate_clips_mode(*, clips, source, out_dir, crop_filter, burn_subtitles, log, progress, should_continue) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not should_continue():
            break
        title    = str(clip.get("title", "clip"))
        out_path = unique_output_path(out_dir / f"short_{clip.get('clip_number', idx)}_{safe_filename(title)}.mp4")
        ok = cut_clip(source, int(clip["start_seconds"]), int(clip["end_seconds"]), out_path, log,
                      crop_filter=crop_filter, burn_subtitles=burn_subtitles,
                      subtitle_text=str(clip.get("hook") or title))
        if ok:
            results.append({"path": str(out_path), "clip": clip, "type": "separate_clip"})
        progress(0.74 + 0.20 * idx / max(1, len(clips)), f"Cutting clip {idx}/{len(clips)}…")
    return results


def _run_compilation_mode(*, clips, source, out_dir, settings, crop_filter, burn_subtitles, log, progress, should_continue) -> List[Dict[str, Any]]:
    final_count   = max(1, min(5,  int(settings.get("num_final_videos", 3))))
    clips_per_vid = max(1, min(10, int(settings.get("clips_per_video",  6))))
    groups        = _slice_clips(clips[: final_count * clips_per_vid], clips_per_vid)
    segment_dir   = out_dir / "_segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    total_segs, done_segs = sum(len(g) for g in groups), 0

    for g_idx, group in enumerate(groups, 1):
        if not should_continue():
            break
        seg_items: List[Dict[str, Any]] = []
        for s_idx, clip in enumerate(group, 1):
            if not should_continue():
                break
            title    = str(clip.get("title", f"moment_{s_idx}"))
            out_path = unique_output_path(segment_dir / f"video_{g_idx:02d}_moment_{s_idx:02d}_{safe_filename(title)}.mp4")
            start, end = int(float(clip["start_seconds"])), int(float(clip["end_seconds"]))
            ok = cut_clip(source, start, end, out_path, log, crop_filter=crop_filter,
                          burn_subtitles=burn_subtitles, subtitle_text=str(clip.get("hook") or title))
            if ok:
                seg_items.append({"path": str(out_path), "clip": clip, "duration": max(1, end - start)})
            done_segs += 1
            progress(0.70 + 0.18 * done_segs / max(1, total_segs), f"Cutting moment {done_segs}/{total_segs}…")

        if not seg_items:
            continue
        final_path = unique_output_path(out_dir / f"shortify_video_{g_idx}.mp4")
        if merge_clips([Path(i["path"]) for i in seg_items], final_path, log):
            results.append({"path": str(final_path), "clip": _compilation_clip_metadata(g_idx, seg_items, final_path),
                            "type": "compilation", "segments": seg_items})
        progress(0.88 + 0.10 * g_idx / max(1, len(groups)), f"Merged video {g_idx}/{len(groups)}…")
    return results


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_shortify_pipeline(*, url, num_clips, durations, settings, output_root, log, progress, should_continue) -> Dict[str, Any]:
    log(f"Provider: {settings.get('ai_provider', 'ollama')}", "dim")
    export_mode = str(settings.get("export_mode", "compilation"))
    crop_mode   = str(settings.get("crop_mode", "auto"))
    resolution  = str(settings.get("download_resolution", "720p"))

    if export_mode == "compilation":
        fv  = max(1, min(5,  int(settings.get("num_final_videos", 3))))
        cpv = max(1, min(10, int(settings.get("clips_per_video",  6))))
        sd  = max(3, min(60, int(settings.get("segment_duration", 8))))
        num_clips = fv * cpv
        durations = [sd] * num_clips
        log(f"Export: {fv} compilation videos × {cpv} moments", "accent")
    else:
        log(f"Export: {num_clips} separate shorts", "accent")

    if not should_continue():
        return {"output_dir": None, "results": []}

    progress(0.08, "Validating URL…")
    video_id = validate_youtube_url(url)
    out_dir  = output_root / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.16, "Fetching transcript…")
    tf = out_dir / "transcript.txt"
    if tf.exists():
        transcript = tf.read_text(encoding="utf-8")
        log("Transcript loaded from cache.", "dim")
    else:
        transcript = get_transcript(video_id)
        tf.write_text(transcript, encoding="utf-8")
        log("Transcript saved.", "ok")

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.30, "Asking AI for viral moments…")
    clips = analyze_with_provider(transcript, num_clips, durations, settings)
    clips = validate_clip_payload(clips, num_clips, durations)[:num_clips]
    if len(clips) < num_clips:
        log(f"AI returned {len(clips)}/{num_clips} usable moments.", "warn")
    (out_dir / "clips.json").write_text(json.dumps({"clips": clips}, indent=2), encoding="utf-8")
    log(f"AI found {len(clips)} viral moments.", "ok")

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.50, f"Downloading video ({resolution})…")
    source = out_dir / "source.mp4"
    if source.exists():
        log("Source video already cached.", "dim")
    else:
        source = download_video(url, out_dir, log, resolution_label=resolution)

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.62, "Detecting video dimensions…")
    resolved_mode = _resolve_crop_mode(crop_mode, source)
    log(f"Crop mode: {crop_mode} → {resolved_mode}", "dim")
    crop_filter   = _build_crop_filter(resolved_mode)
    burn_subtitles = bool(settings.get("burn_subtitles", False))

    if export_mode == "compilation":
        progress(0.68, "Cutting and merging compilation videos…")
        results = _run_compilation_mode(clips=clips, source=source, out_dir=out_dir, settings=settings,
                                        crop_filter=crop_filter, burn_subtitles=burn_subtitles,
                                        log=log, progress=progress, should_continue=should_continue)
    else:
        progress(0.74, "Cutting separate clips…")
        results = _run_separate_clips_mode(clips=clips, source=source, out_dir=out_dir,
                                           crop_filter=crop_filter, burn_subtitles=burn_subtitles,
                                           log=log, progress=progress, should_continue=should_continue)

    manifest = {
        "video_id": video_id, "export_mode": export_mode,
        "num_final_videos": int(settings.get("num_final_videos", 3)),
        "clips_per_video":  int(settings.get("clips_per_video",  6)),
        "segment_duration": int(settings.get("segment_duration", 8)),
        "crop_mode": crop_mode, "resolved_crop": resolved_mode,
        "resolution": resolution, "burn_subtitles": burn_subtitles,
        "results": results,
    }
    (out_dir / "results.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    progress(1.0, f"Done — {len(results)} final video(s) saved")
    log(f"Output folder: {out_dir.resolve()}", "ok")
    return {"output_dir": out_dir, "results": results}