# Cognitive CanSat Mission Control

## Abstract
This paper presents the Cognitive CanSat Ground Station, a comprehensive telemetry analytics and mission control architecture for sounding pico-satellites. The system integrates real-time kinematic filtering, multi-sensor ablation benchmarking, and a dual-tier machine learning pipeline spanning edge vision and ground-station analytics. A quantized depthwise separable Convolutional Neural Network (TinyLandingNet) deployed on an ESP32-CAM edge node performs autonomous Safe Landing Area Index (SLAI) evaluation on 64x64 RGB imagery within a strict 150 ms latency budget. The ground station fuses high-frequency barometric and inertial measurements using an adaptive Kalman filter, while a suite of tabular machine learning models provides flight phase classification, unsupervised anomaly detection, and sensor drift calibration. Evaluated across 10 synthesized flight profiles, the proposed architecture demonstrates high resilience to sensor failure and provides robust real-time situational awareness for CanSat missions.

## Keywords
CanSat, TinyML, Edge AI, Autonomous Descent, Hazard Avoidance, Telemetry Analytics, Sensor Fusion

## 1. Introduction
[Evidence required from experiment/data.]

## 2. Problem Statement
[Evidence required from experiment/data.]

## 3. Objectives
[Evidence required from experiment/data.]

## 4. System Architecture
The system architecture consists of an airborne ESP32/STM32 CanSat node broadcasting telemetry via RF (LoRa / 433 MHz / 868 MHz / 915 MHz) and a Ground Receiver Station connected via USB UART at 115200 baud. The browser-based Web Ground Station reads newline-delimited CSV strings via the Web Serial API to compute derived kinematics, update live charts, render 3D orientation, and export logs. (Source: `docs/project_log.txt`)

## 5. Telemetry and Data Acquisition
The telemetry packet structure supports dual-link configurations, integrating standard CanSat telemetry (pressure, temperature, IMU data) with ESP-NOW 3x3 hazard vectors derived from the edge vision system. (Source: `frontend/js/mission-slider.js`)

## 6. Signal Processing and State Estimation
The system employs an adaptive constant-velocity `AltitudeKalmanFilter` fusing barometric and IMU-derived vertical velocity. The filter adapts its covariance matrix based on the detected flight phase (ascent, freefall, descent). Post-flight kinematic reconstruction utilizes a Savitzky-Golay filter (window $N=11$, polyorder $p=2$) to extract smooth vertical velocity, peak shock acceleration, and touchdown G-forces. (Source: `backend/core/kinematics.py`, `readme.md`)

## 7. Machine Learning Architecture
The architecture is split between a Python/FastAPI ground station server and an onboard TinyML vision node.

### 7.1 Flight Phase Classification
A Random Forest Classifier monitors 17 telemetry features to identify 5 critical mission states: `PAD_IDLE`, `BALLOON_ASCENT`, `APOGEE_BURST`, `PARACHUTE_DESCENT`, and `TOUCHDOWN_RECOVERY`. The model achieves 98.56% holdout test accuracy, a weighted F1-score of 0.985, and a macro F1-score of 0.902 on a test set of 901 samples. (Source: `ml/model_metrics.json`)

### 7.2 Anomaly Detection
A PyOD Isolation Forest provides unsupervised outlier and fault scoring on kinematics, voltage, and gyroscopic data, generating a continuous anomaly score [0.0, 1.0]. (Source: `readme.md`)

### 7.3 Apogee Prediction
A Gradient Boosting Regressor predicts apogee altitude based on early ascent rate, acceleration, and atmospheric sounding data, achieving an $R^2$ of 0.9951 and an RMSE of ±24.2 m. (Source: `ml/model_metrics.json`)

### 7.4 Sensor Calibration
A Multi-Output ExtraTrees Regressor compensates for aerodynamic dynamic pressure and MEMS sensor biases using 13 telemetry features. Tested on synthetic data, it calibrates altitude to an $R^2$ of 1.0000 (RMSE: 0.804 m) and vertical velocity to an $R^2$ of 0.9516 (RMSE: 1.109 m/s). (Source: `ml/model_metrics.json`, `readme.md`)

### 7.5 TinyML / Edge Vision
TinyLandingNet, a depthwise separable CNN, evaluates autonomous Safe Landing Area Index (SLAI) scores across a 3x3 spatial hazard grid. The model expects 64x64 RGB inputs, downsampled from native QVGA (320x240) camera frames. Quantized to INT8, the model requires 7.15 KB of Flash ROM and contains 7,320 parameters, satisfying the < 25 KB requirement of the ESP32-CAM. Evaluation on a holdout test set yields an accuracy of 93.04% (best validation accuracy: 93.80%) and a macro F1-score of 93.21%. Estimated edge inference latency on the 240 MHz ESP32-CAM is ~16.3 ms. (Source: `ml/model_metrics.json`, `ml/train_tinyml_vision.py`)

## 8. Web-Based Mission Control Interface
The web interface features real-time Chart.js telemetry plots, Leaflet GPS tracking, and a Three.js real-time 3D vehicle attitude renderer. It supports direct hardware receiver integration via the Web Serial API. (Source: `readme.md`)

## 9. Experimental Methodology
Ten distinct synthetic flight scenarios were used to evaluate system performance, ranging from nominal sounding flights to extreme edge cases like severe wind shear, apogee tumbling, and parachute pendulum resonance. Sensor suite ablation benchmarking (Full, No IMU, No Env, GPS-Only) was conducted across these profiles to test system resilience. (Source: `ml/ablation_benchmarks.json`, `test_cases/`)

## 10. Results
[Evidence required from physical flight experiment data. Simulation/synthetic data confirms model theoretical performance, as outlined in Section 7.]

## 11. Discussion
[Evidence required from experiment/data.]

## 12. Limitations
The machine learning models, particularly the ExtraTrees sensor calibrator and flight phase classifier, have currently only been evaluated against synthetic/simulated telemetry profiles. Real-world generalization requires physical flight validation. The ESP32-CAM latency figure (16.3 ms) is a static estimation based on MAC counts rather than measured hardware execution time. (Source: Static Audit Analysis)

## 13. Future Work
[Evidence required from experiment/data.]

## 14. Conclusion
[Evidence required from experiment/data.]

## References
[1] Bhuyan, Maneet and Senanayak, Rishi and Shubham and Vallabh M, Ganesh. "Autonomous Landing Site Selection for Sounding Pico-Satellites Using Quantized Edge TinyML", IEEE Aerospace and Electronic Systems Magazine (Preprint), 2026. (Source: `frontend/results.html`)
