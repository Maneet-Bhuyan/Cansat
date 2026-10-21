# Cognitive CanSat Documentation & Mission Journals

This directory contains the engineering manuals, research publication manuscript, technical architecture formulations, and persistent activity logs.

## Documentation Index

* **[`research_paper_draft.md`](research_paper_draft.md)**: Complete 16-section research paper manuscript (*"Cognitive CanSat: A Multi-Tiered Edge TinyML Vision, Out-of-Distribution Guard, and Physics-Informed Telemetry Fusion Architecture for Autonomous Sounding Pico-Satellites"*) containing mathematical formulations, Three-Pillar validation results, 100-flight Monte Carlo ensemble tables, 3-tier CUDA RTX 4060 vision benchmarks, and embedded 300-DPI figures.
* **[`architecture_and_ml.txt`](architecture_and_ml.txt)**: Comprehensive technical breakdown covering sensor kinematics, the full machine learning architecture (`TinyLandingNet` INT8, `MobileNetV3-Small`, `ResNet-18`, `AerialVisionGuard`, Random Forest Phase Classifier, GBDT Touchdown Prognostics, ExtraTrees Sensor Calibrator, GradientBoosting Apogee Regressor, and PyOD Isolation Forest), INT8 quantization footprints, latency benchmarks, confusion matrices, and precision/recall evaluations.
* **[`TELEMETRY_QUALITY_ANALYZER.md`](TELEMETRY_QUALITY_ANALYZER.md)**: Technical manual for the Post-Flight Telemetry Quality & Flight Reliability Analyzer (`backend/core/telemetry_analyzer.py`), documenting packet delivery ratio (PDR), dropout scoring, frozen sensor detection, and automated Post-Flight Report (PFR) grading.
* **[`project_log.txt`](project_log.txt)**: Chronological mission and development journal recording all implemented milestones, hardware bench sessions, CUDA RTX 4060 vision model training, Three-Pillar validation, UI enhancements, and verification test results.

## Repository Organization

The repository is structured into focused modular directories:

* **`frontend/`**: Complete web client suite containing all 6 presentation and mission control surfaces (`index.html`, `tinyml.html`, `dashboard.html`, `models.html`, `analysis.html`, `results.html`), stylesheets (`css/resend-theme.css`), and interactive visualization engines (`js/cansat-3d.js`, `js/mission-slider.js`, `js/results-charts.js`, `js/tinyml-demo.js`).
* **`backend/`**: FastAPI high-throughput async machine learning telemetry engine (`app.py`), standalone HTTP server (`standalone_server.ps1`), core analytical modules (`core/`), and persistent SQLite WAL flight telemetry database (`core/database.py`).
* **`ml/`**: Machine learning training pipelines (`train_tinyml_vision.py`, `train_heavy_vision.py`, `train_models.py`, `train_sensor_calibration.py`, `train_touchdown_prognostics.py`), OOD guard (`vision_guard.py`), 100-flight Monte Carlo benchmark (`generate_monte_carlo_ensemble.py`), database seeder (`seed_judge_database.py`), and serialized artifacts (`saved_models/`).
* **`firmware/`**: Dual-band airborne ESP32 telemetry transmitter (LoRa 433 MHz + 2.4 GHz ESP-NOW / Wi-Fi) and ground station receiver firmware.
* **`reports/`**: Post-flight sounding reports, including all 10 mission PDF evaluations (`reports/pdf/`), 4-panel mission figures and 300-DPI research paper figures (`reports/figures/`), and summary metrics.
* **`analysis/`**: Post-flight telemetry analysis, sensor ablation evaluation notebook, and figure assets.
* **`test_cases/`**: 10 comprehensive CSV mission flight profiles covering nominal and extreme edge-case flight dynamics.
* **`tests/`**: Automated verification and batch test suites (`selftest.js`, `selftest.ps1`, `test_backend_core.py`, `test_database.py`, `test_firmware_protocol.py`, `test_pipeline_integration.py`, `test_telemetry_analyzer.py`, `test_sm.ps1`, `batch_test_ml.py`, `batch_test_ws.py`).
* **`scripts/`**: GPU workstation automated setup and dependency installation scripts.
* **`docs/`**: Research manuscript, technical documentation, engineering manuals, and mission journals.
