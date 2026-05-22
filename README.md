# GBD Bot Availability Monitor - Widget Guide  (v1.7)

## Requirements
- Python installed
- Connected to company network or VPN

## Setup & Launch
1. Save `widget.py` and `widget.bat` in the same folder
2. Double-click `widget.bat`

Required packages (pywebview, pillow) will be installed automatically on first run.

## Features
- Real-time status of 6 bots (Bot0~Bot5)
- Auto-refreshes every 5 seconds
- Manual refresh via Refresh button
- Always on top

## Status Indicators
| Color | Status | Description |
|-------|--------|-------------|
| Green | AVAILABLE | Ready to use |
| Red | IN_USE | Currently connected via Remote Desktop |
| Gray | OFFLINE | Offline or not responding |
| Orange | ERROR | Failed to read status |

## Exit
Open Task Manager and terminate `pythonw.exe`
