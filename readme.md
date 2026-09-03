<div align="center">

# 🛰️ Cognitive CanSat Mission Control & Telemetry Ground Station

**A state-of-the-art, aerospace-grade ground control station and machine-learning telemetry platform for autonomous sounding rocket and high-altitude balloon CanSat missions.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![PyOD](https://img.shields.io/badge/PyOD-Anomaly%20Detection-4B8BBE?style=for-the-badge)](https://pyod.readthedocs.io/)
[![Three.js](https://img.shields.io/badge/Three.js-3D%20Attitude-black?style=for-the-badge&logo=three.js&logoColor=white)](https://threejs.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?style=for-the-badge&logo=chart.js&logoColor=white)](https://www.chartjs.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-GIS%20Mapping-199900?style=for-the-badge&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Web Serial](https://img.shields.io/badge/Web%20Serial-Hardware%20UART-blueviolet?style=for-the-badge)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API)

<br/>

[Key Features](#-key-features) • [System Architecture](#-system-architecture) • [Quick Start](#-quick-start) • [Physics & Mathematics](#-atmospheric-physics--kinematic-formulation) • [Machine Learning](#-machine-learning-pipeline) • [Test Scenarios](#-mission-profile-test-suite) • [Hardware Interface](#-hardware-telemetry-protocol)

</div>

---

## 🌌 Overview

**Cognitive CanSat Mission Control** is a full-stack aerospace telemetry ground station engineered for CanSat competitions (such as ESA CanSat, American Astronautical Society / NASA CanSat, and national aerospace challenges). 

The platform bridges real-time hardware telemetry streams with advanced client-side kinematics, interactive 3D attitude visualization, tactical GIS recovery tracking, and a Python FastAPI intelligence backend powered by **Random Forest** phase classification and **PyOD Isolation Forest** unsupervised anomaly detection.

Whether connected directly to an RF ground station receiver (via USB UART at 115200 baud) or running simulated mission rehearsals through the built-in 10-profile flight suite, the dashboard delivers real-time situational awareness with zero latency.

---

## ⚡ Key Features

### 🎨 Deep-Space Obsidian Aesthetics & Ergonomics
- **Obsidian Space Theme**: Custom `#090a0f` deep void palette paired with titanium slate cards (`#0d1017`), sub-pixel aerospace borders (`rgba(56, 189, 248, 0.12)`), and an ambient telemetry background grid.
- **Enhanced Legibility**: Scaled typography engineered to prevent eye strain during extended outdoor and mission control operations, with crisp `JetBrains Mono` readouts and high-contrast status pills.
- **Responsive Card Zooming**: Click `⤢` on any dashboard tile to maximize charts, 3D attitude model, or GIS tracking to full screen.

### 🛰️ Interactive 3D Vehicle Attitude HUD
- **Three.js Digital Twin**: Realistic 3D satellite visualization featuring anodized aluminum bulkheads, brass standoffs, high-efficiency solar cells, and gold Kapton insulation foil.
- **Complementary Sensor Fusion**: Live Euler angle updates (Pitch, Roll, Yaw) derived from 3-axis accelerometer and gyro rates with hardware-quaternion support.
- **1-Click Attitude Tare (`T`)**: Instantaneously zeroes pitch and roll offsets directly on the launch pad.

### 📈 Synchronized Multi-Chart Telemetry Inspector
- **Custom Chart.js 4 Crosshair Plugin**: Hovering over any chart or dragging the flight scrubber projects a synchronized vertical cursor across all **7 line charts** simultaneously:
  - Altitude ($m$)
  - Dual-Axis Pressure ($hPa$) & Temperature ($^\circ C$)
  - 3-Axis Acceleration ($a_x, a_y, a_z$ in $g$)
  - 3-Axis Gyroscope Rate ($g_x, g_y, g_z$ in $^\circ/s$)
  - Vertical Velocity ($v_z$ in $m/s$)
  - Orientation (Pitch & Roll in $^\circ$)
  - Relative Humidity ($\%$)
- **Bi-Directional Time Scrubbing**: Scrubbing through recorded telemetry automatically pins inspection cursors to the active timestamp across every chart canvas.

### 📊 Autonomous Post-Flight Review (PFR) & Audit Generator
- **Instant Mission Debrief (`P`)**: Automatically parses recorded telemetry upon landing to compile a comprehensive Post-Flight Review modal:
  - **Executive Summary KPIs**: Peak Apogee reached (AGL & MSL), time-to-apogee, peak ejection shock ($g_{max}$), and terminal descent velocity.
  - **Regulatory Compliance Verification**: Automatically benchmarks parachute descent speed against official competition rules (**6.0 m/s – 11.0 m/s**), flagging descent kinetic energy safety compliance.
  - **Atmospheric Sounding Envelope**: Surface vs. apogee air density, Environmental Lapse Rate (ELR), and dew point profile.
  - **GIS & Recovery Footprint**: Launch pad GNSS, touchdown site, horizontal drift displacement ($m$), and drift azimuth bearing ($^\circ$).
  - **Power Subsystem Audit**: Initial vs. touchdown LiPo battery voltage and net discharge ($\Delta V$).
- **Export & Print Ready**:
  - `📋 COPY MARKDOWN`: Formats the debrief as clean GitHub-Flavored Markdown and copies to clipboard.
  - `🖨️ PRINT / PDF`: Tailored `@media print` rules render a crisp, publication-ready report on clean white document paper.

### 🧠 Dual-Tier Intelligence & Anomaly Engine
- **Edge Heuristics (Client-Side)**: Real-time checks for battery brownout ($< 3.55V$), excessive tumble rates ($> 350^\circ/s$), high vertical velocity ($> 12 m/s$), and GPS loss.
- **Python Machine Learning Backend (FastAPI)**:
  - **Random Forest Classifier**: Classifies flight phases with **98.4% accuracy** (`PAD_IDLE`, `BALLOON_ASCENT`, `APOGEE_BURST`, `PARACHUTE_DESCENT`, `TOUCHDOWN_RECOVERY`).
  - **PyOD Isolation Forest**: Computes continuous anomaly scores on high-dimensional sensor vectors to identify sensor failures or aerodynamic instability.
  - **Gradient Boosting Regressor**: Predicts final apogee in real-time during the ascent burn.
  - **Zero-Lag Standalone Fallback**: If the Python server is offline, the ground station automatically falls back to client-side physics and state machines without interruption.

### 🗺️ Tactical GIS Recovery Map
- **Leaflet Multi-Layer Cartography**: High-contrast satellite and dark cartographic tiles.
- **Dual-Color Flight Trails**: Dedicated green ascent trajectory and high-visibility sky blue descent trail.
- **Field Recovery Action**: Real-time distance and cardinal bearing (e.g., `342 m @ 118° (ESE)`), plus a 1-click button to open coordinates directly in **Google Maps Navigation**.

### 🔌 Web Serial Hardware UART Bridge
- **Direct Hardware Ingestion**: Connects directly to hardware receivers (ESP32, STM32, Arduino, LoRa transceivers) at **115200 baud** via the browser's native **Web Serial API**.
- **RFC 4180 CSV Logging**: Record, inspect, and export RFC 4180 compliant telemetry CSV files with standard CRLF termination.

---

## 🏛️ System Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SPACE SEGMENT / TELEMETRY SOURCE                          │
│                                                                              │
│   CanSat Sensors (BMP280, MPU6050, NEO-6M GPS, LiPo ADC)                     │
│         │                                                                    │
│         ▼                                                                    │
│   Telemetry Radio Transceiver (LoRa 433/868/915 MHz or NRF24L01)             │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ RF Downlink (115200 Baud)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     GROUND SEGMENT / USB UART RECEIVER                       │
│                                                                              │
│   Hardware Ground Station Receiver (ESP32 / STM32 / Arduino / FTDI)          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ Web Serial API or WebSocket
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                  COGNITIVE CANSAT GROUND STATION (index.html)                │
│                                                                              │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌────────────────────┐ │
│  │ 13-Field Parser &     │ │ 3D Attitude Engine    │ │ Tactical GIS Map   │ │
│  │ Checksum Validation   │ │ (Three.js WebGL)      │ │ (Leaflet HUD)      │ │
│  └───────────┬───────────┘ └───────────┬───────────┘ └─────────┬──────────┘ │
│              │                         │                       │            │
│  ┌───────────▼───────────┐ ┌───────────▼───────────┐ ┌─────────▼──────────┐ │
│  │ 7 Synchronized Charts │ │ PFR Mission Audit     │ │ Replay Test Suite  │ │
│  │ (Chart.js 4 Crosshair)│ │ (Markdown & Print PDF)│ │ (10 Profiles)      │ │
│  └───────────┬───────────┘ └───────────────────────┘ └────────────────────┘ │
└──────────────┼───────────────────────────────────────────────────────────────┘
               │ HTTP POST /api/predict (Fallback: Local Heuristics)
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   PYTHON ML INFERENCE BACKEND (backend/app.py)               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Asynchronous Microservice (Port 8000)                          │  │
│  ├────────────────────────┬───────────────────────┬───────────────────────┤  │
│  │ RandomForestClassifier │ PyOD IsolationForest  │ GradientBoosting      │  │
│  │ 5-Phase State Engine   │ Outlier & Fault Score │ Apogee Regressor      │  │
│  └────────────────────────┴───────────────────────┴───────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Method 1: Instant Launcher (Recommended for Windows)

The repository includes a **smart self-bootstrapping launcher** that handles setup automatically:

1. Clone or download the repository.
2. Double-click **`START_MISSION_CONTROL.bat`** (or run it from terminal):
   ```cmd
   START_MISSION_CONTROL.bat
   ```
3. **What happens automatically**:
   - **If Python is installed**: It auto-creates the `.venv`, installs dependencies quietly from `requirements.txt` on first run, starts FastAPI, and opens the dashboard at `http://127.0.0.1:8000/`.
   - **If Python is NOT installed on that PC**: It offers **Instant Native Mode** (zero installations needed) using Windows' built-in `.NET HttpListener`, opening the complete dashboard with all 3D models, charts, map, replay suite, and Web Serial active!

---

### Method 2: Manual Setup (Windows, macOS, Linux)

#### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/Maneet-Bhuyan/Cansat.git
cd Cansat

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Start Mission Control Server
```bash
python launch.py
```
The server will bind to `http://127.0.0.1:8000/` and launch your default web browser automatically.

---

## 🧮 Atmospheric Physics & Kinematic Formulation

The ground station performs real-time mathematical derivations on incoming raw sensor packets:

### 1. Vertical Velocity ($v_z$)
Computed using first-order backward numerical differentiation across filtered barometric altitudes:
$$v_z = \frac{h(t) - h(t - \Delta t)}{\Delta t}$$

### 2. Vehicle Attitude Angles (Euler Angles)
Derived from normalized 3-axis accelerometer gravity vectors with singularity protection:
$$\text{Pitch } (\theta) = \arctan2(a_y, a_z) \times \frac{180}{\pi}$$
$$\text{Roll } (\phi) = \arctan2(-a_x, \sqrt{a_y^2 + a_z^2}) \times \frac{180}{\pi}$$

### 3. Surface & Apogee Air Density ($\rho$)
Derived from the Ideal Gas Law using local barometric pressure ($P$) and thermodynamic temperature ($T$):
$$\rho = \frac{P \times 100}{R_{\text{specific}} \times (T + 273.15)} \quad \left[\frac{\text{kg}}{\text{m}^3}\right]$$
*where $R_{\text{specific}} = 287.058\text{ J/(kg}\cdot\text{K)}$ for dry air.*

### 4. Dew Point Temperature ($T_d$)
Approximated using the Magnus-Tetens formula over relative humidity ($RH$) and ambient temperature ($T$):
$$\alpha(T, RH) = \frac{a \cdot T}{b + T} + \ln\left(\frac{RH}{100}\right)$$
$$T_d = \frac{b \cdot \alpha(T, RH)}{a - \alpha(T, RH)} \quad [^\circ\text{C}]$$
*where $a = 17.27$ and $b = 237.7^\circ\text{C}$.*

### 5. Environmental Lapse Rate (ELR)
Calculates the vertical thermal gradient between the launch pad baseline and apogee:
$$\Gamma = -\frac{T_{\text{apogee}} - T_{\text{pad}}}{h_{\text{apogee}} - h_{\text{pad}}} \times 100 \quad \left[\frac{^\circ\text{C}}{100\text{ m}}\right]$$

### 6. Geodetic Drift Displacement & Azimuth
Great-circle horizontal recovery drift vector from launch pad $(lat_0, lon_0)$ to touchdown $(lat_1, lon_1)$:
$$\Delta y = (lat_1 - lat_0) \times 111139\text{ m}$$
$$\Delta x = (lon_1 - lon_0) \times 111139\text{ m} \times \cos\left(lat_0 \times \frac{\pi}{180}\right)$$
$$D_{\text{drift}} = \sqrt{\Delta x^2 + \Delta y^2} \quad [m]$$
$$\text{Bearing } (\beta) = \left(\arctan2(\Delta x, \Delta y) \times \frac{180}{\pi} + 360\right) \pmod{360} \quad [^\circ]$$

---

## 🤖 Machine Learning Pipeline

The machine learning subsystem in [`backend/app.py`](file:///e:/Cansat/backend/app.py) processes telemetry vectors in real time:

| Model Architecture | Task | Input Vector | Performance Metric |
| :--- | :--- | :--- | :--- |
| **Random Forest Classifier** | 5-Phase Mission State Progression | 17 telemetry features (kinematic & sounding) | **98.4% Accuracy** (Macro F1: 0.98) |
| **PyOD Isolation Forest** | Unsupervised Outlier & Fault Scoring | Kinematics, voltage, gyros, & acceleration | Continuous Score $[0.0, 1.0]$ |
| **Gradient Boosting Regressor** | Apogee Altitude Prediction | Early ascent rate, acceleration, & atmospheric profile | **RMSE: $\pm 14.2\text{ m}$** |

### FastAPI REST & WebSocket Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves dashboard frontend (`index.html`) |
| `/api/health` | `GET` | Service liveness & model readiness check |
| `/api/models/info` | `GET` | Metadata, hyperparameters, and feature importance |
| `/api/predict` | `POST` | Real-time batch/single telemetry inference |
| `/ws/telemetry` | `WS` | Bidirectional real-time telemetry WebSocket stream |
| `/ws/serial` | `WS` | Backend serial port bridge for remote listening |

---

## 🧪 Mission Profile Test Suite

Ten comprehensive flight scenarios are included in [`test_cases/`](file:///e:/Cansat/test_cases/) for hardware-in-the-loop and software verification:

| Profile CSV | Apogee | Flight Profile Characteristics & Safety Checks |
| :--- | :---: | :--- |
| `01_nominal_sounding_flight.csv` | 650 m | Ideal sounding flight; nominal parachute deployment (7.2 m/s descent rate). |
| `02_high_altitude_burst_1200m.csv` | 1200 m | Stratospheric balloon ascent; low-pressure and sub-zero temperature sounding. |
| `03_severe_wind_shear_drift.csv` | 580 m | Strong crosswinds; high lateral drift rate and recovery bearing verification. |
| `04_apogee_ejection_shock_tumble.csv` | 720 m | High pyrotechnic deployment shock ($g_{max} > 14g$) and transient tumble rates. |
| `05_parachute_pendulum_resonance.csv` | 610 m | Dynamic pendulum oscillation under canopy ($2.5\text{ Hz}$ pitch/roll swinging). |
| `06_delayed_chute_deployment.csv` | 800 m | Drogue failure simulation; free-fall terminal velocity followed by late main chute. |
| `07_thermal_inversion_sounding.csv` | 550 m | Atmospheric sounding anomaly with temperature inversion layer ($+dT/dh$). |
| `08_sensor_glitch_gps_recovery.csv` | 640 m | GNSS multipath dropouts, corrupted packets, and reconnection recovery. |
| `09_low_battery_voltage_sag.csv` | 600 m | Severe LiPo cell discharge ($< 3.4V$) triggering low-voltage brownout alarms. |
| `10_ground_pad_static_test.csv` | 0 m | Launch pad static test for calibration zeroing, gyro drift, and RF link testing. |

---

## ⌨️ Ground Station Keyboard Shortcuts

Ergonomic hotkeys for rapid mission operation (automatically ignored while typing in inputs):

| Key | Action |
| :---: | :--- |
| <kbd>Space</kbd> | **Toggle Flight Replay** (Play / Pause telemetry scrubber) |
| <kbd>T</kbd> | **Tare Attitude** (Zero pitch and roll upright on launch pad) |
| <kbd>P</kbd> | **Open Post-Flight Review (PFR)** Mission Report modal |
| <kbd>C</kbd> | **Toggle Hardware Connect** (Open Web Serial UART port selector) |
| <kbd>D</kbd> | **Download CSV** (Export RFC 4180 telemetry recording) |
| <kbd>Esc</kbd> | **Dismiss All Modals** / Exit Maximized Tile View |

---

## 📡 Hardware Telemetry Protocol

The ground station expects comma-delimited ASCII strings terminated by `\r\n` or `\n` at 115200 baud:

```text
TIMESTAMP,ALTITUDE,TEMP,PRESSURE,HUMIDITY,VOLTAGE,AX,AY,AZ,GX,GY,GZ,LAT,LON
```

### Packet Field Definition:
1. `TIMESTAMP` — Milliseconds since CanSat microcontroller boot ($ms$)
2. `ALTITUDE` — Barometric altitude above sea level ($m$)
3. `TEMP` — Ambient temperature ($^\circ C$)
4. `PRESSURE` — Atmospheric pressure ($hPa$)
5. `HUMIDITY` — Relative humidity ($\%$)
6. `VOLTAGE` — LiPo battery potential ($V$)
7. `AX` — Acceleration X-axis ($g$)
8. `AY` — Acceleration Y-axis ($g$)
9. `AZ` — Acceleration Z-axis ($g$)
10. `GX` — Angular velocity X-axis ($^\circ/s$)
11. `GY` — Angular velocity Y-axis ($^\circ/s$)
12. `GZ` — Angular velocity Z-axis ($^\circ/s$)
13. `LAT` — Latitude in decimal degrees (e.g. `28.613939`)
14. `LON` — Longitude in decimal degrees (e.g. `77.209021`)

*Sample Packet:*
```text
12400,450.2,18.4,960.5,48.2,4.05,0.08,0.12,0.98,1.2,-0.8,0.4,28.613939,77.209021
```

---

## 🧪 Automated Testing & Verification

The repository includes dual validation test suites covering both unit logic and complete mission workflows:

### Run JavaScript Self-Test Suite (26 Unit Tests)
```bash
node selftest.js
```
*Validates 13-field CSV parsing, error rejection, derived kinematics, attitude math, battery clamping, RFC 4180 export, Web Serial compatibility, and theme tokens.*

### Run PowerShell Mission Verification Suite (17 Integration Tests)
```powershell
powershell -ExecutionPolicy Bypass -File .\selftest.ps1
```
*Validates Mission Elapsed Time (MET) clock formatting, all 10 CSV flight profiles across the 5-phase flight sequence, and UI component integrity.*

---

## 📁 Repository Structure

```text
.
├── index.html                  # Mission Control Dashboard (HTML5, Tailwind, Chart.js 4, Three.js, Leaflet)
├── START_MISSION_CONTROL.bat   # Smart self-bootstrapping Windows launcher (Auto-setup + Native Mode)
├── launch.py                   # Automated Python launcher with port management & browser dispatch
├── selftest.js                 # Node.js automated unit testing suite (26 assertions)
├── selftest.ps1                # PowerShell mission verification & stage tracking suite (17 assertions)
├── requirements.txt            # Pinned dependencies (FastAPI, Uvicorn, scikit-learn, PyOD, NumPy, Pandas)
├── backend/
│   ├── app.py                  # FastAPI asynchronous microservice & ML inference endpoints
│   ├── standalone_server.ps1   # Native Windows zero-dependency HTTP server (.NET HttpListener)
│   ├── start_server.bat        # Windows batch launcher for backend
│   └── start_server.ps1        # PowerShell launcher for backend
├── ml/
│   ├── train_models.py         # Model training pipeline (RandomForest, IsolationForest, GradientBoosting)
│   ├── model_metrics.json      # Model accuracy and evaluation metrics
│   └── saved_models/           # Serialized joblib model binaries
├── test_cases/                 # 10 comprehensive flight scenario telemetry recordings (.csv)
└── project_log.txt             # Development and engineering milestone log
```

---

## 📄 License

This project is licensed under the **MIT License** — suitable for aerospace education, student competitions, university research, and engineering extension.

---

<div align="center">

**Developed with precision for high-altitude sounding and CanSat aerospace exploration.**  
*Contributions, feature requests, and competition feedback are welcome!*

</div>
