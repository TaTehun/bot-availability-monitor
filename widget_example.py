"""
widget_example.py

Reference implementation of the desktop widget.
Replace STATUS_DIR with your actual network share path before use.
"""

import webview
import json
import os
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
last_connected_cache = {bot: None for bot in BOTS}
fail_count = {bot: 0 for bot in BOTS}


class Api:
    def _read_bot(self, bot):
        file = STATUS_DIR / f"{bot}.json"
        tmp  = STATUS_DIR / f"{bot}.json.tmp"

        # .json 없으면 .tmp fallback 시도
        if not file.exists():
            if tmp.exists():
                file = tmp
            else:
                fail_count[bot] += 1
                status = "OFFLINE" if fail_count[bot] >= 3 else (prev_status[bot] or "OFFLINE")
                return {"bot": bot, "status": status, "updated": None, "last_connected": last_connected_cache[bot]}

        try:
            fail_count[bot] = 0
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            data = json.loads(file.read_text(encoding="utf-8-sig"))
            if (datetime.now() - mtime).total_seconds() > 30:
                data["status"] = "OFFLINE"
            if last_connected_cache[bot] is None:
                last_connected_cache[bot] = data.get("last_connected")
            if prev_status[bot] == "IN_USE" and data["status"] != "IN_USE":
                last_connected_cache[bot] = mtime.strftime("%Y-%m-%d %H:%M:%S")
            prev_status[bot] = data["status"]
            data["updated"] = mtime.strftime("%Y-%m-%d %H:%M:%S")
            data["last_connected"] = last_connected_cache[bot]
            return data
        except:
            # .json 읽기 실패(잠금 등) 시 .tmp fallback
            if tmp.exists():
                try:
                    mtime = datetime.fromtimestamp(tmp.stat().st_mtime)
                    data = json.loads(tmp.read_text(encoding="utf-8-sig"))
                    if (datetime.now() - mtime).total_seconds() > 30:
                        data["status"] = "OFFLINE"
                    prev_status[bot] = data["status"]
                    data["updated"] = mtime.strftime("%Y-%m-%d %H:%M:%S")
                    data["last_connected"] = last_connected_cache[bot]
                    return data
                except:
                    pass
            return {"bot": bot, "status": "ERROR", "updated": None, "last_connected": last_connected_cache[bot]}

    def get_status(self):
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
  <button class="refresh-btn" onclick="load()">Refresh</button>
</div>
<div id="list"></div>
<div class="refresh-time" id="time"></div>
<script>
  async function load() {
    try {
      const data = await window.pywebview.api.get_status();
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
