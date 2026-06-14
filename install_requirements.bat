@echo off
setlocal

echo Installing Shortify requirements...

where py >nul 2>nul
if %errorlevel%==0 (
  set PY_CMD=py
) else (
  set PY_CMD=python
)

if not exist .venv (
  %PY_CMD% -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-build.txt

echo Done.
pause
