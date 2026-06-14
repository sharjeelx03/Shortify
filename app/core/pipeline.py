from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .providers import analyze_with_provider
from .settings import bundled_binary

LogFn = Callable[[str, str], None]
ProgressFn = Callable[[float, str], None]
ShouldContinueFn = Callable[[], bool]


def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"shorts/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not find a YouTube video ID in that URL.")


def get_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        entries = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        entries = transcripts.find_generated_transcript(["en"]).fetch()

    lines = []
    for item in entries:
        start = int(item["start"])
        lines.append(f"[{start // 60:02d}:{start % 60:02d}] {item['text']}")
    return "\n".join(lines)


def download_video(url: str, out_dir: Path, log: LogFn) -> Path:
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = Path(bundled_binary("ffmpeg"))
    opts: Dict[str, Any] = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "merge_output_format": "mp4",
        "ffmpeg_location": str(ffmpeg_path.parent) if ffmpeg_path.exists() else None,
        "quiet": True,
        "no_warnings": True,
    }
    opts = {key: value for key, value in opts.items() if value is not None}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        log(f"Downloaded source: {info.get('title', '')[:58]}", "ok")

    for ext in ["mp4", "mkv", "webm"]:
        source = out_dir / f"source.{ext}"
        if source.exists():
            return source
    raise FileNotFoundError("Downloaded source file was not found.")


def _vertical_filter() -> str:
    return "crop=w='min(iw,ih*9/16)':h='min(ih,iw*16/9)':x='(iw-out_w)/2':y='(ih-out_h)/2',scale=1080:1920"


