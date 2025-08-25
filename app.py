"""
更新版：通用瀏覽器媒體抓取器（圖片/影片）
-------------------------------------------------
完整版本，包含：
- URL 輸入、圖片/影片格式選擇
- Playwright（可選）與進階瀏覽器選項折疊
- 掃描時置中大型 GIF 提示
- 縮圖預覽、大小（以 KB 浮點數）即時篩選拉霸、排序按鈕
- 全選/取消全選、估算總大小（逐步 HEAD）
- 下載位置自訂＆記憶、跨平台啟動器（Windows/macOS）
"""

import os
import sys
import json
import time
import pathlib
from dataclasses import dataclass
import hashlib
from typing import List, Tuple, Dict, Optional
import platform

# --- Windows asyncio 事件迴圈修正：Playwright 需要 Proactor loop 支援 subprocess ---
import asyncio, sys
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

APP_TITLE = "通用瀏覽器媒體抓取器（圖片/影片）"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".web_media_scraper_gui.json")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
REQUEST_TIMEOUT = 20
MAX_THREADS = 16
CHUNK = 1024 * 128
IMAGE_EXT_DEFAULT = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "svg"]
VIDEO_EXT_DEFAULT = ["mp4", "webm", "mov", "m4v", "avi", "mkv"]

@dataclass
class MediaItem:
    url: str
    kind: str  # "image" or "video"
    filename: str
    size: Optional[int] = None  # bytes
    content_type: str = ""

def fetch_html_playwright(...):
    # 確保在 Windows 下是 Proactor loop（避免 NotImplementedError）
    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    ...

def load_config() -> Dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg: Dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def human_kb(n: Optional[int]) -> str:
    if n is None or n < 0:
        return "—"
    kb = n / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.2f} MB"
    gb = mb / 1024
    return f"{gb:.2f} GB"

# ---- Playwright 渲染（選用）----

def fetch_html_requests(url: str, timeout_sec: int = 20) -> str:
    """以 requests 取得 HTML，帶常見瀏覽器標頭，並允許 302 追蹤。"""
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_sec, allow_redirects=True)
    r.raise_for_status()
    return r.text

def fetch_html_playwright(url: str, channel: Optional[str] = None, exe_path: Optional[str] = None, timeout_sec: int = 40, do_scroll: bool = True) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("請先安裝 Playwright：pip install playwright 並執行 'playwright install'") from e

    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if channel:
            launch_kwargs["channel"] = channel
        browser = p.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(timeout_sec * 1000)
            page.goto(url, wait_until="networkidle")
            if do_scroll:
                for _ in range(6):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(400)
            html = page.content()
            # 存 Referer/Cookie 供之後 HEAD/下載帶入
            try:
                cookies = context.cookies()
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                st.session_state.playwright_cookies = cookie_header
                st.session_state.page_referer = url
            except Exception:
                pass
            return html
        finally:
            browser.close()

# ---- 工具函式 ----

def normalize_url(base_url: str, src: Optional[str]) -> Optional[str]:
    if not src:
        return None
    try:
        u = urljoin(base_url, src)
        p = urlparse(u)
        return p._replace(fragment="").geturl()
    except Exception:
        return None

