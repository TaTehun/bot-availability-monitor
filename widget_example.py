"""
widget_example.py  -  v1.8

Reference implementation of the desktop widget.
Replace STATUS_DIR with your actual network share path before use.
Layout: pass 4x2 (default), 2x4, 1x7, or 7x1 as the first argument.
"""

import webview
import json
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

STATUS_DIR = Path(r"\\your-server\YourShare\YourFolder\Bot Availability Monitor")
BOTS = ["Bot0", "Bot1", "Bot2", "Bot3", "Bot4", "Bot5", "Bot6"]

# Card size is the same in both layouts; only the grid arrangement changes
LAYOUTS = {
    "4x2": {"cols": 4, "normal": (529, 231), "mini": (347, 109), "initial": (529, 274)},
    "2x4": {"cols": 2, "normal": (272, 397), "mini": (178, 165), "initial": (272, 440)},
    "1x7": {"cols": 1, "normal": (150, 676), "mini": (108, 242), "initial": (166, 719)},
    "7x1": {"cols": 7, "normal": (915, 148), "mini": (420, 58), "initial": (915, 191)},
}
LAYOUT_NAME = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in LAYOUTS else "4x2"
LAYOUT = LAYOUTS[LAYOUT_NAME]

ICON_PATH = os.path.join(os.path.expanduser("~"), "icon_bot_monitor.ico")


def create_icon():
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark monitor background
    draw.rounded_rectangle([2, 2, 61, 61], radius=12, fill=(20, 24, 38, 255))

    # Monitor screen inner area
    draw.rounded_rectangle([8, 8, 55, 50], radius=6, fill=(30, 34, 52, 255))

    # 7 dots: 4 on top, 3 below, representing 7 bots
    green = (34, 197, 94, 255)
    positions = [
        (17, 22), (27, 22), (37, 22), (47, 22),
        (22, 36), (32, 36), (42, 36),
    ]
    for x, y in positions:
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=green)

    # Monitor stand
    draw.rectangle([29, 51, 35, 57], fill=(20, 24, 38, 255))
    draw.rectangle([22, 57, 42, 60], fill=(20, 24, 38, 255))

    img.save(ICON_PATH, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])


prev_status = {bot: None for bot in BOTS}
fail_count = {bot: 0 for bot in BOTS}
last_mtime = {bot: None for bot in BOTS}


