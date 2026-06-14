# Build Shortify EXE

## Fast way

Run:

```bat
build.bat
```

The output will be:

```text
dist/Shortify/Shortify.exe
```

## ffmpeg

Shortify needs ffmpeg and ffprobe for video processing.

Recommended:

```bat
setup_ffmpeg.bat
build.bat
```

If ffmpeg is already installed on your system PATH, `build.bat` tries to copy `ffmpeg.exe` and `ffprobe.exe` into the `bin/` folder automatically before packaging.

## Development mode

```bat
run_dev.bat
```

## Manual commands

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt
python app\main.py
pyinstaller Shortify.spec --clean --noconfirm
```