def head_content_length(url: str) -> Tuple[Optional[int], str]:
    try:
        headers = DEFAULT_HEADERS.copy()
        if st.session_state.get("page_referer"):
            headers["Referer"] = st.session_state.get("page_referer")
        if st.session_state.get("playwright_cookies"):
            headers["Cookie"] = st.session_state.get("playwright_cookies")
        r = requests.head(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if r.status_code >= 400 or "Content-Length" not in r.headers:
            r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
        size = None
        if "Content-Length" in r.headers:
            try:
                size = int(r.headers["Content-Length"])
            except Exception:
                size = None
        ctype = r.headers.get("Content-Type", "")
        return size, ctype
    except Exception:
        return None, ""

def enrich_sizes(items: List[MediaItem]) -> None:
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        fut_map = {ex.submit(head_content_length, it.url): it for it in items}
        for fut in as_completed(fut_map):
            it = fut_map[fut]
            try:
                size, ctype = fut.result()
                it.size = size
                it.content_type = ctype
            except Exception:
                it.size = None
                it.content_type = ""

def download_one(it: MediaItem, folder: str) -> Tuple[str, bool, Optional[int]]:
    try:
        headers = DEFAULT_HEADERS.copy()
        if st.session_state.get("page_referer"):
            headers["Referer"] = st.session_state.get("page_referer")
        if st.session_state.get("playwright_cookies"):
            headers["Cookie"] = st.session_state.get("playwright_cookies")
        resp = requests.get(it.url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
        fname = pathlib.Path(it.filename).name or f"file_{int(time.time())}"
        fpath = os.path.join(folder, fname)
        total_written = 0
        with open(fpath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=CHUNK):
                if not chunk:
                    continue
                f.write(chunk)
                total_written += len(chunk)
        return fpath, True, total_written
    except Exception:
        return it.url, False, None

# ---- 主程式 ----

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    cfg = load_config()

    # Session state 初始化
    for k, v in {
        "media_items": [],              # List[MediaItem]
        "items_df": None,               # DataFrame 檢視
        "scanned": False,
        "size_unit": "KB",
        "spinner_url": "https://media.tenor.com/On7kvXhzml4AAAAj/loading-gif.gif",
        "sort_desc": True,
        "size_range_kb": None,
        "playwright_cookies": "",
        "page_referer": "",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Sidebar
    with st.sidebar:
        st.markdown(f"#### {APP_TITLE}")
        url = st.text_input("🌐", placeholder="輸入網址")
        img_exts = st.multiselect("圖片格式", IMAGE_EXT_DEFAULT, default=IMAGE_EXT_DEFAULT)
        vid_exts = st.multiselect("影片格式", VIDEO_EXT_DEFAULT, default=["mp4", "webm", "mov"])

        use_js = st.checkbox(
            "使用無頭瀏覽器渲染 (Playwright)", value=False,
            help="需要 JS/SPA 的頁面建議開啟（需 pip install playwright 並 playwright install）",
        )
        with st.expander("進階瀏覽器選項（少用時可收起）", expanded=False):
            channel = st.selectbox("瀏覽器 channel（選填）", ["(auto)", "chrome", "msedge"], index=0)
            if channel == "(auto)":
                channel = None
            exe_path = st.text_input("瀏覽器 EXE 路徑（選填）", value="")

        spinner_input = st.text_input("掃描動畫 GIF 連結", value=st.session_state.spinner_url)
        if spinner_input:
            st.session_state.spinner_url = spinner_input.strip()

        download_dir = st.text_input(
            "下載資料夾",
            value=cfg.get("last_download_dir", os.path.join(os.path.expanduser("~"), "Downloads")),
        )
        remember = st.checkbox("記住此下載位置", value=True)
        if st.button("儲存設定"):
            if remember:
                cfg["last_download_dir"] = download_dir
            save_config(cfg)
            st.success("設定已保存")

        st.markdown("---")
        st.markdown("**快速啟動（Windows / macOS）**")
        app_dir_default = pathlib.Path(__file__).resolve().parent.as_posix()
        custom_app_dir = st.text_input("App 資料夾 (預設為此檔案位置)", app_dir_default)
        if st.button("在桌面建立啟動器 (Win/macOS)"):
            try:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                os.makedirs(desktop, exist_ok=True)
                if platform.system() == "Windows":
                    launcher_path = os.path.join(desktop, "通用瀏覽器媒體抓取器.bat")
                    script = f"""@echo off
chcp 65001 >nul
cd /d "{custom_app_dir}"
if exist .venv\\Scripts\\activate.bat (call .venv\\Scripts\\activate.bat)
where streamlit >nul 2>nul
if %errorlevel%==0 (
  start "" cmd /c "streamlit run app.py & pause"
) else (
  start "" cmd /c "python -m streamlit run app.py & pause"
)
"""
                    with open(launcher_path, "w", encoding="utf-8") as f:
                        f.write(script)
                    st.success(f"已建立：{launcher_path}")
                else:  # macOS
                    launcher_path = os.path.join(desktop, "通用瀏覽器媒體抓取器.command")
                    script = f"""#!/bin/bash
cd "{custom_app_dir}"
if [ -d .venv ]; then
  source .venv/bin/activate
fi
if command -v streamlit >/dev/null 2>&1; then
  streamlit run app.py
else
  python3 -m streamlit run app.py
fi
read -n 1 -s -r -p "Press any key to close..."
"""
                    with open(launcher_path, "w") as f:
                        f.write(script)
                    os.chmod(launcher_path, 0o755)
                    st.success(f"已建立：{launcher_path}")
            except Exception as e:
                st.error(f"建立啟動器失敗：{e}")

    # ---- 掃描按鈕 & 流程 ----
    scan_btn = st.button("🔎 掃描媒體")
    center_holder = st.empty()

    if scan_btn:
        if not url:
            st.warning("請輸入網址")
        else:
            with center_holder.container():
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    st.image(st.session_state.spinner_url, caption="正在掃描，請稍候…", width=400)
            try:
                if use_js:
                    html = fetch_html_playwright(url, channel=channel, exe_path=exe_path or None, timeout_sec=40)
                else:
                    try:
                        html = fetch_html_requests(url, timeout_sec=REQUEST_TIMEOUT)
                    except requests.HTTPError as e:
                        status = getattr(e.response, 'status_code', None)
                        if status in (401, 403):
                            st.warning(f"目標網站拒絕直連（HTTP {status}）。已自動改用無頭瀏覽器重試…")
                            html = fetch_html_playwright(url, channel=channel, exe_path=exe_path or None, timeout_sec=40)
                        else:
                            raise
                soup = BeautifulSoup(html, "html.parser")

                found: Dict[str, MediaItem] = {}
                def add_item(u: Optional[str], kind: str):
                    if not u or u in found:
                        return
                    path = urlparse(u).path.lower()
                    if kind == "image":
                        if ("." in path and any(path.endswith("."+ext) for ext in IMAGE_EXT_DEFAULT)) or ("." not in path):
                            filename = pathlib.Path(urlparse(u).path).name or f"image_{hashlib.md5(u.encode()).hexdigest()[:8]}.jpg"
                            found[u] = MediaItem(url=u, kind="image", filename=filename)
                    else:
                        if ("." in path and any(path.endswith("."+ext) for ext in VIDEO_EXT_DEFAULT)) or ("." not in path):
                            filename = pathlib.Path(urlparse(u).path).name or f"video_{hashlib.md5(u.encode()).hexdigest()[:8]}.mp4"
                            found[u] = MediaItem(url=u, kind="video", filename=filename)

                # <img> + srcset
                for img in soup.find_all("img"):
                    add_item(normalize_url(url, img.get("src")), "image")
                    if img.get("srcset"):
                        parts = [s.strip().split(" ")[0] for s in img.get("srcset").split(",") if s.strip()]
                        for p in parts:
                            add_item(normalize_url(url, p), "image")
                # <video> + <source>
                for v in soup.find_all("video"):
                    add_item(normalize_url(url, v.get("src")), "video")
                    for s in v.find_all("source"):
                        add_item(normalize_url(url, s.get("src")), "video")
                # <a href>
                for a in soup.find_all("a"):
                    u = normalize_url(url, a.get("href"))
                    if not u:
                        continue
                    path = urlparse(u).path.lower()
                    if any(path.endswith("."+ext) for ext in IMAGE_EXT_DEFAULT):
                        add_item(u, "image")
                    if any(path.endswith("."+ext) for ext in VIDEO_EXT_DEFAULT):
                        add_item(u, "video")

                items = list(found.values())
                total = len(items)
                if total:
                    prog = st.progress(0)
                    stat = st.empty()
                    batch = 8
                    for i in range(0, total, batch):
                        enrich_sizes(items[i:i+batch])
                        done = min(total, i+batch)
                        total_known = sum((it.size or 0) for it in items)
                        stat.info(f"即將抓取：{done}/{total}，估計總大小：{human_kb(total_known)}")
                        prog.progress(int(done/total*100))

                st.session_state.media_items = items
                st.session_state.scanned = True
            finally:
                center_holder.empty()

    # ---- 結果顯示 ----
    if st.session_state.scanned and st.session_state.media_items:
        items = st.session_state.media_items
        df = pd.DataFrame([
            {
                "ID": i,
                "選取": True,
                "類型": it.kind,
                "縮圖": (it.url if it.kind == "image" else ""),
                "檔名": it.filename,
                "大小_bytes": ((it.size/1024.0) if (it.size is not None) else -1.0),  # 單位：KB（浮點）
                "Content-Type": it.content_type,
                "URL": it.url,
            }
            for i, it in enumerate(items)
        ])
        st.session_state.items_df = df

        sizes_known = [float(s) for s in df["大小_bytes"].tolist() if s is not None and s >= 0]
        kb_min = float(min(sizes_known)) if sizes_known else 0.0
        kb_max = float(max(sizes_known)) if sizes_known else 0.0
        unit = "MB" if kb_max >= 1024 else "KB"

        if st.session_state.size_range_kb is None:
            st.session_state.size_range_kb = (kb_min, kb_max)

        if unit == "MB":
            lo_disp = st.session_state.size_range_kb[0] / 1024.0
            hi_disp = st.session_state.size_range_kb[1] / 1024.0
            lo_disp, hi_disp = st.slider(
                "選取大小範圍",
                min_value=float(kb_min/1024.0),
                max_value=float(max(kb_max/1024.0, kb_min/1024.0 + 0.1)),
                value=(float(lo_disp), float(hi_disp)),
                step=0.1,
                format="%.1f MB",
            )
            lo_kb, hi_kb = lo_disp * 1024.0, hi_disp * 1024.0
        else:
            lo_kb, hi_kb = st.slider(
                "選取大小範圍",
                min_value=float(kb_min),
                max_value=float(max(kb_max, kb_min + 0.1)),
                value=(float(st.session_state.size_range_kb[0]), float(st.session_state.size_range_kb[1])),
                step=0.1,
                format="%.1f KB",
            )
        st.session_state.size_range_kb = (lo_kb, hi_kb)

        def _fmt_kb(v: float) -> str:
            return f"{v:.1f} KB" if v < 1024 else f"{v/1024:.1f} MB"
        st.caption(f"目前範圍：{_fmt_kb(lo_kb)} ～ {_fmt_kb(hi_kb)}")

        df_view = df.copy()
        in_range = (df_view["大小_bytes"] >= lo_kb) & (df_view["大小_bytes"] <= hi_kb)
        df_view.loc[:, "選取"] = in_range

        if st.button(f"按大小排序（{'大→小' if st.session_state.sort_desc else '小→大'}）"):
            st.session_state.sort_desc = not st.session_state.sort_desc
        df_view = df_view.sort_values(by="大小_bytes", ascending=not st.session_state.sort_desc)

        col_all, col_none = st.columns(2)
        with col_all:
            if st.button("全選"):
                df_view.loc[:, "選取"] = True
        with col_none:
            if st.button("取消全選"):
                df_view.loc[:, "選取"] = False

        edited = st.data_editor(
            df_view[["選取", "類型", "縮圖", "檔名", "大小_bytes", "Content-Type", "URL", "ID"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "選取": st.column_config.CheckboxColumn("選取"),
                "縮圖": st.column_config.ImageColumn("縮圖", width=220),
                "大小_bytes": st.column_config.NumberColumn("大小(KB)", format="%.1f"),
                "URL": st.column_config.TextColumn("🔗", width="small"),
                "ID": st.column_config.NumberColumn("ID", format="%d", help="內部索引"),
            },
            num_rows="dynamic",
        )

        sel_mask = edited["選取"] == True
        selected_ids = edited.loc[sel_mask, "ID"].astype(int).tolist()
        sel_items = [items[i] for i in selected_ids]
        total_sel = len(sel_items)
        total_bytes = sum((it.size or 0) for it in sel_items)
        st.info(f"即將下載：{total_sel} 個檔案，總大小 {human_kb(total_bytes)}")

        if st.button("⬇️ 下載已勾選項目"):
            folder = download_dir.strip() or os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(folder, exist_ok=True)
            if remember:
                cfg["last_download_dir"] = folder
                save_config(cfg)
            prog = st.progress(0)
            for idx, it in enumerate(sel_items, start=1):
                path_or_url, ok, bytes_written = download_one(it, folder)
                if ok:
                    st.write(f"✅ {it.filename} ({human_kb(bytes_written)})")
                else:
                    st.write(f"⚠️ 下載失敗：{path_or_url}")
                prog.progress(int(idx/len(sel_items)*100))

if __name__ == "__main__":
    main()
