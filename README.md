<p align="center">
  <img src="./assets/logo.png" width="220" alt="Shortify Logo">
</p>

<h1 align="center">Shortify</h1>

<p align="center">
  Open-source modern local AI desktop app that turns long YouTube videos into compilation-style Shorts.
</p>

<p align="center">
  <b>Modern UI</b> · <b>Local-first</b> · <b>No login</b> · <b>Ollama / Claude / OpenAI / Gemini</b> · <b>Windows .exe ready</b>
</p>

---

## What is Shortify?

Shortify is a modern desktop app for creators. Paste a YouTube link, choose an AI provider, and Shortify will:

1. Fetch the transcript.
2. Ask AI to find multiple viral moments.
3. Download the video locally.
4. Cut each selected moment locally with ffmpeg.
5. Merge those moments into final compilation MP4 videos.
6. Save the results on your PC.

No login and no cloud backend are required.

---

## Modern UI

Shortify now uses a clean CustomTkinter dashboard instead of the older raw Tkinter layout.

Main UI sections:

- Generate — paste URL, choose provider, set final video count, clips per video, and moment length.
- Library — view generated output folders.
- Settings — configure Ollama, Claude, OpenAI, Gemini, output folder, and update checks.
- Updates — check GitHub Releases for newer versions.

---

## Quick Start

After copying this repo into your GitHub folder, run:

```bat
run_dev.bat
```

To build the Windows desktop app:

```bat
build.bat
```

Output:

```text
dist/Shortify/Shortify.exe
```

---

## Clone in VS Code

```bash
git clone https://github.com/sharjeelx03/Shortify.git
cd Shortify
code .
```

If your repo is empty, extract this project ZIP and copy all files into the cloned `Shortify` folder.

Then push:

```bash
git add .
git commit -m "Release Shortify v0.5.1"
git push origin main
```

---

## Development Mode

Windows:

```bat
run_dev.bat
```

Manual:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app\main.py
```

---

## ffmpeg Requirement

Shortify needs `ffmpeg` and `ffprobe` for video download, cutting, and merging final compilation videos.

Recommended setup:

```bat
setup_ffmpeg.bat
build.bat
```

If ffmpeg is already installed on your PC, `build.bat` will try to copy it into:

```text
bin/ffmpeg.exe
bin/ffprobe.exe
```

For final release builds, these files should be present in the `bin/` folder so PyInstaller can bundle them.

---

## Build Windows .exe

```bat
build.bat
```

Output:

```text
dist/Shortify/Shortify.exe
```

Shortify uses PyInstaller in `--onedir` style because it works cleaner with video binaries like ffmpeg.

---

## AI Providers

Shortify supports:

- Ollama Local
- Claude API
- OpenAI / GPT API
- Gemini API

At least one provider must be available to generate clips.

API keys are saved locally in the user's app data folder, not in GitHub.

---

## GitHub Update Checker

Shortify checks this endpoint:

```text
https://api.github.com/repos/sharjeelx03/Shortify/releases/latest
```

If a newer release exists, it shows an update notification and opens the release download page.

---

## Project Structure

```text
Shortify/
├─ app/
│  ├─ main.py
│  └─ __init__.py
├─ assets/
│  ├─ logo.png
│  ├─ banner.png
│  └─ icon.ico
├─ bin/
│  ├─ .gitkeep
│  └─ README.md
├─ docs/
│  ├─ BUILD_EXE.md
│  ├─ CODEX_PROMPT.md
│  ├─ GITHUB_SETUP.md
│  └─ ROADMAP.md
├─ installer/
│  └─ Shortify.iss
├─ scripts/
│  └─ create_release_zip.py
├─ tests/
│  └─ README.md
├─ requirements.txt
├─ requirements-build.txt
├─ run_dev.bat
├─ build.bat
├─ setup_ffmpeg.bat
├─ install_requirements.bat
├─ Shortify.spec
├─ README.md
├─ LICENSE
├─ CONTRIBUTING.md
├─ CHANGELOG.md
├─ START_HERE.txt
└─ GIT_COMMANDS.txt
```

---

## License

MIT License.
