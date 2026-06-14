# Changelog

## v0.5.1

- Fixed startup crash caused by mixing `pack()` and `grid()` in the Generate page controls.
- Updated sidebar logo loading to prefer `CTkImage` for clean HighDPI rendering.

## v0.5.0

- Added Compilation Mode as the default export workflow.
- Shortify now creates multiple final MP4 videos from one source video.
- Each final video can contain 1–10 stitched viral moments.
- Added controls for Final Videos, Clips / Video, and Moment Length.
- Added ffmpeg concat merge step after cutting individual moments.
- Results now save final compilation videos in the main output folder and helper segments in `_segments/`.
- Updated results.json to include compilation metadata and segment details.

## v0.4.1

- Used `TRANSCRIPT_CHAR_LIMIT` consistently in the provider prompt slice.
- Library Play button now ignores `source.mp4` and plays generated clips only.

## v0.4.0

- Sidebar logo now shows from `assets/logo.png`.
- Library cards show date, size, clip count, format, and clip metadata from `results.json`.
- Added toast/snackbar system.
- Added recent URL chips.
- Split UI pages into submodules.

## v0.2.0

- Rebuilt the desktop UI with CustomTkinter.
- Added modern sidebar navigation: Generate, Library, Settings, Updates.
- Added SaaS-style cards, clean system status, activity feed, and progress bar.
- Moved AI provider/API key controls into a clean Settings page.
- Kept the local-first pipeline: transcript, AI analysis, video download, ffmpeg clipping, local output.

## v0.1.0

- Initial Shortify desktop app structure.
