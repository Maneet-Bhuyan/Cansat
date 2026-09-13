# Backend Services & Telemetry Processing Engines

This directory contains the Python backend services, asynchronous hardware serial dispatchers, and mathematical signal processing engines.

## Architecture & Components

* **pp.py**: FastAPI server exposing REST analytics endpoints (/analytics/kinematics, /analytics/sounding, /hardware/tare, /hardware/ports), full-duplex WebSocket streams (/ws/serial, /ws/telemetry), and ML inference pipelines.
* **core/**: Core mathematical and serial abstraction engines:
  * **serial_manager.py**: DualSerialManager handling multi-port asynchronous hardware polling (COM4/COM3 LoRa @ 9600 baud and COM5 Video @ 460800 baud).
  * **kinematics.py**: KinematicsEngine providing 1D Kalman Filter state estimation (, v_z$), 6-DOF complementary attitude fusion, and high-G / tumble alarm triggers.
  * **tmospheric.py**: AtmosphericEngine providing hypsometric altimetry, Magnus-Tetens dew point, dry/moist air density, and Environmental Lapse Rate (ELR).
* **standalone_server.ps1**: Zero-dependency native Windows HTTP server utilizing .NET HttpListener for running the ground station on systems without Python.
