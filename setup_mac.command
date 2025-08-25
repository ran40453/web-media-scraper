#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "[macOS] 建立虛擬環境與安裝依賴..."
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
pip install -r requirements.txt
python3 -m playwright install
echo "啟動應用程式..."
streamlit run app.py
