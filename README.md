<p align="center">
  <img src="./assets/logo.png" width="220" alt="Shortify Logo">
</p>

<h1 align="center">Shortify</h1>

<p align="center">
  Local-first AI desktop app that turns long YouTube videos into compilation-style Shorts.
</p>

<p align="center">
  <b>No login</b> · <b>Modern UI</b> · <b>Ollama / Claude / OpenAI / Gemini</b> · <b>Windows installer ready</b>
</p>

---

## Download & Install

Go to the **Releases** page and download:

```text
Shortify_Setup_v0.6.0.exe
```

Then double-click the installer.

The installer will:

- Install Shortify on your PC.
- Create Start Menu shortcut.
- Optionally create Desktop shortcut.
- Include the required app files.
- Include bundled Python dependencies.
- Include ffmpeg/ffprobe when packaged by the maintainer.

You do not need to clone the repo or run commands to use Shortify.

---

## AI Setup

Shortify needs one AI provider.

You can use:

- Ollama Local
- Claude API key
- OpenAI API key
- Gemini API key

Ollama is optional and is not bundled inside the installer.

During installation, you can choose to open the Ollama download page if you want local AI.

---

## What Shortify Does

Paste a YouTube link and Shortify will:

1. Fetch the transcript.
2. Find viral moments using AI.
3. Download the source video locally.
4. Cut multiple moments with ffmpeg.
5. Merge them into final compilation MP4 videos.
6. Save everything on your PC.

---

## Output Example

```text
shortify_video_1.mp4
shortify_video_2.mp4
shortify_video_3.mp4
```

Each final video contains multiple stitched viral moments.

---

## For Developers

Clone the repo:

```bash
git clone https://github.com/sharjeelx03/Shortify.git
cd Shortify
code .
```

Run development mode:

```bat
run_dev.bat
```

Build app:

```bat
build.bat
```

Build installer:

```bat
build_installer.bat
```

Installer output:

```text
release/Shortify_Setup_v0.6.0.exe
```

---

## GitHub Release Upload

Upload this file to GitHub Releases:

```text
release/Shortify_Setup_v0.6.0.exe
```

Optional:

```text
Shortify_Portable_v0.6.0.zip
```

---

## Project Structure

```text
Shortify/
├─ app/
├─ assets/
├─ bin/
├─ docs/
├─ installer/
├─ release/
├─ requirements.txt
├─ build.bat
├─ build_installer.bat
└─ README.md
```

---

## License

MIT License.
