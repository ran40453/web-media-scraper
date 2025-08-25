@echo off
setlocal enableextensions
set "HERE=%~dp0"
cd /d "%HERE%"

echo [Windows] 檢查 Python / py 啟動器...
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo 未找到 python 或 py 指令。請先安裝 Python 3.9+ 並勾選 "Add to PATH"。
    pause
    exit /b 1
  )
)

echo [Windows] 建立虛擬環境 .venv...
where python >nul 2>nul && python -m venv .venv
if errorlevel 1 (
  echo python 建 venv 失敗，改用 py -3...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo 建 venv 仍失敗，請截圖錯誤訊息。
    pause
    exit /b 1
  )
)

REM 後續一律用 venv 的 python
set "VPY=.venv\Scripts\python.exe"

echo [Windows] 安裝依賴...
"%VPY%" -m pip install -U pip
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo 安裝 requirements 失敗，請檢查網路/Proxy。
  pause
  exit /b 1
)

echo [Windows] 安裝 Playwright 瀏覽器引擎（可能較久）...
"%VPY%" -m playwright install

echo [Windows] 啟動應用程式...
"%VPY%" -m streamlit run app.py

echo (若沒有自動開瀏覽器，手動前往 http://localhost:8501)
pause
