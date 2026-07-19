# Kills any running garmin_server.py / coach_server.py processes.
#
# Claude Desktop launches these as child processes when it starts, but
# doesn't reliably kill them when the app quits or restarts -- they can be
# left running with old code even after you've pulled a fix. Run this,
# then reopen Claude Desktop so it spawns fresh processes.
#
# Usage: right-click this file -> "Run with PowerShell", or from a terminal:
#   powershell -ExecutionPolicy Bypass -File restart_mcp_servers.ps1

$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*garmin_server*' -or $_.CommandLine -like '*coach_server*'
}

if (-not $targets) {
    Write-Output "No garmin_server/coach_server processes found -- nothing to kill."
} else {
    $targets | ForEach-Object {
        Write-Output "Killing PID $($_.ProcessId): $($_.CommandLine)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Output "Done. Reopen Claude Desktop to relaunch with the current code."
}

Read-Host "Press Enter to close"
