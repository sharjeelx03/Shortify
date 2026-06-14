@echo off
setlocal

echo ==========================================
echo Running Shortify in Development Mode
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
python app\main.py
