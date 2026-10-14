@echo off
setlocal enabledelayedexpansion
title Cognitive CanSat & Telemetry Pipeline - Integrated Mission Control
color 0B
cd /d "%~dp0"

echo ===============================================================================
echo       COGNITIVE CANSAT & DISTRIBUTED TELEMETRY PIPELINE INTEGRATED SYSTEM
echo ===============================================================================
echo.
echo Components:
echo   [1] CanSat Mission Control HUD & 3D Attitude  : http://localhost:8000/
echo   [2] FastAPI & Real-Time ML Inference Engine   : http://localhost:8000/api/predict
echo   [3] Distributed Message Broker (Redpanda)     : localhost:19092
echo   [4] Hot Path Time-Series Engine (TimescaleDB) : localhost:5432
echo   [5] Cold Path Parquet Data Lakehouse (MinIO)  : http://localhost:9001/
echo   [6] Mission Operations Cockpit (Grafana)      : http://localhost:3000/
echo.
echo ===============================================================================
echo.

set "PIPELINE_DIR=%~dp0pipeline"
if not exist "%PIPELINE_DIR%\docker-compose.yml" (
    set "PIPELINE_DIR=%~dp0..\cansat-telemetry-pipeline"
)

:: Step 1: Check Docker infrastructure
echo [1/3] Checking Docker Desktop & Pipeline Infrastructure...
docker ps >nul 2>&1
if !errorlevel! equ 0 (
    echo [+] Docker engine is active!
    if exist "%PIPELINE_DIR%\docker-compose.yml" (
        echo [i] Starting distributed services: Redpanda, TimescaleDB, MinIO, Grafana...
        docker compose -f "%PIPELINE_DIR%\docker-compose.yml" up -d
        echo [+] Pipeline containers verified and running!
    )
) else (
    echo [i] Docker Desktop is currently offline.
    echo     CanSat Mission Control will run with full telemetry HUD, ML inference,
    echo     and local pipeline queuing.
    echo     (To activate Grafana and TimescaleDB, start Docker Desktop and relaunch.)
)
echo.

:: Step 2: Verify Python environment
echo [2/3] Checking Python virtual environment...
set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "!PYTHON_EXE!" (
    if exist "..\Cansat\.venv\Scripts\python.exe" (
        set "PYTHON_EXE=..\Cansat\.venv\Scripts\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
)

echo [+] Using Python interpreter: !PYTHON_EXE!
echo.

:: Step 3: Launch integrated CanSat Mission Control & Pipeline
echo [3/3] Launching Integrated Mission Control System...
echo.
"!PYTHON_EXE!" launch.py

pause
