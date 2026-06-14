# bin folder

Put video binaries here before making a final Windows release:

```text
bin/ffmpeg.exe
bin/ffprobe.exe
```

You can run this from the project root:

```bat
setup_ffmpeg.bat
```

If ffmpeg is already installed on your Windows PATH, `build.bat` will try to copy `ffmpeg.exe` and `ffprobe.exe` into this folder automatically.

These binaries are required for video downloading, merging, and clipping.
