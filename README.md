# Bot Availability Monitor

Real-time availability board for 7 shared bot PCs. Each PC reports whether a Chrome Remote Desktop session is connected; a desktop widget and a web dashboard show who is free.

> **Visual overview:** [project-overview.html](project-overview.html)

---

## How it works

1. `monitor_BotN.ps1` runs on each bot PC every 5 seconds via Task Scheduler
2. `IN_USE` while `remoting_desktop.exe` exists; held for 30s (6 polls) after it disappears so reconnects and screen locks don't flicker
3. Status is written atomically (`BotN.json.tmp` -> `BotN.json`) to a network share
4. The widget and web dashboard read all 7 files in parallel and mark a file older than the stale threshold as `OFFLINE`
5. Editing the script makes it exit; the 1-minute task trigger relaunches the new version

---

## Files

```
bot-availability-monitor/
├── monitor_BotN_example.ps1   # Bot PC status writer (session detection + debounce)
├── widget_example.py          # Desktop widget (pywebview), 4 layouts + mini mode
├── app_example.py             # Web dashboard (FastAPI)
├── test_widget.py             # Widget read-logic tests
└── project-overview.html      # Visual overview
```

Replace `STATUS_DIR` / `$sharePath` with your network share before use.

---

## Widget

```
pythonw widget_example.py 4x2   # default: 4 columns
pythonw widget_example.py 2x4
pythonw widget_example.py 1x7   # vertical strip
pythonw widget_example.py 7x1   # horizontal strip
```

Requires `pywebview` and `pillow`. **Mini ver.** button shrinks the window; **Origin ver.** restores it.

| Color | Status | Meaning |
|-------|--------|---------|
| Green | AVAILABLE | No session for 30s |
| Red | IN_USE | Remote Desktop session connected |
| Gray | OFFLINE | Status file stale or missing |
| Orange | ERROR | Status file unreadable |

---

## Changelog

### v1.8 · 2026-11-16 · Session detection, debounce, layouts
- Detect sessions from `remoting_desktop.exe` instead of `remoting_host` + TCP matching
- 30s debounce on `IN_USE`
- Monitor script exits on file change; task trigger relaunches it every minute
- 7 bots (Bot0~Bot6)
- 4x2 / 2x4 / 1x7 / 7x1 layouts, mini mode, frameless window with custom controls
