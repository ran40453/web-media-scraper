@echo off
setlocal enableextensions
chcp 65001 >nul
set "HERE=%~dp0"
cd /d "%HERE%"

echo [Windows] 檢查 Python...
where python >nul 2>nul || (
  echo 未找到 Python。請先安裝 Python 3.9+ 後再重試。
  pause
  exit /b 1
)

echo [Windows] 建立虛擬環境...
python -m venv .venv || (
  echo 建立虛擬環境失敗。
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

echo [Windows] 升級 pip 並安裝需求...
python -m pip install -U pip
pip install -r requirements.txt || (
  echo 安裝 requirements 失敗。
  pause
  exit /b 1
)

echo [Windows] 安裝 Playwright 瀏覽器引擎（可稍久）...
python -m playwright install

echo [Windows] 啟動應用程式...
python -m streamlit run app.py
echo (若視窗立即關閉，請改用 run_win.bat 以保留畫面)
pause
