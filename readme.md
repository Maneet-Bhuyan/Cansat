# Cognitive CanSat Mission Control

A full-stack aerospace telemetry and machine-learning platform for CanSat mission operations, atmospheric sounding, and flight dynamics analysis.

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![PyOD](https://img.shields.io/badge/PyOD-3.6-4B8BBE)](https://pyod.readthedocs.io/)

</div>

## Overview

This project combines a browser-based mission control dashboard with a real-time ML backend to monitor a CanSat during ascent, burst, descent, touchdown, and recovery. It includes telemetry ingestion, derived kinematic calculations, atmospheric sounding physics, phase classification, anomaly detection, and replay-based validation using mission test profiles.

## What it does

- Real-time telemetry dashboard for altitude, pressure, temperature, IMU, battery health, and GPS
- Live anomaly scoring and safety alerts for abnormal flight behavior
- Flight-phase detection across PAD_IDLE, BALLOON_ASCENT, APOGEE_BURST, PARACHUTE_DESCENT, and TOUCHDOWN_RECOVERY
- 3D CanSat attitude visualization using Three.js
- GIS tracking and recovery tools with Leaflet mapping
- CSV replay engine and synthetic mission test profiles
- Python ML inference service with FastAPI and WebSocket telemetry streaming

## Architecture

```text
CanSat / RF Receiver / USB Serial
            |
            v
Ground Station Frontend (index.html)
  - telemetry parsing
  - derived kinematics
  - charts + maps + 3D model
  - replay + data export
            |
            v
FastAPI backend (backend/app.py)
  - /api/predict
  - /api/health
  - /api/models/info
  - WebSocket telemetry stream
            |
            v
ML models
  - Random Forest phase classifier
  - Isolation Forest anomaly detector
  - Gradient Boosting apogee regressor
```

## Repository structure

```text
.
├── index.html                  # Mission dashboard and frontend logic
├── backend/
│   ├── app.py                 # FastAPI ML inference backend
│   ├── start_server.ps1       # Backend startup script
│   └── start_server.bat       # Windows batch launcher
├── ml/
│   ├── train_models.py        # Training pipeline
│   ├── model_metrics.json     # Model performance summary
│   └── saved_models/          # Trained artifacts
├── test_cases/                # Ten mission profile CSV datasets
├── requirements.txt           # Python dependencies
├── selftest.ps1               # Local validation script
├── generate_test_cases.ps1    # Synthetic scenario generator
├── project_log.txt            # Development and mission log
├── powershell_command.txt     # Setup/run command notes
├── explaination.txt           # Project architecture notes
├── readme.md                  # GitHub landing page
└── .gitignore
```

## Key technologies

### Frontend
- HTML, CSS, JavaScript
- Chart.js for live telemetry plots
- Leaflet for GPS tracking and map overlays
- Three.js for 3D vehicle attitude rendering
- Web Serial API for hardware receiver integration

### Backend and ML
- Python 3
- FastAPI
- Uvicorn
- scikit-learn
- PyOD
- pandas, numpy, joblib

## Getting started

### 1. Set up the environment

```powershell
cd E:\Cansat
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start the complete mission control system

The included Windows launcher starts the frontend dashboard and FastAPI backend together:

```powershell
cd E:\Cansat
START_MISSION_CONTROL.bat
```

You can also double-click `START_MISSION_CONTROL.bat` from File Explorer. The dashboard is available at:

```text
http://127.0.0.1:8000/
```

Keep the launcher window open while using the dashboard. Press `Ctrl+C` in that window to stop the backend.

### 4. Manual startup

Use the manual commands below when you need to run the backend and frontend separately.

#### Start the backend

```powershell
cd E:\Cansat
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Or use the included script:

```powershell
powershell -ExecutionPolicy Bypass -File E:\Cansat\backend\start_server.ps1
```

#### Launch the dashboard

Open the dashboard directly:

```powershell
start "E:\Cansat\index.html"
```

Or serve locally:

```powershell
cd E:\Cansat
python -m http.server 8000
```

Then browse to:

```text
http://localhost:8000/
```

## API reference

The backend exposes the following endpoints:

- `GET /` — service info
- `GET /api/health` — health status
- `GET /api/models/info` — model metadata
- `POST /api/predict` — telemetry inference request
- `WS /ws/telemetry` — live telemetry stream

Example prediction payload:

```json
{
  "temp": 18.5,
  "pressure": 1012.4,
  "altitude": 42.1,
  "gx": 1.2,
  "gy": -2.3,
  "gz": 4.1,
  "ax": 0.1,
  "ay": 0.2,
  "az": 1.0,
  "lat": 22.5727,
  "lon": 88.3655,
  "humidity": 52.0,
  "batteryVoltage": 4.1,
  "vSpd": 2.3,
  "padAlt": 0.0,
  "padTemp": 25.0,
  "padPress": 1013.25
}
```

## Mission profile coverage

The project includes ten representative telemetry profiles:

- 01_nominal_sounding_flight.csv
- 02_high_altitude_burst_1200m.csv
- 03_severe_wind_shear_drift.csv
- 04_apogee_ejection_shock_tumble.csv
- 05_parachute_pendulum_resonance.csv
- 06_delayed_chute_deployment.csv
- 07_thermal_inversion_sounding.csv
- 08_sensor_glitch_gps_recovery.csv
- 09_low_battery_voltage_sag.csv
- 10_ground_pad_static_test.csv

## Verification

```powershell
powershell -ExecutionPolicy Bypass -File E:\Cansat\selftest.ps1
```

This validates the UI, parsing logic, telemetry math, mission timing, and test-case replay behavior.

## Project status

This repository represents a complete, prototype-grade CanSat ground station and inference stack designed for research, simulation, and mission rehearsal workflows. It is suitable for local demonstration, hardware integration testing, and further engineering extension.

## License

This project is provided for educational and engineering use.

## Contact

For questions or collaboration, connect through the repository issues or the project maintainer profile on GitHub.

