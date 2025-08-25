@echo off
setlocal EnableExtensions
set "HERE=%~dp0"
cd /d "%HERE%"

rem Check python/py
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python not found. Install Python 3.9+ with "Add to PATH".
    pause
    exit /b 1
  )
)

rem Create venv if missing
if not exist ".venv\Scripts\python.exe" (
  where python >nul 2>nul && python -m venv .venv
  if errorlevel 1 (
    py -3 -m venv .venv
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo Failed to create venv.
  pause
  exit /b 1
)

set "VPY=.venv\Scripts\python.exe"

echo [setup] upgrade pip and install requirements...
"%VPY%" -m pip install -U pip
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements.
  pause
  exit /b 1
)

echo [setup] install Playwright browsers (can take a while)...
"%VPY%" -m playwright install

echo [setup] launch app...
"%VPY%" -m streamlit run app.py
echo If browser did not open, go to http://localhost:8501
pause
