@echo off
setlocal EnableExtensions
set "HERE=%~dp0"
cd /d "%HERE%"

if not exist ".venv\Scripts\python.exe" (
  echo venv not found. Run setup_win.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py
echo If browser did not open, go to http://localhost:8501
pause
