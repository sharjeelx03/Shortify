@echo off
setlocal EnableExtensions

echo ==========================================
echo Building Shortify Installer
echo ==========================================

if not exist dist\Shortify\Shortify.exe (
  echo Shortify.exe not found. Building app first...
  call build.bat
)

if not exist release mkdir release

set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe") do (
  if exist "%%~P" set "ISCC=%%~P"
)

if not defined ISCC (
  for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$paths=@($env:LOCALAPPDATA+'\Programs','C:\Program Files','C:\Program Files (x86)'); $x=Get-ChildItem $paths -Filter ISCC.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName; if($x){Write-Output $x}"`) do set "ISCC=%%I"
)

if not defined ISCC (
  echo.
  echo Inno Setup compiler not found.
  echo Install Inno Setup 6 or run ISCC.exe manually.
  echo.
  pause
  exit /b 1
)

echo Using Inno Setup: %ISCC%
"%ISCC%" "installer\Shortify.iss"

if errorlevel 1 (
  echo.
  echo Installer build failed.
  pause
  exit /b 1
)

echo.
echo Installer ready:
echo release\Shortify_Setup_v0.6.2.exe
echo.
pause
