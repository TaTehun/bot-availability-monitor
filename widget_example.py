"""
widget_example.py  —  v1.7

Reference implementation of the desktop widget.
Replace STATUS_DIR with your actual network share path before use.
"""

import webview
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

STATUS_DIR = Path(r"\\your-server\YourShare\YourFolder\Bot Availability Monitor")
BOTS = ["Bot0", "Bot1", "Bot2", "Bot3", "Bot4", "Bot5"]

ICON_PATH = os.path.join(os.path.expanduser("~"), "icon_grd.ico")


def create_icon():
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([2, 2, 61, 61], radius=12, fill=(20, 24, 38, 255))
    draw.rounded_rectangle([8, 8, 55, 50], radius=6, fill=(30, 34, 52, 255))

    green = (34, 197, 94, 255)
    positions = [
        (22, 22), (32, 22), (42, 22),
        (22, 36), (32, 36), (42, 36),
    ]
    for x, y in positions:
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=green)

    draw.rectangle([29, 51, 35, 57], fill=(20, 24, 38, 255))
    draw.rectangle([22, 57, 42, 60], fill=(20, 24, 38, 255))

    img.save(ICON_PATH, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])


prev_status = {bot: None for bot in BOTS}
fail_count = {bot: 0 for bot in BOTS}
last_mtime = {bot: None for bot in BOTS}


class Api:
    def _apply_mtime_guard(self, bot, mtime):
        if last_mtime[bot] and mtime < last_mtime[bot]:
            return last_mtime[bot]
        last_mtime[bot] = mtime
        return mtime

    def _read_from(self, bot, path):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            mtime = self._apply_mtime_guard(bot, mtime)
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if (datetime.now() - mtime).total_seconds() > 90:
                data["status"] = "OFFLINE"
            prev_status[bot] = data["status"]
            data["updated"] = mtime.strftime("%Y-%m-%d %H:%M:%S")
            return data
        except Exception:
            return None

    def _read_bot(self, bot):
        file = STATUS_DIR / f"{bot}.json"
        tmp  = STATUS_DIR / f"{bot}.json.tmp"

        # 1. .json 읽기 시도
        if file.exists():
            data = self._read_from(bot, file)
            need_recover = data is None or data["status"] == "OFFLINE"

            if need_recover and tmp.exists():
                try:
                    tmp_mtime  = datetime.fromtimestamp(tmp.stat().st_mtime)
                    json_mtime = datetime.fromtimestamp(file.stat().st_mtime) if file.exists() else None
                except Exception:
                    tmp_mtime, json_mtime = None, None

                if tmp_mtime and (json_mtime is None or tmp_mtime > json_mtime):
                    try:
                        os.replace(str(tmp), str(file))
                        recovered = self._read_from(bot, file)
                        if recovered is not None:
                            fail_count[bot] = 0
                            return recovered
                    except Exception:
                        pass

            if data is not None:
                fail_count[bot] = 0
                return data

        # 2. .json 없으면 fail_count 누적
        fail_count[bot] += 1

        # 3. 12회 이상이면 .tmp → .json 복구 시도
        if fail_count[bot] >= 12 and tmp.exists():
            try:
                shutil.copy2(str(tmp), str(file))
                data = self._read_from(bot, file)
                if data is not None:
                    fail_count[bot] = 0
                    return data
            except Exception:
                pass

        # 4. 1~12회 → prev_status 유지
        if fail_count[bot] <= 12:
            return {"bot": bot, "status": prev_status[bot] or "CALCULATING...", "updated": None, "last_connected": None}
        # 5. 13~19회 → CALCULATING
        if fail_count[bot] < 20:
            return {"bot": bot, "status": "CALCULATING...", "updated": None, "last_connected": None}
        # 6. 20회 이상 → ERROR
        return {"bot": bot, "status": "ERROR", "updated": None, "last_connected": None}

    def get_status(self, reset=False):
        if reset:
            for bot in BOTS:
                prev_status[bot] = None
                last_mtime[bot] = None
                fail_count[bot] = 0
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(self._read_bot, BOTS))
        return results


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', sans-serif;
    background: #1e1e1e;
    color: #eee;
    padding: 10px;
    user-select: none;
    overflow-y: auto;
  }
  .header {
    font-size: 11px;
    color: #888;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .refresh-btn {
    font-size: 10px;
    background: #333;
    color: #aaa;
    border: none;
    border-radius: 4px;
    padding: 2px 8px;
    cursor: pointer;
  }
  .refresh-btn:hover { background: #444; }
  .refresh-time { font-size: 10px; color: #555; margin-top: 6px; text-align: right; }
  #list {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
  }
  .row {
    border-radius: 6px;
    background: #2a2a2a;
    padding: 8px;
  }
  .row-top {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }
  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .AVAILABLE { background: #22c55e; }
  .IN_USE { background: #ef4444; }
  .OFFLINE { background: #555; }
  .ERROR { background: #f97316; }
  .bot-name { font-size: 12px; font-weight: 600; }
  .status { font-size: 10px; color: #aaa; }
  .last-conn { font-size: 9px; color: #888; margin-top: 2px; }
</style>
</head>
<body>
<div class="header">
  <span>Bot Status</span>
  <button class="refresh-btn" onclick="load(true)">Refresh</button>
</div>
<div id="list"></div>
<div class="refresh-time" id="time"></div>
<script>
  async function load(refreshing = false) {
    try {
      const data = await window.pywebview.api.get_status(refreshing);
      document.getElementById("list").innerHTML = data.map(b => `
        <div class="row">
          <div class="row-top">
            <div class="dot ${b.status}"></div>
            <span class="bot-name">${b.bot.replace('Bot', 'BOT ')}</span>
          </div>
          <div class="status ${b.status.toLowerCase()}">${b.status}</div>
          <div class="last-conn">Updated: ${b.updated ? b.updated.slice(5) : '—'}</div>
          <div class="last-conn">Last use: ${b.last_connected ? b.last_connected.slice(5) : '—'}</div>
        </div>
      `).join("");
      document.getElementById("time").textContent = "Updated: " + new Date().toLocaleTimeString();
    } catch(e) {}
  }

  let started = false;
  function init() {
    if (started) return;
    started = true;
    load();
    setInterval(load, 5000);
  }

  if (window.pywebview) {
    init();
  } else {
    window.addEventListener("pywebviewready", init);
    setTimeout(() => { if (window.pywebview) init(); }, 1000);
  }
</script>
</body>
</html>
"""

if not os.path.exists(ICON_PATH):
    try:
        create_icon()
    except Exception:
        ICON_PATH = None

api = Api()
window = webview.create_window(
    "Bot Status",
    html=HTML,
    js_api=api,
    width=400,
    height=280,
    on_top=True,
    resizable=False,
)
webview.start(icon=ICON_PATH)
