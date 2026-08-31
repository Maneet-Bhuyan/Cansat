@echo off
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found at %PYTHON_EXE%
    pause
    exit /b 1
)

echo ==========================================================
echo  Starting Cognitive CanSat Real-Time ML FastAPI Backend 
echo  Running on http://127.0.0.1:8000 (Docs at /docs)
echo ==========================================================

cd /d "%ROOT_DIR%"
"%PYTHON_EXE%" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
