# Backend Services & Telemetry Processing Engines

This directory contains the Python backend services, asynchronous hardware serial dispatchers, mathematical signal processing engines, persistent SQLite flight database, and REST/WebSocket API endpoints.

## Architecture & Components

* **`app.py`**: FastAPI application exposing REST analytics endpoints, full-duplex WebSocket telemetry streams, ML inference pipelines, static report mounts, and web page routers:
  * **Web Page Routes**:
    * `GET /` or `GET /index.html`: Mission overview, interactive 3D PLA airframe, and hardware specs.
    * `GET /dashboard.html`: Real-time aerospace telemetry HUD, 3D attitude, and Web Serial bridge.
    * `GET /tinyml.html`: TinyML edge vision deep dive, INT8 quantization benchmarks, and inference simulator.
    * `GET /models.html`: 6-model machine learning architecture and comparative benchmark analysis.
    * `GET /analysis.html`: Post-flight mission analytics, interactive telemetry charts, sensor ablation suite, and dropout simulator.
    * `GET /results.html`: Flight testing research viewer and scenario comparison charts.
  * **REST Analytics & Telemetry Endpoints**:
    * `POST /analytics/kinematics`: 1D Kalman filter state estimation ($z, v_z$) and 6-DOF attitude calculation.
    * `POST /analytics/sounding`: Hypsometric altimetry, Magnus-Tetens dew point, air density, and environmental lapse rate.
    * `GET /hardware/ports`: Active USB serial COM port auto-detection.
    * `POST /hardware/tare`: 1-click sensor calibration and static gyro drift nulling.
    * `POST /api/predict`: Tabular ML inference (Random Forest phase classifier & Isolation Forest anomaly detector).
  * **Post-Flight Analysis & Ablation Endpoints**:
    * `GET /api/analysis/scenarios`: Enumeration of all 10 flight mission profiles with flight metadata.
    * `GET /api/analysis/scenario/{scenario_name}`: Full RFC 4180 telemetry CSV dataset for the requested scenario.
    * `GET /api/analysis/ablation-data`: Pre-computed multi-sensor ablation benchmarks across all 10 profiles and 4 sensor configurations (`ml/ablation_benchmarks.json`).
    * `POST /api/analysis/run-ablation`: Live sensor ablation trial execution evaluating custom dropped sensor subsets on flight datasets.
    * `GET /api/analysis/reports-zip`: In-memory ZIP archive packaging all 10 mission flight PDF reports and `reports/all_missions_summary.csv`.
  * **Flight Database (SQLite WAL) & Post-Flight Review (PFR) Persistence Endpoints**:
    * `POST /api/db/missions/start`: Arm and initialize a new flight mission session in SQLite (`data/cansat_missions.db`).
    * `POST /api/db/missions/telemetry`: High-frequency batch packet streaming (up to 500 pkts/batch).
    * `POST /api/db/missions/{mission_id}/events`: Record discrete flight events (stage separation, parachute deployment, alarms).
    * `POST /api/db/missions/{mission_id}/finish`: Seal flight, compute kinematic KPIs, and generate automated PFR audit report.
    * `GET /api/db/missions`: List all archived missions with status, duration, apogee, and packet count.
    * `GET /api/db/missions/{mission_id}`: Retrieve detailed mission metadata.
    * `GET /api/db/missions/{mission_id}/report`: Retrieve the stored Post-Flight Review audit report.
    * `GET /api/db/missions/{mission_id}/telemetry`: Fetch full historical telemetry records for replay and analysis.
    * `GET /api/db/stats`: Storage diagnostics returning database file size, WAL size, total missions, total packets, events, reports, and journal mode.
    * `GET /api/db/download`: Direct binary stream download of `data/cansat_missions.db` with prior WAL checkpointing for external inspection.
    * `GET /api/db/missions/{mission_id}/export/csv`: Export full 25-column mission flight telemetry in standard CanSat CSV format.
    * `DELETE /api/db/missions`: Complete cascaded wipe and purge of all stored flight sessions and sequence tables.
    * `DELETE /api/db/missions/{mission_id}`: Cascade deletion of a specific mission and all its telemetry, events, and reports.
  * **WebSocket Telemetry Streams**:
    * `/ws/serial`: Real-time dual-port serial bridge dispatcher (LoRa telemetry & video frame chunks).
    * `/ws/telemetry`: Simulated telemetry broadcast stream for replay and headless testing.
  * **Static File Mounts**:
    * `/reports`: Serves generated flight report PDFs (`reports/pdf/`) and high-resolution figures (`reports/figures/`).
* **`core/`**: Core mathematical, database, and serial abstraction engines:
  * **`database.py`**: SQLite persistent database engine operating in Write-Ahead Logging (WAL) mode with foreign keys. Manages 4 relational tables (`missions`, `telemetry_records`, `mission_reports`, `mission_events`), batch ingestion, PFR audit metrics computation, storage statistics diagnostics, full database purge, and 25-column CSV telemetry export.
  * **`serial_manager.py`**: `DualSerialManager` handling multi-port asynchronous hardware polling (COM4/COM3 LoRa @ 9600 baud and COM5 Video @ 460800 baud).
  * **`kinematics.py`**: `KinematicsEngine` providing 1D Kalman Filter state estimation ($z, v_z$), 6-DOF complementary attitude fusion, and high-G / tumble alarm triggers.
  * **`atmospheric.py`**: `AtmosphericEngine` providing hypsometric altimetry, Magnus-Tetens dew point, dry/moist air density, and Environmental Lapse Rate (ELR).
* **`standalone_server.ps1`**: Zero-dependency native Windows HTTP server utilizing .NET `HttpListener` for running the ground station on systems without Python.

## Running the Backend

From the repository root with the active virtual environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```
