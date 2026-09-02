# Cognitive CanSat Mission Control - PowerShell Launcher
Write-Host =============================================================================== -ForegroundColor Cyan
Write-Host  COGNITIVE CANSAT MISSION CONTROL - SYSTEM LAUNCHER  -ForegroundColor Cyan
Write-Host =============================================================================== -ForegroundColor Cyan
Write-Host "

 = Split-Path -Parent System.Management.Automation.InvocationInfo.MyCommand.Path
Set-Location 

# Auto-clear port 8000 if in use
 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if () {
 Write-Host [i] Clearing port 8000 used by PID ... -ForegroundColor Yellow
 Stop-Process -Id .OwningProcess -Force -ErrorAction SilentlyContinue
}

 = Join-Path .venv\Scripts\python.exe
if (-not (Test-Path )) {
 Write-Warning [!] .venv not found at . Falling back to system python.
 = python
}

Write-Host [1/2] Opening Mission Control Dashboard in browser... -ForegroundColor Green
Start-Process http://127.0.0.1:8000/

Write-Host [2/2] Launching Ground Station Backend on Port 8000... -ForegroundColor Green
Write-Host Press Ctrl + C in this window to stop the server anytime. -ForegroundColor Yellow
Write-Host 

& -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
