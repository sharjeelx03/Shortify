<p align="center">
  <img src="./assets/logo.png" width="200" alt="Shortify Logo">
</p>

<h1 align="center">Shortify</h1>

<p align="center">
  Local-first AI desktop app that turns long YouTube videos into compilation-style Shorts.
</p>

<p align="center">
  <b>No login</b> · <b>Windows UI</b> · <b>Ollama / Claude / OpenAI / Gemini</b>
</p>

---

## Download

Go to **Releases** and download:

```text
Shortify_Setup_v0.6.2.exe
```

Double-click it and install Shortify like a normal Windows app.

No terminal commands are required for normal users.

---

## Installer Includes

- Shortify desktop app
- Required Python app dependencies bundled by PyInstaller
- ffmpeg / ffprobe if packaged by the maintainer
- Start Menu shortcut
- Optional Desktop shortcut
- Uninstaller

Ollama is **not bundled**. During setup, users can choose to open the Ollama download page.

---

## AI Options

Shortify needs one AI provider:

- Ollama for local AI
- Claude API key
- OpenAI API key
- Gemini API key

Use Ollama for local mode. Use API keys if you do not want Ollama.

---

## What It Does

1. Paste a YouTube link.
2. Shortify finds viral moments with AI.
3. It cuts and merges moments into final Shorts.
4. Videos are saved locally on your PC.

Example output:

```text
shortify_video_1.mp4
shortify_video_2.mp4
shortify_video_3.mp4
```

---

## For Developers

```bat
run_dev.bat
build.bat
build_installer.bat
```

Installer output:

```text
release/Shortify_Setup_v0.6.2.exe
```

---

## License

MIT License.
