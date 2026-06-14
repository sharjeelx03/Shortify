# Prompt for Codex

Use this prompt after opening the Shortify repository in VS Code/Codex:

```text
You are working on Shortify, a local-first open-source Windows desktop app written in Python/Tkinter.

Goal:
Make the app stable, beginner-friendly, and release-ready.

Rules:
- Do not add forced login.
- Do not add a cloud backend.
- Keep video processing local.
- Keep API keys stored locally only.
- Use GitHub only for source code, releases, and update checks.
- The app should support Ollama, Claude, OpenAI, and Gemini as AI providers.
- The app should build into a Windows .exe using PyInstaller.

Start by reviewing the codebase, then improve one feature at a time.
First task:
Audit app/main.py for bugs, missing imports, packaging issues, and UX problems. Then propose a clean improvement plan before editing.
```
