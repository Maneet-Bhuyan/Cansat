# Machine Learning & Sensor Calibration Pipelines

This directory contains the machine learning pipelines for real-time telemetry inference, sensor physics calibration, post-flight kinematics analysis, and Edge TinyML vision.

## Pipelines & Scripts

* **`train_tinyml_vision.py`**: Depthwise separable CNN (`TinyLandingNet`, 7,320 parameters) for autonomous Safe Landing Area Index (SLAI) trained on 27,000 EuroSAT Sentinel-2 aerial images. Achieved 93.80% validation accuracy and 93.21% macro F1-score across 4 SLAI tiers (`SAFE_LZ`, `OBSTACLE_CANOPY`, `CRITICAL_HAZARD`, `WATER_HAZARD`).
* **`export_tinyml_header.py`**: Post-training INT8 quantization and C++ flatbuffer byte array header exporter (`firmware/esp32_cam_airborne/model_data.h` and `ml/saved_models/model_data.h`). Compresses model footprint to 7.15 KB Flash ROM (< 25 KB limit).
* **`benchmark_inference.py`**: Inference latency and edge microcontroller resource benchmarking tool (Task ML-04). Measures execution times across ONNX Runtime CPU (0.055 ms), PyTorch CUDA RTX 4060 (0.614 ms), and computes the AI-Thinker ESP32-CAM budget (~16.3 ms, 783,360 MACs). Also validates 3x3 spatial hazard grid evaluation and evasion heading derivation.
* **`download_dataset.py`**: Automated EuroSAT aerial dataset loader and integrity validator (verifies 27,000 images across 10 classes and extracts from `data/EuroSAT_RGB.zip`).
* **`train_touchdown_prognostics.py`**: Gradient Boosting quantile regressor predicting Time-to-Touchdown (TTD) with 10th, 50th, and 90th percentile confidence bounds and aerodynamic descent regime classification.
* **`train_sensor_calibration.py`**: Multi-Output ExtraTrees Regressor compensating for Bernoulli aerodynamic pressure drops and MEMS sensor biases across all 10 mission profiles.
* **`train_models.py`**: Tabular flight telemetry ML training pipeline (Random Forest phase classifier: 98.56% accuracy, PyOD Isolation Forest anomaly detector, and Gradient Boosting apogee regressor: R² 0.9951).
* **`flight_analyzer.py`**: Batch kinematic reconstruction, Savitzky-Golay filtering, atmospheric lapse rate profiling, and automated publication report generator.
* **`model_metrics.json`**: Master evaluation metrics, benchmark latencies, per-tier classification reports, and confusion matrices for all models.
* **`saved_models/`**: Serialized model artifacts (`tinylandingnet_best.pth`, `tinylandingnet.onnx`, `model_data.h`, and tabular `.joblib` models).

