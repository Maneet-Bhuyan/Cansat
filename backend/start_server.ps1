$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Virtual environment not found! Please run 'python -m venv .venv' and install requirements." -ForegroundColor Red
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Cognitive CanSat Real-Time ML FastAPI Backend " -ForegroundColor Cyan
Write-Host " Running on http://127.0.0.1:8000 (Docs at /docs)        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Set-Location $RootDir
& $PythonExe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
