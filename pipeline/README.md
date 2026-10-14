# CanSat Distributed Telemetry & Flight Data Lakehouse Pipeline

An enterprise-grade, distributed streaming and analytics pipeline designed for pico-satellite and sounding rocket avionics. Seamlessly integrates with the **Cognitive CanSat Mission Control** platform.

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Kafka / Redpanda](https://img.shields.io/badge/Broker-Redpanda%20v23.3-red?logo=apachekafka&logoColor=white)](https://redpanda.com/)
[![TimescaleDB](https://img.shields.io/badge/Hot%20Path-TimescaleDB%20PG16-fdb515?logo=postgresql&logoColor=white)](https://www.timescale.com/)
[![MinIO](https://img.shields.io/badge/Cold%20Path-MinIO%20S3%20Lake-C72C48?logo=minio&logoColor=white)](https://min.io/)
[![Grafana](https://img.shields.io/badge/Cockpit-Grafana%20Latest-F46800?logo=grafana&logoColor=white)](https://grafana.com/)
[![DuckDB](https://img.shields.io/badge/OLAP-DuckDB%20Parquet-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)

</div>

---

## 🛰️ Architecture Overview

```text
       Airborne Sensors / Real Hardware LoRa Serial (9600) / CanSat 10 Flight Scenarios
                                       │
                                       ▼
                       Cognitive CanSat Mission Control
                         (FastAPI + EKF Kinematics + ML)
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             FastAPI HUD & Three.js              PipelineBridge (async worker)
             (http://localhost:8000)                             │
                                                                 ▼
                                            Redpanda Distributed Message Broker
                                              (Kafka Protocol @ 19092 / 9092)
                                              Topic: cansat.telemetry.raw
                                                                 │
                                                                 ▼
                                                Stream Processing Engine
                                                (stream_worker.py @ ~10-100Hz)
                                                - Rolling kinematics verification
                                                - Cognitive AI anomaly trap
                                                                 │
                                       ┌─────────────────────────┴─────────────────────────┐
                                       ▼                                                   ▼
                         TimescaleDB Hot Path (5432)                             MinIO S3 Cold Lake (9000/9001)
                         - Hypertable: raw_telemetry                             - Bucket: cansat-telemetry-lake
                         - Hypertable: flight_events                             - Format: Snappy Parquet chunks
                         - Continuous Aggregate: telemetry_1s_summary            - Engine: DuckDB analytical queries
                                       │
                                       ▼
                            Grafana Operations Cockpit
                             (http://localhost:3000)
```

---

## 🚀 Quick Start

### 1. Launch Integrated Mission Control (Recommended)

Simply double-click `START_INTEGRATED_MISSION_CONTROL.bat` in either repository root:
- Checks Docker and starts containers (`redpanda`, `timescaledb`, `minio`, `grafana`).
- Launches the CanSat Mission Control FastAPI backend and 3D attitude HUD on `http://localhost:8000/`.
- Starts the Stream Processing Worker in the background.
- Connects Grafana telemetry dashboards at `http://localhost:3000/`.

### 2. Manual Startup with Docker Compose

```bash
# 1. Spin up distributed infrastructure
docker compose up -d

# 2. Start the Stream Processing Worker
python stream_processing/stream_worker.py

# 3. Start the Ingestion Daemon (choose any mode):
# Mode A: Scenario CSV Replay (from CanSat 10 flight profiles)
python ingestion/daemon.py --mode replay --scenario 01_nominal_sounding_flight --rate 10.0

# Mode B: CanSat Flight Simulator
python ingestion/daemon.py --mode sim --rate 10.0

# Mode C: Hardware Serial Bridge (LoRa COM port)
python ingestion/daemon.py --mode serial --port COM4 --baud 9600

# Mode D: Live WebSocket Bridge from CanSat FastAPI
python ingestion/daemon.py --mode bridge --ws ws://127.0.0.1:8000/ws/serial
```

---

## 📊 Services & Endpoints

| Service | Port / Protocol | URL / Connection | Description |
|---|---|---|---|
| **CanSat Mission Control** | HTTP / 8000 | `http://localhost:8000/` | Aerospace HUD, 3D attitude, live ML inference |
| **Grafana Operations HUD** | HTTP / 3000 | `http://localhost:3000/` | 7-panel avionics cockpit pre-provisioned to TimescaleDB |
| **Redpanda Broker** | Kafka / 19092, 9092 | `localhost:19092` | Distributed pub/sub topic `cansat.telemetry.raw` |
| **TimescaleDB** | PostgreSQL / 5432 | `localhost:5432/telemetry_db` | Hot-path time-series hypertables with 1s continuous aggregates |
| **MinIO Object Console** | HTTP / 9001 | `http://localhost:9001/` | Web console for Snappy Parquet cold lakehouse |
| **MinIO S3 API** | S3 / 9000 | `localhost:9000` | High-throughput object storage API |

---

## 🔍 Cold-Path DuckDB Analytics

Run ultra-fast OLAP queries over archived flight Parquet files:

```bash
# Print formatted mission report
python analytics/post_flight_analytics.py

# Filter by specific flight mission ID
python analytics/post_flight_analytics.py --mission-id MISSION_ALPHA_01

# Output raw JSON for programmatic reporting
python analytics/post_flight_analytics.py --json
```

---

## 🧪 Automated Testing

Run the full integration test suite:

```bash
pytest tests/test_integration.py -v
```
