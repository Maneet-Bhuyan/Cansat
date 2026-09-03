# Cognitive CanSat Mission Control - PowerShell Launcher
$ErrorActionPreference = "Continue"

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "             COGNITIVE CANSAT MISSION CONTROL - SYSTEM LAUNCHER                " -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# 1. Check for .venv Python
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$PythonExe = $null

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host "[OK] Using virtual environment Python: $PythonExe" -ForegroundColor Green
} else {
    # Check system python
    $SysPy = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $SysPy) {
        $SysPy = Get-Command "py" -ErrorAction SilentlyContinue
    }
    if ($SysPy) {
        Write-Host "[i] Initializing local virtual environment (.venv)..." -ForegroundColor Yellow
        & $SysPy.Source -m venv (Join-Path $ScriptDir ".venv")
        if (Test-Path $VenvPython) {
            Write-Host "[i] Installing required ML dependencies..." -ForegroundColor Yellow
            & $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt")
            $PythonExe = $VenvPython
        } else {
            $PythonExe = $SysPy.Source
        }
    }
}

# 2. If Python is still not found, launch Native Standalone Mode
if (-not $PythonExe) {
    Write-Host "[!] Python was not detected on this system." -ForegroundColor Yellow
    Write-Host "[i] Starting Mission Control in Native Windows Standalone Mode (Zero Dependencies)..." -ForegroundColor Green
    & (Join-Path $ScriptDir "backend\standalone_server.ps1")
    exit 0
}

# 3. Auto-clear port 8000 if in use
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $pids) {
        Write-Host "[i] Clearing port 8000 used by PID $p..." -ForegroundColor Yellow
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 600
}

# 4. Launch Mission Control via Python Launcher
Write-Host "[i] Launching FastAPI backend & Ground Station..." -ForegroundColor Green
& $PythonExe (Join-Path $ScriptDir "launch.py")
