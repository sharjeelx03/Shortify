@echo off
setlocal

echo ==========================================
echo Shortify ffmpeg Setup
echo ==========================================

echo Checking ffmpeg...
where ffmpeg >nul 2>nul
if %errorlevel%==0 (
  echo ffmpeg already installed on PATH.
) else (
  echo ffmpeg not found.
  echo.
  echo Trying to install ffmpeg using winget...
  winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
)

echo.
echo Creating bin folder...
if not exist bin mkdir bin

if not exist bin\ffmpeg.exe (
  for /f "delims=" %%F in ('where ffmpeg 2^>nul') do (
    echo Copying ffmpeg.exe to bin...
    copy "%%F" bin\ffmpeg.exe >nul
    goto copied_ffmpeg
  )
)
:copied_ffmpeg

if not exist bin\ffprobe.exe (
  for /f "delims=" %%F in ('where ffprobe 2^>nul') do (
    echo Copying ffprobe.exe to bin...
    copy "%%F" bin\ffprobe.exe >nul
    goto copied_ffprobe
  )
)
:copied_ffprobe

echo.
if exist bin\ffmpeg.exe (
  echo ffmpeg.exe is ready in bin\
) else (
  echo WARNING: ffmpeg.exe still missing.
)

if exist bin\ffprobe.exe (
  echo ffprobe.exe is ready in bin\
) else (
  echo WARNING: ffprobe.exe still missing.
)

echo.
echo Done. Now run build.bat
pause
