# Cognitive CanSat Documentation & Mission Journals

This directory contains the engineering manuals, technical architecture formulations, and persistent activity logs.

## Documentation Index

* **[`architecture_and_ml.txt`](architecture_and_ml.txt)**: Comprehensive technical breakdown (written for 4th-year CSE / aerospace engineers) covering sensor kinematics, the full 6-model machine learning architecture (TinyLandingNet Edge Vision CNN, Random Forest Phase Classifier, GBDT Touchdown Prognostics, ExtraTrees Sensor Calibrator, GradientBoosting Apogee Regressor, and PyOD Isolation Forest), INT8 quantization footprints, latency benchmarks, confusion matrices, and precision/recall evaluations.
* **[`python-ml_focused.text`](python-ml_focused.text)**: The master architectural roadmap and tracking document detailing the transition to a Python-dominated backend, FastAPI routing, and TinyML edge vision pipeline.
* **[`GPU_TRAINING_INSTRUCTIONS.md`](GPU_TRAINING_INSTRUCTIONS.md)**: Standalone instructions and automated setup guide for the Antigravity agent running on the secondary NVIDIA GPU workstation.
* **[`project_log.txt`](project_log.txt)**: Chronological mission and development journal recording all implemented milestones, 3D PLA kit modeling, nadir camera orientation, side GPS bracket, blinking beacon highlight, `models.html` creation, `analysis.html` post-flight telemetry and sensor ablation suite, bugs resolved, and verification results.
* **[`whatsapp_messages.txt`](whatsapp_messages.txt)**: Formatted role-specific task briefings for team members (Maneet, Rishi, Shubham, Ganesh), including Rishi's analysis deep dive page (`analysis.html`) and Shubham's production deployment and batch testing deliverables.
* **[`tasks.txt`](../tasks.txt)**: Master task tracker with assigned deliverables, status badges, and milestone checklists (includes completed `TASK DA-06`).

## Repository Organization

The repository is structured into focused modular directories:

* **`frontend/`**: Complete web client suite containing all 6 presentation and mission control surfaces (`index.html`, `tinyml.html`, `dashboard.html`, `models.html`, `analysis.html`, `results.html`), stylesheets (`css/resend-theme.css`), and interactive visualization engines (`js/cansat-3d.js`, `js/mission-slider.js`, `js/results-charts.js`, `js/tinyml-demo.js`).
* **`backend/`**: FastAPI high-throughput async machine learning telemetry engine (`app.py`), standalone HTTP server (`standalone_server.ps1`), and core analytical modules (`core/`).
* **`ml/`**: Machine learning pipelines, INT8 quantized TinyLandingNet ONNX model, 6 scikit-learn models, flight analyzer script, and sensor ablation benchmarks.
* **`firmware/`**: Dual-band airborne ESP32 telemetry transmitter (LoRa 433 MHz + 2.4 GHz ESP-NOW / Wi-Fi) and ground station receiver firmware.
* **`reports/`**: Post-flight sounding reports, including all 10 mission PDF evaluations (`reports/pdf/`), 60+ 4-panel publication figures (`reports/figures/`), and summary metrics.
* **`analysis/`**: Post-flight telemetry analysis, sensor ablation evaluation notebook, and figure assets.
* **`test_cases/`**: 10 comprehensive CSV mission flight profiles covering nominal and extreme edge-case flight dynamics.
* **`tests/`**: Automated verification test suites (`selftest.js`, `selftest.ps1`, `test_backend_core.py`, `test_firmware_protocol.py`, `test_sm.ps1`).
* **`scripts/`**: GPU workstation automated setup and dependency installation scripts.
* **`docs/`**: Technical documentation, engineering manuals, mission journals, and team task trackers.


