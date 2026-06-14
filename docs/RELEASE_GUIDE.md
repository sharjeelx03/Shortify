# Shortify Release Guide

## User download flow

Users should not clone the repo or run commands.

They should:

1. Open the GitHub Releases page.
2. Download `Shortify_Setup_v0.6.0.exe`.
3. Double-click the setup file.
4. Complete installation.
5. Launch Shortify from Desktop or Start Menu.

## What the installer includes

The installer includes the built Shortify app, Python runtime dependencies bundled by PyInstaller, assets, and ffmpeg/ffprobe when they are copied into `bin/` before build.

The installer does not install Ollama automatically.

During installation, the user can choose:

- I already have Ollama installed.
- I will use Claude / OpenAI / Gemini API keys instead.
- Open Ollama download page after installation.

## Build release files

Developer commands:

```bat
build.bat
build_installer.bat
```

Upload this file to GitHub Releases:

```text
release/Shortify_Setup_v0.6.0.exe
```

Optional portable upload:

```text
dist/Shortify/
```

Zip the `dist/Shortify` folder as `Shortify_Portable_v0.6.0.zip`.
