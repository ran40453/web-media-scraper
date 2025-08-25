@echo off
chcp 65001 >nul
setlocal enableextensions
echo [Win] 建立虛擬環境與安裝依賴...
python -V || (echo 請先安裝 Python 3.9+ & pause & exit /b)
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements.txt
python -m playwright install
echo 啟動應用程式...
streamlit run app.py
