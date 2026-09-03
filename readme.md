# Cognitive CanSat Mission Control

A full-stack aerospace telemetry and machine-learning platform for CanSat mission operations, atmospheric sounding, and flight dynamics analysis.

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![PyOD](https://img.shields.io/badge/PyOD-3.6-4B8BBE)](https://pyod.readthedocs.io/)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black?logo=three.js&logoColor=white)](https://threejs.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?logo=chart.js&logoColor=white)](https://www.chartjs.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?logo=leaflet&logoColor=white)](https://leafletjs.com/)

</div>

## Overview

This project combines a browser-based mission control dashboard with a real-time ML backend to monitor a CanSat during ascent, burst, descent, touchdown, and recovery. It includes telemetry ingestion, derived kinematic calculations, atmospheric sounding physics, phase classification, anomaly detection, and replay-based validation using mission test profiles.

## What it does

- Real-time telemetry dashboard for altitude, pressure, temperature, IMU, battery health, and GPS
- Live anomaly scoring and safety alerts for abnormal flight behavior
- Flight-phase detection across PAD_IDLE, BALLOON_ASCENT, APOGEE_BURST, PARACHUTE_DESCENT, and TOUCHDOWN_RECOVERY
- 3D CanSat attitude visualization using Three.js with complementary sensor fusion
- Synchronized multi-chart crosshair inspection projected across all 7 telemetry plots
- Post-Flight Review (PFR) report generator with automated apogee, descent compliance, and PDF export
- Tactical GIS tracking and recovery tools with Leaflet mapping and direct navigation links
- CSV replay engine and synthetic mission test profiles for 10 distinct flight regimes
- Direct hardware USB serial streaming via the native browser Web Serial API
- Python ML inference service with FastAPI and WebSocket telemetry streaming
- Smart zero-touch bootstrap launcher with zero-dependency standalone native Windows support

## Architecture

```text
CanSat / RF Receiver / USB Serial
            |
            v
Ground Station Frontend (index.html)
  - telemetry parsing and checksum validation
  - derived kinematics and atmospheric sounding
  - 3D attitude visualization (Three.js)
  - synchronized telemetry charts (Chart.js 4)
  - tactical GIS ground track (Leaflet)
  - post-flight review generator (PFR)
  - replay engine and RFC 4180 export
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
├── START_MISSION_CONTROL.bat   # Smart self-bootstrapping Windows launcher
├── launch.py                   # System launcher with port manager and browser dispatch
├── selftest.js                 # Node.js automated unit testing suite (26 assertions)
├── selftest.ps1                # PowerShell mission verification suite (17 assertions)
├── requirements.txt            # Python dependencies
├── backend/
│   ├── app.py                 # FastAPI ML inference backend
│   ├── standalone_server.ps1  # Native Windows HTTP server (.NET HttpListener)
│   ├── start_server.ps1       # Backend startup script
│   └── start_server.bat       # Windows batch launcher
├── ml/
│   ├── train_models.py        # Training pipeline
│   ├── model_metrics.json     # Model performance summary
│   └── saved_models/          # Trained artifacts
├── test_cases/                # Ten mission profile CSV datasets
├── generate_test_cases.ps1    # Synthetic scenario generator
├── project_log.txt            # Development and mission log
├── powershell_command.txt     # Setup/run command notes
├── explaination.txt           # Project architecture notes
├── readme.md                  # Project documentation
└── .gitignore
```

## Key technologies

### Frontend
- HTML, CSS, JavaScript (Obsidian space theme with high-legibility typography)
- Chart.js 4 for live telemetry plots with synchronized multi-chart crosshairs
- Leaflet for GPS tracking, flight trail overlays, and distance/bearing calculations
- Three.js for real-time 3D vehicle attitude rendering and 1-click tare
- Web Serial API for direct hardware receiver integration at 115200 baud

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

You can also double-click `START_MISSION_CONTROL.bat` from File Explorer. The launcher automatically:
1. Verifies if `.venv` exists and contains required packages.
2. If Python is installed but the virtual environment is missing, it creates `.venv` and installs dependencies automatically.
3. If Python is not installed on the system, it provides an **Instant Native Mode** using Windows' built-in `.NET HttpListener` (requiring zero third-party software).

The dashboard is available at:

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

## Atmospheric physics and kinematic formulation

The ground station performs real-time mathematical derivations on incoming telemetry packets:

### Vertical velocity
Derived using first-order backward numerical differentiation across filtered barometric altitudes:

$$v_z = \frac{h(t) - h(t - \Delta t)}{\Delta t}$$

### Vehicle attitude angles (Euler angles)
Derived from normalized 3-axis accelerometer gravity vectors with singularity protection:

$$\text{Pitch } (\theta) = \arctan2(a_y, a_z) \times \frac{180}{\pi}$$

$$\text{Roll } (\phi) = \arctan2(-a_x, \sqrt{a_y^2 + a_z^2}) \times \frac{180}{\pi}$$

### Air density
Derived using the Ideal Gas Law from barometric pressure and ambient temperature:

$$\rho = \frac{P \times 100}{R_{\text{specific}} \times (T + 273.15)} \quad \left[\frac{\text{kg}}{\text{m}^3}\right]$$

where $R_{\text{specific}} = 287.058\text{ J/(kg}\cdot\text{K)}$ for dry air.

### Dew point temperature
Calculated via the Magnus-Tetens approximation using relative humidity and temperature:

$$\alpha(T, RH) = \frac{a \cdot T}{b + T} + \ln\left(\frac{RH}{100}\right)$$

$$T_d = \frac{b \cdot \alpha(T, RH)}{a - \alpha(T, RH)} \quad [^\circ\text{C}]$$

where $a = 17.27$ and $b = 237.7^\circ\text{C}$.

### Environmental lapse rate (ELR)
Measures the vertical temperature gradient between the launch pad baseline and apogee:

$$\Gamma = -\frac{T_{\text{apogee}} - T_{\text{pad}}}{h_{\text{apogee}} - h_{\text{pad}}} \times 100 \quad \left[\frac{^\circ\text{C}}{100\text{ m}}\right]$$

### Horizontal drift and recovery bearing
Great-circle geodetic displacement and cardinal bearing from launch coordinates to touchdown:

$$\Delta y = (lat_1 - lat_0) \times 111139\text{ m}$$

$$\Delta x = (lon_1 - lon_0) \times 111139\text{ m} \times \cos\left(lat_0 \times \frac{\pi}{180}\right)$$

$$D_{\text{drift}} = \sqrt{\Delta x^2 + \Delta y^2} \quad [m]$$

$$\text{Bearing } (\beta) = \left(\arctan2(\Delta x, \Delta y) \times \frac{180}{\pi} + 360\right) \pmod{360} \quad [^\circ]$$

## API reference

The backend exposes the following endpoints:

- `GET /` — service info
- `GET /api/health` — health status
- `GET /api/models/info` — model metadata
- `POST /api/predict` — telemetry inference request
- `WS /ws/telemetry` — live telemetry stream
- `WS /ws/serial` — background serial port bridge

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

## Machine learning pipeline

The machine learning subsystem in `backend/app.py` processes telemetry vectors in real time:

| Model Architecture | Task | Input Vector | Performance Metric |
| :--- | :--- | :--- | :--- |
| Random Forest Classifier | 5-Phase Mission State Progression | 17 telemetry features | 98.4% Accuracy (Macro F1: 0.98) |
| PyOD Isolation Forest | Unsupervised Outlier and Fault Scoring | Kinematics, voltage, gyros, acceleration | Continuous Score [0.0, 1.0] |
| Gradient Boosting Regressor | Apogee Altitude Prediction | Early ascent rate, acceleration, sounding | RMSE: +/- 14.2 m |

## Mission profile coverage

The project includes ten representative telemetry profiles in `test_cases/`:

- `01_nominal_sounding_flight.csv`: Nominal sounding trajectory with 650 m apogee and compliant descent (7.2 m/s).
- `02_high_altitude_burst_1200m.csv`: Extended altitude balloon mission with low-pressure and sub-zero sounding.
- `03_severe_wind_shear_drift.csv`: High lateral crosswinds with extended drift displacement and recovery bearing analysis.
- `04_apogee_ejection_shock_tumble.csv`: Pyrotechnic deployment transient shock (> 14g) and tumbling motion.
- `05_parachute_pendulum_resonance.csv`: Dynamic pendulum oscillation under canopy (2.5 Hz angular rate swinging).
- `06_delayed_chute_deployment.csv`: Drogue failure and late main deployment with high free-fall descent speed.
- `07_thermal_inversion_sounding.csv`: Atmospheric sounding profile featuring a positive thermal inversion layer.
- `08_sensor_glitch_gps_recovery.csv`: Intermittent GNSS dropout, corrupt field recovery, and packet reconnection.
- `09_low_battery_voltage_sag.csv`: Rapid LiPo cell discharge (< 3.4V) triggering low-voltage brownout warnings.
- `10_ground_pad_static_test.csv`: Launch pad pre-flight static test for sensor zeroing, gyro drift, and RF link verification.

## Hardware telemetry protocol

The ground station parses comma-delimited ASCII strings terminated by `\r\n` or `\n` at 115200 baud:

```text
TIMESTAMP,ALTITUDE,TEMP,PRESSURE,HUMIDITY,VOLTAGE,AX,AY,AZ,GX,GY,GZ,LAT,LON
```

### Packet fields:
1. `TIMESTAMP`: Milliseconds since microcontroller boot (ms)
2. `ALTITUDE`: Barometric altitude above sea level (m)
3. `TEMP`: Ambient temperature (deg C)
4. `PRESSURE`: Atmospheric pressure (hPa)
5. `HUMIDITY`: Relative humidity (%)
6. `VOLTAGE`: LiPo battery voltage (V)
7. `AX`: Acceleration X-axis (g)
8. `AY`: Acceleration Y-axis (g)
9. `AZ`: Acceleration Z-axis (g)
10. `GX`: Angular velocity X-axis (deg/s)
11. `GY`: Angular velocity Y-axis (deg/s)
12. `GZ`: Angular velocity Z-axis (deg/s)
13. `LAT`: Latitude in decimal degrees
14. `LON`: Longitude in decimal degrees

Example packet:
```text
12400,450.2,18.4,960.5,48.2,4.05,0.08,0.12,0.98,1.2,-0.8,0.4,28.613939,77.209021
```

## Operator keyboard shortcuts

Hotkeys for rapid ground station operation (disabled during text input):

| Key | Function |
| :--- | :--- |
| Space | Toggle flight replay (Play / Pause) |
| T | Tare attitude (zero pitch and roll on launch pad) |
| P | Open Post-Flight Review (PFR) report modal |
| C | Toggle hardware connection (Web Serial UART port dialog) |
| D | Download CSV telemetry recording |
| Esc | Close active modal or exit maximized card view |

## Verification

The project includes comprehensive test suites for unit and integration testing:

### JavaScript unit test suite (26 assertions)
```bash
node selftest.js
```
Validates 13-field CSV parsing, invalid packet rejection, kinematic derivations, attitude math, battery clamping, RFC 4180 export compliance, Web Serial compatibility, and UI styling tokens.

### PowerShell mission verification suite (17 assertions)
```powershell
powershell -ExecutionPolicy Bypass -File E:\Cansat\selftest.ps1
```
Validates Mission Elapsed Time (MET) clock formatting, all 10 CSV flight profiles across the 5-phase flight sequence, and UI component integrity.

## Project status

This repository represents a complete, prototype-grade CanSat ground station and inference stack designed for research, simulation, and mission rehearsal workflows. It is suitable for local demonstration, hardware integration testing, and further engineering extension.

## License

This project is provided for educational and engineering use under the MIT License.

## Contact

For questions or collaboration, connect through the repository issues or the project maintainer profile on GitHub.
