@echo off
setlocal

echo ==========================================
echo Building Shortify Installer
echo ==========================================

if not exist dist\Shortify\Shortify.exe (
  echo Shortify.exe not found. Building app first...
  call build.bat
)

if not exist release mkdir release

set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
  echo.
  echo Inno Setup is not installed.
  echo Install Inno Setup 6, then run this again.
  echo Download: https://jrsoftware.org/isdl.php
  echo.
  pause
  exit /b 1
)

%ISCC% installer\Shortify.iss

echo.
echo Installer ready:
echo release\Shortify_Setup_v0.6.0.exe
echo.
pause
