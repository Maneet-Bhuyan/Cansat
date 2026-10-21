# Machine Learning & Sensor Calibration Pipelines

This directory contains the machine learning pipelines for real-time telemetry inference, sensor physics calibration, post-flight kinematics analysis, multi-sensor ablation benchmarking, and Edge TinyML vision.

## Pipelines, Scripts & Datasets

* **`train_tinyml_vision.py`**: Depthwise separable CNN (`TinyLandingNet`, 6,996 FP32 / 7,320 INT8 parameters) for autonomous Safe Landing Area Index (SLAI) trained on 27,000 EuroSAT Sentinel-2 aerial images. Achieved **93.04% holdout test accuracy** (best validation accuracy: 93.80%) and 93.21% macro F1-score across 4 SLAI tiers (`SAFE_LZ`, `OBSTACLE_CANOPY`, `CRITICAL_HAZARD`, `WATER_HAZARD`).
* **`train_heavy_vision.py`**: CUDA GPU fine-tuning pipeline (`NVIDIA GeForce RTX 4060 Laptop GPU`, 15 epochs on 27,000 EuroSAT samples) for Tier 2 `MobileNetV3-Small` (1,521,956 parameters, **99.68% validation accuracy**, 5.81 MB FP32 / 1,486.3 KB INT8) and Tier 3 `ResNet-18` (11,178,564 parameters, **99.73% validation accuracy**, 42.64 MB FP32 / 10,916.6 KB INT8), exporting `.pth` and `.onnx` weights to `ml/saved_models/` and training histories to `ml/gpu_training_summary.json`.
* **`vision_guard.py`**: 5-stage Out-of-Distribution (`AerialVisionGuard`) non-aerial rejection filter (Exposure/Occlusion, $YC_bC_r$ Portrait Skin-Tone Ratio, Laplacian Micro-Texture Density, Helmholtz Free Energy / Shannon Entropy, and VARI Spectral Consistency) achieving **100% rejection** of close-up human faces and indoor walls before CNN evaluation.
* **`benchmark_vision_models.py`**: 3-tier computer vision benchmark comparing `TinyLandingNet`, `MobileNetV3-Small`, and `ResNet-18` across parameter count, Flash/SRAM footprint, CPU latency, OOD rejection, and real drone descent videos (`ml/vision_model_comparison.json`).
* **`export_tinyml_header.py`**: Post-training INT8 quantization and C++ flatbuffer byte array header exporter (`firmware/esp32_cam_airborne/model_data.h` and `ml/saved_models/model_data.h`). Compresses model footprint to 7.15 KB Flash ROM (< 25 KB limit).
* **`benchmark_inference.py`**: Inference latency and edge microcontroller resource benchmarking tool (Task ML-04). Measures execution times across ONNX Runtime CPU (0.055 ms), PyTorch CUDA RTX 4060 (0.614 ms), and computes the AI-Thinker ESP32-CAM budget (~16.3 ms, 783,360 MACs). Also validates 3x3 spatial hazard grid evaluation and evasion heading derivation.
* **`download_dataset.py`**: Automated EuroSAT aerial dataset loader and integrity validator (verifies 27,000 images across 10 classes and extracts from `data/EuroSAT_RGB.zip`).
* **`train_touchdown_prognostics.py`**: Gradient Boosting quantile regressor predicting Time-to-Touchdown (TTD) with 10th, 50th, and 90th percentile confidence bounds ($R^2 = 0.9963$, $\text{RMSE} = 2.33\,\text{s}$, 94.8% error reduction vs. naive baseline, 81.27% PICP) and aerodynamic descent regime classification (99.75% accuracy).
* **`train_sensor_calibration.py`**: Multi-Output ExtraTrees Regressor compensating for Bernoulli aerodynamic pressure drops and MEMS sensor biases across all 10 mission profiles (Altitude $R^2 = 1.0000$, $\text{RMSE} = 0.959\,\text{m}$).
* **`train_models.py`**: Tabular flight telemetry ML training pipeline (Random Forest phase classifier: 97.96% holdout accuracy on stochastic noisy telemetry, PyOD Isolation Forest anomaly detector: 0.8616 ROC-AUC, and Gradient Boosting apogee regressor: $R^2 = 0.9753$).
* **`generate_monte_carlo_ensemble.py`**: 100-flight randomized 6-DOF Monte Carlo statistical benchmark (`ml/monte_carlo_benchmarks.json`) proving the Hybrid Physics-Informed Kalman + ExtraTrees estimator reduces altitude RMSE by **40.4%** ($1.078 \pm 0.046\,\text{m}$ vs. $1.810 \pm 0.085\,\text{m}$ raw baro).
* **`seed_judge_database.py`**: Non-destructive SQLite WAL database seeder that preserves the 3 physical bench-top hardware missions (`MSN-20260920-192811-A2F9`, `MSN-20260920-194606-2DD8`, `MSN-20260921-092203-74EE`, $N=362$ packets) and seeds all 10 benchmark flight scenarios (`MSN-BENCH-01-NOMINAL` through `MSN-BENCH-10-STATICPAD`) with full PFR audit reports.
* **`generate_paper_figures.py`**: Generates 300-DPI publication figures (`paper_fig1_hardware_bench_characterization.png` through `paper_fig4_vision_hierarchy_and_ood_guard.png`) in `reports/figures/`.
* **`flight_analyzer.py`**: Batch kinematic reconstruction, Savitzky-Golay filtering, atmospheric lapse rate profiling, and automated publication report generator producing publication-grade vector PDFs and high-resolution PNG figures in `reports/`.
* **`ablation_benchmarks.json`**: Pre-computed multi-sensor ablation benchmark dataset systematically evaluating model performance under sensor failures across all 10 mission profiles and 4 sensor configurations:
  * **Full Sensor Suite**: Barometer + IMU (Acc/Gyro) + GNSS + Environmental sensors.
  * **No IMU**: Barometer + GNSS + Environmental sensors (Acc/Gyro disabled; evaluates aerodynamic drag estimation without direct acceleration feedback).
  * **No Environmental / Baro**: IMU + GNSS (Barometer and temperature disabled; relies on GPS altitude and kinematic integration).
  * **GPS-Only**: Standalone GPS position & velocity (degraded high-frequency dynamics; simulates total internal sensor bus failure).
  * Consumed directly by `backend/app.py` via `/api/analysis/ablation-data` and rendered interactively on `analysis.html`.
* **`model_metrics.json`**, **`vision_model_comparison.json`**, **`gpu_training_summary.json`**, **`monte_carlo_benchmarks.json`**: Master evaluation metrics, 3-tier CUDA vision benchmarks, 100-flight Monte Carlo statistics, and confusion matrices.
* **`saved_models/`**: Serialized model artifacts (`tinylandingnet_best.pth`, `tinylandingnet.onnx`, `mobilenet_v3_small_best.pth`, `mobilenet_v3_small.onnx`, `resnet18_best.pth`, `resnet18.onnx`, `model_data.h`, and tabular `.joblib` models).

## Integration with Web Analytics

The machine learning models and ablation benchmarks in this directory directly power the **Mission Control Post-Flight Analytics Suite** (`analysis.html`):
1. **Sensor Ablation Comparison**: Interactive bar charts comparing RMSE, MAE, R², and TTD error across all 4 configurations for any selected mission scenario.
2. **Live Dropout Simulator**: Interactive testing module executing dynamic sensor failure trials and comparing predicted touchdown times against ground truth flight profiles.
3. **Automated Flight Reports**: Generated by `flight_analyzer.py` and served via `/reports/pdf/` and the batch export endpoint `/api/analysis/reports-zip`.


