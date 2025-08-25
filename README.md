# 通用瀏覽器媒體抓取器（圖片/影片）

可在任何平台用 Streamlit 跑的 Web GUI，抓取目標頁面的圖片與影片：支援 Playwright（可選）、縮圖預覽、大小範圍拉霸、排序、全選/取消全選、估算總大小、下載位置記憶與 Win/Mac 快速啟動器。

## 快速開始（懶人安裝）

### Windows
1. 下載或 clone 本專案，進入資料夾。
2. 雙擊 `setup_win.bat`（或在資料夾路徑列輸入 `cmd` -> `setup_win.bat`）。
3. 完成後會自動啟動：`streamlit run app.py`。

### macOS
1. 下載或 clone 本專案，進入資料夾。
2. 在終端機執行並授權腳本：
   ```bash
   chmod +x setup_mac.command
   ./setup_mac.command
   ```
3. 完成後會自動啟動：`streamlit run app.py`。

> 若勾選「使用無頭瀏覽器（Playwright）」第一次會自動安裝瀏覽器引擎，時間較久屬正常。

## 選用：桌面啟動器
App 內建「在桌面建立啟動器 (Win/macOS)」按鈕，可一鍵生成啟動捷徑。

## GitHub 發布教學

### A. 用瀏覽器上傳（最簡單）
1. 到 GitHub 建一個新 repo，例如 `web-media-scraper`。
2. 在 repo 頁面點 **Add file → Upload files**，將以下檔案全部拖進去：
   - `app.py`
   - `requirements.txt`
   - `setup_win.bat`
   - `setup_mac.command`
   - `.gitignore`
   - `README.md`
3. Commit 上去就完成。

### B. 用 Git（命令列）
```bash
git init
git add .
git commit -m "Initial commit: web media scraper"
git branch -M main
git remote add origin https://github.com/<你的帳號>/web-media-scraper.git
git push -u origin main
```

### C. 發佈 zip（可放在 Releases）
1. 先在本機打包：
   ```bash
   zip -r web-media-scraper.zip .
   ```
2. 在 GitHub 專案頁 → **Releases** → **Draft a new release**，上傳 `web-media-scraper.zip` 即可。

## 需求
- Python 3.9+
- （選用）Playwright：`pip install playwright && playwright install`

## 常見問題
- **403/401 被擋**：未勾選 Playwright 時，程式會先用 requests 抓，若 401/403 會自動切到 Playwright 再試一次。
- **Cloudflare/需要登入**：請勾 Playwright，必要時先在 Playwright 視窗登入（可拓展程式加入手動登入流程）。