def cut_clip(source: Path, start: int, end: int, output: Path, log: LogFn, vertical_crop: bool = True) -> bool:
    duration = max(1, int(end) - int(start))
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        bundled_binary("ffmpeg"),
        "-y",
        "-ss",
        str(int(start)),
        "-i",
        str(source),
        "-t",
        str(duration),
    ]
    if vertical_crop:
        cmd += ["-vf", _vertical_filter()]
    cmd += [
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        mb = output.stat().st_size / 1048576
        log(f"Saved segment {output.name} ({mb:.1f} MB)", "ok")
        return True
    log(f"ffmpeg cut error: {result.stderr[-240:]}", "err")
    return False


def merge_clips(segments: List[Path], output: Path, log: LogFn) -> bool:
    """Merge already-normalized segment files into one final MP4."""
    if not segments:
        log("No segments available to merge.", "err")
        return False

    output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output.with_suffix(".concat.txt")
    lines = []
    for segment in segments:
        safe = str(segment.resolve()).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    copy_cmd = [
        bundled_binary("ffmpeg"),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output),
    ]
    result = subprocess.run(copy_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: re-encode if stream-copy fails for any reason.
        reencode_cmd = [
            bundled_binary("ffmpeg"),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-movflags",
            "+faststart",
            str(output),
        ]
        result = subprocess.run(reencode_cmd, capture_output=True, text=True)

    try:
        concat_file.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode == 0 and output.exists():
        mb = output.stat().st_size / 1048576
        log(f"Merged final video: {output.name} ({mb:.1f} MB)", "ok")
        return True
    log(f"ffmpeg merge error: {result.stderr[-240:]}", "err")
    return False


def safe_filename(title: str) -> str:
    return re.sub(r"[^\w\-]+", "_", title.lower()).strip("_")[:34] or "clip"


def _unique_hashtags(segment_items: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    seen: List[str] = []
    for item in segment_items:
        clip = item.get("clip", {})
        tags = clip.get("hashtags", [])
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
    first_clip = segment_items[0].get("clip", {}) if segment_items else {}
    hooks = [str(item.get("clip", {}).get("hook", "")).strip() for item in segment_items]
    hooks = [hook for hook in hooks if hook]
    titles = [str(item.get("clip", {}).get("title", "")).strip() for item in segment_items]
    titles = [title for title in titles if title]
    title = f"Shortify Video {group_number}"
    if titles:
        title = f"Shortify Video {group_number}: {titles[0][:42]}"
    return {
        "clip_number": group_number,
        "title": title,
        "hook": hooks[0] if hooks else str(first_clip.get("hook", "Compilation of viral moments.")),
        "start_seconds": "multiple",
        "end_seconds": "multiple",
        "duration_seconds": sum(max(1, int(item.get("duration", 0))) for item in segment_items),
        "why_viral": f"A stitched compilation of {len(segment_items)} high-energy moments designed to keep retention moving.",
        "hashtags": _unique_hashtags(segment_items),
        "segments": [item.get("clip", {}) for item in segment_items],
        "output_name": output.name,
    }


def _slice_clips(clips: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [clips[index : index + size] for index in range(0, len(clips), size)]


def _run_separate_clips_mode(
    *,
    clips: List[Dict[str, Any]],
    source: Path,
    out_dir: Path,
    vertical_crop: bool,
    log: LogFn,
    progress: ProgressFn,
    should_continue: ShouldContinueFn,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, start=1):
        if not should_continue():
            break
        title = str(clip.get("title", "clip"))
        clip_number = clip.get("clip_number", idx)
        out_path = out_dir / f"short_{clip_number}_{safe_filename(title)}.mp4"
        ok = cut_clip(source, int(clip["start_seconds"]), int(clip["end_seconds"]), out_path, log, vertical_crop=vertical_crop)
        if ok:
            results.append({"path": str(out_path), "clip": clip, "type": "separate_clip"})
        progress(0.74 + (0.2 * idx / max(1, len(clips))), f"Cutting clip {idx}/{len(clips)}...")
    return results


def _run_compilation_mode(
    *,
    clips: List[Dict[str, Any]],
    source: Path,
    out_dir: Path,
    settings: Dict[str, Any],
    vertical_crop: bool,
    log: LogFn,
    progress: ProgressFn,
    should_continue: ShouldContinueFn,
) -> List[Dict[str, Any]]:
    final_video_count = max(1, min(5, int(settings.get("num_final_videos", 3))))
    clips_per_video = max(1, min(10, int(settings.get("clips_per_video", 6))))
    groups = _slice_clips(clips[: final_video_count * clips_per_video], clips_per_video)
    segment_dir = out_dir / "_segments"
    segment_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    total_segments = sum(len(group) for group in groups)
    processed_segments = 0

    for group_index, group in enumerate(groups, start=1):
        if not should_continue():
            break
        segment_items: List[Dict[str, Any]] = []
        for segment_index, clip in enumerate(group, start=1):
            if not should_continue():
                break
            title = str(clip.get("title", f"moment_{segment_index}"))
            out_path = segment_dir / f"video_{group_index:02d}_moment_{segment_index:02d}_{safe_filename(title)}.mp4"
            start = int(float(clip["start_seconds"]))
            end = int(float(clip["end_seconds"]))
            ok = cut_clip(source, start, end, out_path, log, vertical_crop=vertical_crop)
            if ok:
                segment_items.append({"path": str(out_path), "clip": clip, "duration": max(1, end - start)})
            processed_segments += 1
            progress(
                0.70 + (0.18 * processed_segments / max(1, total_segments)),
                f"Cutting moment {processed_segments}/{total_segments}...",
            )

        if not segment_items:
            continue

        final_path = out_dir / f"shortify_video_{group_index}.mp4"
        if merge_clips([Path(item["path"]) for item in segment_items], final_path, log):
            metadata = _compilation_clip_metadata(group_index, segment_items, final_path)
            results.append(
                {
                    "path": str(final_path),
                    "clip": metadata,
                    "type": "compilation",
                    "segments": segment_items,
                }
            )
        progress(0.88 + (0.10 * group_index / max(1, len(groups))), f"Merged video {group_index}/{len(groups)}...")

    return results


def run_shortify_pipeline(
    *,
    url: str,
    num_clips: int,
    durations: List[int],
    settings: Dict[str, Any],
    output_root: Path,
    log: LogFn,
    progress: ProgressFn,
    should_continue: ShouldContinueFn,
) -> Dict[str, Any]:
    log(f"Provider: {settings.get('ai_provider', 'ollama')}", "dim")
    export_mode = str(settings.get("export_mode", "compilation"))

    if export_mode == "compilation":
        final_video_count = max(1, min(5, int(settings.get("num_final_videos", 3))))
        clips_per_video = max(1, min(10, int(settings.get("clips_per_video", 6))))
        segment_duration = max(3, min(30, int(settings.get("segment_duration", 8))))
        num_clips = final_video_count * clips_per_video
        durations = [segment_duration] * num_clips
        log(f"Export mode: {final_video_count} compilation videos × {clips_per_video} moments", "accent")
    else:
        log(f"Export mode: {num_clips} separate shorts", "accent")

    if not should_continue():
        return {"output_dir": None, "results": []}

    progress(0.08, "Reading YouTube URL...")
    video_id = extract_video_id(url)
    out_dir = output_root / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"Video ID: {video_id}", "dim")

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.18, "Fetching transcript...")
    transcript_file = out_dir / "transcript.txt"
    if transcript_file.exists():
        transcript = transcript_file.read_text(encoding="utf-8")
        log("Transcript loaded from cache.", "dim")
    else:
        transcript = get_transcript(video_id)
        transcript_file.write_text(transcript, encoding="utf-8")
        log("Transcript saved.", "ok")
    log(f"Transcript lines: {len(transcript.splitlines())}", "dim")

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.34, "Asking AI for viral moments...")
    clips = analyze_with_provider(transcript, num_clips, durations, settings)
    clips = clips[:num_clips]
    (out_dir / "clips.json").write_text(json.dumps({"clips": clips}, indent=2), encoding="utf-8")
    log(f"AI found {len(clips)} viral moments.", "ok")

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    progress(0.54, "Downloading source video...")
    source = out_dir / "source.mp4"
    if source.exists():
        log("Source video already exists.", "dim")
    else:
        source = download_video(url, out_dir, log)

    if not should_continue():
        return {"output_dir": out_dir, "results": []}

    vertical_crop = bool(settings.get("vertical_crop", True))
    if export_mode == "compilation":
        progress(0.68, "Cutting and merging compilation videos...")
        results = _run_compilation_mode(
            clips=clips,
            source=source,
            out_dir=out_dir,
            settings=settings,
            vertical_crop=vertical_crop,
            log=log,
            progress=progress,
            should_continue=should_continue,
        )
    else:
        progress(0.74, "Cutting separate clips with ffmpeg...")
        results = _run_separate_clips_mode(
            clips=clips,
            source=source,
            out_dir=out_dir,
            vertical_crop=vertical_crop,
            log=log,
            progress=progress,
            should_continue=should_continue,
        )

    manifest = {
        "video_id": video_id,
        "export_mode": export_mode,
        "num_final_videos": int(settings.get("num_final_videos", 3)),
        "clips_per_video": int(settings.get("clips_per_video", 6)),
        "segment_duration": int(settings.get("segment_duration", 8)),
        "vertical_crop": vertical_crop,
        "results": results,
    }
    (out_dir / "results.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    progress(1.0, f"Done — {len(results)} final video(s) saved")
    log(f"Done. Output folder: {out_dir.resolve()}", "ok")
    return {"output_dir": out_dir, "results": results}
