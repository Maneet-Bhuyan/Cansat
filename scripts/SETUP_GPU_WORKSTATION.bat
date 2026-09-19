@echo off
setlocal
title Cognitive CanSat - NVIDIA GPU Workstation Bootstrapper
color 0A
cd /d "%~dp0"

echo ===============================================================================
echo       COGNITIVE CANSAT - NVIDIA GPU WORKSTATION 1-CLICK BOOTSTRAPPER           
echo ===============================================================================
echo.
echo This script sets up a completely clean machine with:
echo   1. Python 64-bit (auto-downloads if missing)
echo   2. Local virtual environment (.venv)
echo   3. CUDA-accelerated PyTorch + TorchVision (bundles CUDA 12.1 runtime)
echo   4. Machine Learning dependencies (ONNX, scikit-learn, PyOD, FastAPI)
echo   5. EuroSAT aerial dataset verification
echo.
echo Starting setup in 3 seconds...
timeout /t 3 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_gpu_workstation.ps1"

echo.
echo Press any key to exit...
pause >nul
