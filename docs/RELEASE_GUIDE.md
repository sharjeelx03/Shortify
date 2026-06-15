# Shortify Release Guide

## User Download Flow

Users should download only this file from GitHub Releases:

```text
Shortify_Setup_v0.6.3.exe
```

They double-click it, install the app, and open Shortify from the Desktop or Start Menu.

## Build Release

```bat
build.bat
build_installer.bat
```

Installer output:

```text
release/Shortify_Setup_v0.6.3.exe
```

## Upload to GitHub

Upload this file under **GitHub → Releases → Create a new release**.

Do not upload `.venv`, `build`, or `dist` to the repo.

## Ollama

Ollama is optional and not bundled. The installer can open the Ollama download page if the user wants local AI.
