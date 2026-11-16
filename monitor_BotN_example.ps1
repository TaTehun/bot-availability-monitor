# monitor_BotN_example.ps1
#
# Reference implementation of the bot monitor script.
# Deploy one copy per bot PC via register_task_BotN.bat.
# Replace $botName and $sharePath before use.

$botName  = "BotN"   # e.g. "Bot0", "Bot1", ...
$sharePath = "\\your-server\YourShare\YourFolder\Bot Availability Monitor"
$path      = "$sharePath\$botName.json"

$prevStatus    = ""
$lastConnected = $null
$scriptStamp   = (Get-Item $PSCommandPath).LastWriteTime
$emptyCount    = 0
$emptyLimit    = 6   # 6 x 5s = 30s of no session before AVAILABLE

# Load last_connected from existing file on startup
if (Test-Path $path) {
    try {
        $existing      = Get-Content $path -Encoding UTF8 | ConvertFrom-Json
        $lastConnected = $existing.last_connected
    } catch {}
}

while ($true) {
    $status = "AVAILABLE"

    try {
        # remoting_desktop.exe exists only while a session is connected
        $desktop = Get-Process -Name "remoting_desktop" -ErrorAction SilentlyContinue
        if ($desktop) {
            $status = "IN_USE"
            $emptyCount = 0
        }
        else {
            # Debounce: keep IN_USE through brief gaps (reconnect, lock, session switch)
            $emptyCount++
            if ($prevStatus -eq "IN_USE" -and $emptyCount -lt $emptyLimit) {
                $status = "IN_USE"
            }
        }
    }
    catch {
        $status = "ERROR"
    }

    # Track the moment a session ends
    if ($prevStatus -eq "IN_USE" -and $status -ne "IN_USE") {
        $lastConnected = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    $prevStatus = $status

    # Atomic write: tmp -> rename prevents partial reads by the widget
    try {
        $json = @{
            bot            = $botName
            status         = $status
            updated        = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            last_connected = $lastConnected
        } | ConvertTo-Json

        $tmp = "$path.tmp"
        Set-Content -Path $tmp -Value $json -Encoding UTF8
        Move-Item -Path $tmp -Destination $path -Force
    }
    catch {
        # Write failure: keep looping; stale guard on reader side handles it
    }

    # Script file changed: exit so the 1-minute task trigger relaunches the new version
    if ((Get-Item $PSCommandPath).LastWriteTime -ne $scriptStamp) { exit }

    Start-Sleep -Seconds 5
}
