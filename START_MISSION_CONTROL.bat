@echo off
title Cognitive CanSat Mission Control
color 0B
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" launch.py
) else (
    python launch.py
)

pause
