# Machine Learning & Sensor Calibration Pipelines

This directory contains the machine learning pipelines for real-time telemetry inference, sensor physics calibration, and Edge TinyML vision.

## Pipelines & Scripts

* **	rain_models.py**: Tabular flight telemetry ML training pipeline (Random Forest phase classifier, PyOD Isolation Forest anomaly detector, and Gradient Boosting apogee regressor).
* **	rain_sensor_calibration.py**: Multi-Output ExtraTrees Regressor compensating for Bernoulli aerodynamic pressure drops and MEMS sensor biases across all 10 mission profiles.
* **	rain_tinyml_vision.py**: Depthwise separable CNN (~22k params) for autonomous Safe Landing Area Index (SLAI) trained on the EuroSAT Sentinel-2 dataset.
* **export_tinyml_header.py**: INT8 post-training quantization and C++ flatbuffer byte array header exporter (irmware/esp32_cam_airborne/model_data.h).
* **download_dataset.py**: Automated EuroSAT aerial dataset downloader and integrity validator.
* **model_metrics.json**: Performance metrics, cross-validation scores, and confusion matrix summaries.
* **saved_models/**: Serialized model artifacts (.joblib, .pth, .onnx).
