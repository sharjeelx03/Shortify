@echo off
setlocal

echo ==========================================
echo Building Shortify Windows Desktop App
echo ==========================================

where py >nul 2>nul
if %errorlevel%==0 (
  set PY_CMD=py
) else (
  set PY_CMD=python
)

if not exist .venv (
  echo Creating virtual environment...
  %PY_CMD% -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-build.txt

if not exist bin mkdir bin

if not exist bin\ffmpeg.exe (
  for /f "delims=" %%F in ('where ffmpeg 2^>nul') do (
    echo Found system ffmpeg. Copying to bin\ffmpeg.exe...
    copy "%%F" bin\ffmpeg.exe >nul
    goto copied_ffmpeg
  )
)
:copied_ffmpeg

if not exist bin\ffprobe.exe (
  for /f "delims=" %%F in ('where ffprobe 2^>nul') do (
    echo Found system ffprobe. Copying to bin\ffprobe.exe...
    copy "%%F" bin\ffprobe.exe >nul
    goto copied_ffprobe
  )
)
:copied_ffprobe

if not exist bin\ffmpeg.exe (
  echo.
  echo WARNING: bin\ffmpeg.exe not found.
  echo Run setup_ffmpeg.bat or manually place ffmpeg.exe in bin\ before final release.
  echo.
)

if not exist bin\ffprobe.exe (
  echo.
  echo WARNING: bin\ffprobe.exe not found.
  echo Run setup_ffmpeg.bat or manually place ffprobe.exe in bin\ before final release.
  echo.
)

pyinstaller Shortify.spec --clean --noconfirm

echo.
echo Build complete.
echo Output: dist\Shortify\Shortify.exe
echo.
pause
