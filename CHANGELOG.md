# Changelog

## v0.6.3

- Increased default transcript analysis window to 20,000 characters.
- Added user-controlled transcript character limit in Settings.
- Added AI JSON validation before ffmpeg cuts any video.
- Added retry logic for Ollama, Claude, OpenAI, and Gemini responses.
- Scaled AI output token limits based on requested clip count.
- Added early YouTube URL validation.
- Added friendlier provider/error messages for common failures.
- Improved Windows-safe ffmpeg concat path handling.
- Added collision-safe output filenames so old exports are not overwritten.
- Added visible warning for locally stored API keys.
- Logged yt-dlp version/source during downloads for debugging.
- Added retry prompts for placeholder/generic AI outputs.
- Added unit tests for parsing, validation, URL extraction, and filename helpers.
- Added elapsed/estimated remaining time in the progress label.
- Replaced Moment Length dropdown with a slider.
- Added optional hook subtitle burn-in for exported videos.

## v0.6.2

- Reduced Ollama prompt size to avoid local 4k-context failures.
- Default Ollama model changed to `llama3.2:3b`.
- Added Ollama JSON mode for more reliable clip metadata.
- Improved Ollama error messages so the real server response is shown.

## v0.6.1

- Added proper Windows installer script using Inno Setup.
- Added `build_installer.bat` for generating `Shortify_Setup_v0.6.1.exe`.
- Updated README for user-first download/install flow.
- Added installer AI setup page for Ollama/API-key choice.
- Installer can open Ollama download page after install.
- App version bumped to 0.6.1.

## v0.5.3
- Fixed transcript fetching for youtube-transcript-api v1.x by using `YouTubeTranscriptApi().fetch()` and `list()` while keeping old API fallback compatibility.
- Fixed packaged EXE startup error: `No module named ui`.
- Switched internal imports to package-safe `app.*` imports.
- Updated PyInstaller spec to include app packages explicitly.

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
