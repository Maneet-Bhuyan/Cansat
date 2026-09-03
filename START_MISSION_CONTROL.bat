@echo off
setlocal enabledelayedexpansion
title Cognitive CanSat Mission Control - System Launcher
color 0B
cd /d "%~dp0"

echo ===============================================================================
echo                 COGNITIVE CANSAT MISSION CONTROL LAUNCHER
echo ===============================================================================
echo.

:: 1. Check if virtual environment already exists and has dependencies
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import uvicorn, fastapi" 2>nul
    if !errorlevel! equ 0 (
        echo [OK] Verified Python virtual environment. Launching Mission Control...
        ".venv\Scripts\python.exe" launch.py
        goto :eof
    )
)

:: 2. Check for system Python (python.exe or py.exe)
set "SYSTEM_PYTHON="
for %%P in (python.exe py.exe) do (
    where %%P >nul 2>&1
    if !errorlevel! equ 0 if not defined SYSTEM_PYTHON (
        set "SYSTEM_PYTHON=%%P"
    )
)

:: 3. If system Python is available, auto-create venv and install dependencies
if defined SYSTEM_PYTHON (
    echo [i] Python detected on system: !SYSTEM_PYTHON!
    if not exist ".venv\Scripts\python.exe" (
        echo [i] Initializing local virtual environment (.venv)...
        !SYSTEM_PYTHON! -m venv .venv
    )
    if exist ".venv\Scripts\python.exe" (
        echo [i] First-time setup: Installing required machine learning dependencies...
        echo     (FastAPI, Uvicorn, scikit-learn, PyOD, NumPy, Pandas)
        ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
        ".venv\Scripts\python.exe" -m pip install -r requirements.txt
        echo.
        echo [OK] Setup completed successfully! Launching Mission Control...
        ".venv\Scripts\python.exe" launch.py
        goto :eof
    )
)

:: 4. If Python is NOT found on this machine
echo [!] Python was not detected on this system.
echo.
echo Select how you would like to run Mission Control:
echo.
echo   [1] INSTANT NATIVE MODE (Recommended - Zero Installation Needed)
echo       Runs directly in your browser using native Windows tools.
echo       Full 3D attitude model, GPS tracking, telemetry charts,
echo       Web Serial API hardware link, and 10 flight test profiles all work.
echo.
echo   [2] AUTOMATICALLY INSTALL PYTHON 3.11
echo       Installs Python 3.11 via Windows Package Manager (winget) to enable
echo       the Python FastAPI ML server and scikit-learn models.
echo.
set "USER_CHOICE=1"
set /p "USER_CHOICE=Enter choice [1 or 2] (Default is 1): "

if "%USER_CHOICE%"=="2" (
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        echo [i] Installing Python 3.11 via winget...
        winget install -e --id Python.Python.3.11 --scope user
        echo.
        echo [i] Python installation initiated! Please restart START_MISSION_CONTROL.bat when complete.
        pause
        goto :eof
    ) else (
        echo [!] winget is not available on this Windows version.
        echo Falling back to Instant Native Mode...
        timeout /t 2 >nul
    )
)

:: 5. Instant Native Mode: Run native Windows PowerShell HTTP server
echo.
echo [i] Starting Mission Control in Native Windows Mode...
powershell -ExecutionPolicy Bypass -File "%~dp0backend\standalone_server.ps1"
if !errorlevel! neq 0 (
    echo [i] Launching dashboard directly in default browser...
    start "" "%~dp0index.html"
)
pause
