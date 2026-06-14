@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo ==========================================
echo Building Shortify Windows Desktop App
echo ==========================================

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY_CMD=py -3.13"
) else (
  set "PY_CMD=python"
)

if exist .venv (
  if not exist .venv\Scripts\activate.bat (
    echo Broken virtual environment found. Recreating .venv...
    rmdir /s /q .venv
  )
)

if not exist .venv (
  echo Creating virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo.
    echo Failed to create .venv. Close other terminals and run build.bat again.
    pause
    exit /b 1
  )
)

if not exist .venv\Scripts\activate.bat (
  echo.
  echo .venv activation file missing. Delete .venv and run again.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo.
  echo Failed to activate .venv.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

pip install -r requirements.txt
if errorlevel 1 exit /b 1

pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

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

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller Shortify.spec --clean --noconfirm
if errorlevel 1 (
  echo.
  echo Build failed. dist\Shortify\Shortify.exe was not created.
  pause
  exit /b 1
)

if not exist dist\Shortify\Shortify.exe (
  echo.
  echo Build failed. dist\Shortify\Shortify.exe was not created.
  pause
  exit /b 1
)

echo.
echo Build complete.
echo Output: dist\Shortify\Shortify.exe
echo.
pause
