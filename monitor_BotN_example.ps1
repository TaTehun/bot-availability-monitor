# monitor_BotN_example.ps1
#
# Reference implementation of the bot monitor script.
# Deploy one copy per bot PC via register_task_BotN.bat.
# Replace $botName and $sharePath before use.

$botName  = "BotN"   # e.g. "Bot0", "Bot1", ...
$sharePath = "\\your-server\YourShare\YourFolder\Bot Availability Monitor"
$path      = "$sharePath\$botName.json"

$prevStatus   = ""
$lastConnected = $null

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
        $processes = Get-Process -Name "remoting_host" -ErrorAction SilentlyContinue

        if ($processes) {
            $pids = $processes | Select-Object -ExpandProperty Id
            $conn = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue |
                Where-Object { $pids -contains $_.OwningProcess }

            if ($conn) {
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

    # Atomic write: tmp → rename prevents partial reads by the widget
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
        # Write failure — keep looping; stale guard on reader side handles it
    }

    Start-Sleep -Seconds 5
}
