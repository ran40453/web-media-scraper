@echo off
setlocal enableextensions
set "HERE=%~dp0"
cd /d "%HERE%"

if not exist ".venv\Scripts\python.exe" (
  echo 找不到虛擬環境 .venv，請先執行 setup_win.bat 完成安裝。
  pause
  exit /b 1
)

REM 啟動就直接用 venv 的 python，避免吃到系統 Python
".venv\Scripts\python.exe" -m streamlit run app.py

echo (若沒有自動開瀏覽器，手動前往 http://localhost:8501)
pause
