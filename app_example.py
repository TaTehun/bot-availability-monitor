"""
app_example.py

Reference implementation of the FastAPI web dashboard.
Replace STATUS_DIR with your actual network share path before use.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
from datetime import datetime

app = FastAPI()

STATUS_DIR = Path(r"\\your-server\YourShare\YourFolder\Bot Availability Monitor")
BOTS = ["Bot0", "Bot1", "Bot2", "Bot3", "Bot4", "Bot5"]


def read_bot(bot):
    file = STATUS_DIR / f"{bot}.json"
    if not file.exists():
        return {"bot": bot, "status": "OFFLINE", "updated": None, "last_connected": None}
    try:
        data = json.loads(file.read_text(encoding="utf-8-sig"))
        updated = datetime.strptime(data["updated"], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - updated).total_seconds() > 30:
            data["status"] = "OFFLINE"
        data.setdefault("last_connected", None)
        return data
    except:
        return {"bot": bot, "status": "ERROR", "updated": None, "last_connected": None}


@app.get("/api/status")
def status():
    return [read_bot(b) for b in BOTS]


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bot Availability Monitor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: #f0f2f5; padding: 40px; }
        h1 { font-size: 22px; color: #333; margin-bottom: 8px; }
        .subtitle { font-size: 13px; color: #888; margin-bottom: 30px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            max-width: 720px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px 20px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .card-header { font-size: 16px; font-weight: bold; color: #333; }
        .status-row { display: flex; align-items: center; gap: 8px; }
        .dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
        .dot.available { background: #22c55e; }
        .dot.inuse     { background: #ef4444; }
        .dot.offline   { background: #9ca3af; }
        .dot.error     { background: #f97316; }
        .status-text { font-size: 14px; font-weight: 600; }
        .available { color: #22c55e; }
        .inuse     { color: #ef4444; }
        .offline   { color: #9ca3af; }
        .error     { color: #f97316; }
        .updated        { font-size: 11px; color: #aaa; }
        .last-connected { font-size: 11px; color: #bbb; }
        .message { font-size: 12px; color: #555; background: #f8f8f8; border-radius: 6px; padding: 6px 10px; }
        .refresh-btn { margin-top: 24px; padding: 10px 24px; background: #333; color: white; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; }
        .refresh-btn:hover { background: #555; }
        .last-refresh { margin-top: 10px; font-size: 12px; color: #aaa; }
    </style>
</head>
<body>
    <h1>Bot Availability Monitor</h1>
    <p class="subtitle">Real-time availability monitor for Bot PCs based on Google Remote Desktop session detection</p>

    <div class="grid" id="grid"></div>

    <br>
    <button class="refresh-btn" onclick="load()">Refresh</button>
    <div class="last-refresh" id="last-refresh"></div>

    <script>
        const MESSAGES = {
            AVAILABLE: "Available for use",
            IN_USE: "Currently in use via Remote Desktop",
            OFFLINE: "Bot is offline or not responding",
            ERROR: "Unable to read status"
        };

        function getClass(status) {
            if (status === "AVAILABLE") return "available";
            if (status === "IN_USE") return "inuse";
            if (status === "OFFLINE") return "offline";
            return "error";
        }

        async function load() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();
                const grid = document.getElementById("grid");

                grid.innerHTML = data.map(b => {
                    const cls = getClass(b.status);
                    const msg = MESSAGES[b.status] || b.status;
                    const updated = b.updated ? `Last updated: ${b.updated}` : "";
                    const lastConn = b.last_connected ? `Last connected: ${b.last_connected}` : "Last connected: —";
                    return `
                        <div class="card">
                            <div class="card-header">${b.bot}</div>
                            <div class="status-row">
                                <div class="dot ${cls}"></div>
                                <span class="status-text ${cls}">${b.status}</span>
                            </div>
                            <div class="message">${msg}</div>
                            <div class="updated">${updated}</div>
                            <div class="last-connected">${lastConn}</div>
                        </div>
                    `;
                }).join("");

                document.getElementById("last-refresh").textContent =
                    "Last refreshed: " + new Date().toLocaleTimeString();
            } catch (e) {
                console.error(e);
            }
        }

        load();
        setInterval(load, 10000);
    </script>
</body>
</html>
"""
