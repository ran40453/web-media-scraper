@echo off
chcp 65001 >nul
echo [Windows] 建立虛擬環境與安裝依賴...

REM 檢查 Python
python -V >nul 2>&1 || (
  echo 請先安裝 Python 3.9 以上版本
  pause
  exit /b
)

REM 建立虛擬環境
python -m venv .venv
call .venv\Scripts\activate.bat

python -m pip install -U pip
pip install -r requirements.txt
python -m playwright install

echo 啟動應用程式...
streamlit run app.py
pause