class Api:
    def _apply_mtime_guard(self, bot, mtime):
        # SMB cache can move mtime backwards: keep the previous value
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

        # 1. Try reading .json
        if file.exists():
            data = self._read_from(bot, file)
            need_recover = data is None or data["status"] == "OFFLINE"

            if need_recover and tmp.exists():
                try:
                    tmp_mtime = datetime.fromtimestamp(tmp.stat().st_mtime)
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

        # 2. No usable .json: count the failure
        fail_count[bot] += 1

        # 3. 12+ failures: try restoring .json from .tmp
        if fail_count[bot] >= 12 and tmp.exists():
            try:
                shutil.copy2(str(tmp), str(file))
                data = self._read_from(bot, file)
                if data is not None:
                    fail_count[bot] = 0
                    return data
            except Exception:
                pass

        # 4. 1-12 failures: keep prev_status
        if fail_count[bot] <= 12:
            return {"bot": bot, "status": prev_status[bot] or "CALCULATING...", "updated": None, "last_connected": None}
        # 5. 13-19 failures: CALCULATING
        if fail_count[bot] < 20:
            return {"bot": bot, "status": "CALCULATING...", "updated": None, "last_connected": None}
        # 6. 20+ failures: ERROR
        return {"bot": bot, "status": "ERROR", "updated": None, "last_connected": None}

    def get_status(self, reset=False):
        if reset:
            for bot in BOTS:
                prev_status[bot] = None
                last_mtime[bot] = None
                fail_count[bot] = 0
        with ThreadPoolExecutor(max_workers=len(BOTS)) as executor:
            results = list(executor.map(self._read_bot, BOTS))
        return results

    def resize_window(self, mini):
        window.resize(*LAYOUT["mini" if mini else "normal"])

    def minimize_window(self):
        window.minimize()

    def close_window(self):
        window.destroy()


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { overflow: hidden; }
  body {
    font-family: 'Segoe UI', sans-serif;
    background: #1e1e1e;
    color: #eee;
    padding: 10px;
    user-select: none;
  }
  .header {
    font-size: 13px;
    font-weight: 600;
    color: #ddd;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header span { margin-left: 4px; }
  .win-btn {
    font-size: 13px;
    background: transparent;
    color: #aaa;
    border: none;
    width: 22px;
    height: 20px;
    line-height: 20px;
    cursor: pointer;
  }
  .win-btn:hover { background: #333; color: #eee; }
  .win-btn.close-btn:hover { background: #e81123; color: #fff; }
  .win-controls { display: flex; gap: 2px; }
  .mode-btn {
    font-size: 10px;
    background: #333;
    color: #aaa;
    border: none;
    border-radius: 4px;
    padding: 2px 8px;
    cursor: pointer;
  }
  .mode-btn:hover { background: #444; }
  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
  }
  .refresh-time { font-size: 10px; color: #aaa; white-space: nowrap; }
  #list {
    display: grid;
    grid-template-columns: repeat(__COLS__, 1fr);
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

  body.mini { padding: 6px; }
  body.mini .header { margin-bottom: 4px; }
  body.mini #list { grid-template-columns: repeat(__COLS__, 1fr); gap: 4px; }
  body.mini .row { padding: 4px 8px; }
  body.mini .row-top { margin-bottom: 0; }
  body.mini .status,
  body.mini .last-conn { display: none; }
  body.mini .footer { margin-top: 4px; gap: 4px; }
  body.mini .refresh-time { font-size: 9px; }

  /* 1x7 (normal + mini): time stacked under the mode button */
  body.l1x7 .footer { flex-direction: column; align-items: flex-start; gap: 2px; }

  /* 1x7 mini: icons only in header, time stacked under the mode button, tighter spacing */
  body.l1x7.mini { padding: 5px; }
  body.l1x7.mini .header { margin-bottom: 3px; justify-content: center; }
  body.l1x7.mini .header span { display: none; }
  body.l1x7.mini #list { gap: 3px; }
  body.l1x7.mini .row { padding: 3px 6px; }
  body.l1x7.mini .footer { margin-top: 3px; }

  /* 7x1 mini: one top row (title, mode button, time, icons), cards below with "B0" names */
  body.l7x1.mini { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px; padding: 5px; }
  body.l7x1.mini .header, body.l7x1.mini .footer { display: contents; }
  body.l7x1.mini .header span { order: 1; margin-left: 0; }
  body.l7x1.mini .mode-btn { order: 2; }
  body.l7x1.mini .refresh-time { order: 3; }
  body.l7x1.mini .win-controls { order: 4; margin-left: auto; }
  body.l7x1.mini #list { order: 5; width: 100%; gap: 3px; }
  body.l7x1.mini .row { padding: 3px 6px; }
  body.l7x1.mini .ot { display: none; }
</style>
</head>
<body class="__LAYOUT__">
<div class="header">
  <span>Bot Status</span>
  <div class="win-controls">
    <button class="win-btn" onclick="load(true)" title="Refresh">&#8635;</button>
    <button class="win-btn" onclick="window.pywebview.api.minimize_window()">&#8211;</button>
    <button class="win-btn close-btn" onclick="window.pywebview.api.close_window()">&#10005;</button>
  </div>
</div>
<div id="list"></div>
<div class="footer">
  <button class="mode-btn" id="modeBtn" onclick="toggleMini()">Mini ver.</button>
  <span class="refresh-time" id="time"></span>
</div>
<script>
  let mini = false;

  async function load(refreshing = false) {
    try {
      const data = await window.pywebview.api.get_status(refreshing);
      document.getElementById("list").innerHTML = data.map(b => `
        <div class="row">
          <div class="row-top">
            <div class="dot ${b.status}"></div>
            <span class="bot-name">${b.bot.replace('Bot', 'B<span class="ot">OT </span>')}</span>
          </div>
          <div class="status ${b.status.toLowerCase()}">${b.status}</div>
          <div class="last-conn">Updated: ${b.updated ? b.updated.slice(5) : '—'}</div>
          <div class="last-conn">Last use: ${b.last_connected ? b.last_connected.slice(5) : '—'}</div>
        </div>
      `).join("");
      document.getElementById("time").textContent = "Updated: " + new Date().toLocaleTimeString();
    } catch(e) {}
  }

  function toggleMini() {
    mini = !mini;
    document.body.classList.toggle("mini", mini);
    document.getElementById("modeBtn").textContent = mini ? "Origin ver." : "Mini ver.";
    window.pywebview.api.resize_window(mini);
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
    html=HTML.replace("__COLS__", str(LAYOUT["cols"])).replace("__LAYOUT__", "l" + LAYOUT_NAME),
    js_api=api,
    width=LAYOUT["initial"][0],
    height=LAYOUT["initial"][1],
    on_top=True,
    resizable=False,
    frameless=True,
    easy_drag=True,
    min_size=(40, 30),
)
webview.start(icon=ICON_PATH)
