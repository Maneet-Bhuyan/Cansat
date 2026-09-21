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

## 13. Telemetry Data Quality and Reliability Assessment

### 13.1 Motivation and Scope

Reliable post-flight analysis and real-time machine learning inference are contingent on the integrity of the underlying telemetry dataset. Corrupted packets, timestamp discontinuities, GNSS lock losses, and sensor dropouts introduce systematic bias into downstream models. For instance, the Random Forest flight phase classifier (Section 7.1) uses altitude, acceleration magnitude, and vertical velocity derived directly from raw telemetry fields; missing or erroneous samples propagate errors through kinematic integration steps. Similarly, the Savitzky-Golay filter used in post-flight reconstruction requires temporally uniform samples to preserve the spectral properties of the velocity signal.

This section describes an objective, deterministic data quality assessment pipeline implemented in `backend/core/telemetry_analyzer.py` and exposed via REST endpoints `/api/analysis/quality/{scenario_name}` and `/api/analysis/quality/analyze-csv`. The analyzer reports only measurable facts and does not assign subjective quality scores.

### 13.2 Packet Integrity

Each row in the telemetry CSV constitutes one packet. The analyzer reports:

- **Total rows** $N$: the count of lines excluding the RFC 4180 header.
- **Valid packets** $N_v$: rows in which all 13 primary telemetry channels are numeric, finite, and parsable.
- **Corrupted rows** $N_c$: rows with non-numeric tokens (e.g., `"CORRUPT"`, `"ERR"`), floating-point infinities, or pandas parse failures.
- **Duplicate packets** $N_d$: exact row duplicates or repeated ISO 8601 timestamps detected via pandas `.duplicated()`.
- **Missing packets estimate** $\hat{N}_m$: estimated sequence losses derived from temporal gap analysis (see Section 13.3).

Packet completeness is defined as:

$$C = \frac{N_v}{N_v + N_c + \hat{N}_m} \times 100\%$$

This metric quantifies the fraction of expected packets that were successfully received and decoded, accounting for both data corruption and communication dropouts.

### 13.3 Temporal Integrity

The CanSat telemetry system operates at a fixed nominal sampling interval of $\Delta t_0 = 0.8\,\text{s}$ (1.25 Hz). Temporal integrity is evaluated by computing pairwise successive timestamp differences:

$$\Delta t_i = t_{i+1} - t_i, \quad i = 1, \ldots, N-1$$

The following statistics are reported without thresholding:

- Mean interval: $\overline{\Delta t} = \frac{1}{N-1}\sum_{i=1}^{N-1} \Delta t_i$
- Median interval: $\text{median}(\Delta t)$
- Minimum and maximum: $\min(\Delta t)$, $\max(\Delta t)$
- Jitter (standard deviation): $\sigma_{\Delta t} = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N-1}(\Delta t_i - \overline{\Delta t})^2}$

A **timestamp gap** is defined as any interval satisfying $\Delta t_i \geq \tau_\text{gap}$, where $\tau_\text{gap} = 2.0\,\text{s}$ is a configurable threshold (default: $2.5 \times \Delta t_0$). The number of missing packets per gap is estimated as:

$$\hat{N}_{m,i} = \max\!\left(1,\; \left\lfloor \frac{\Delta t_i}{\Delta t_0} \right\rceil - 1\right)$$

**Irregular intervals** are defined as samples deviating more than $\pm 20\%$ from the observed median interval, flagging oscillator instability or packet-level retransmission artifacts.

### 13.4 Sensor Completeness

For each of the 13 primary telemetry fields (`temp`, `pressure`, `altitude`, `gx`, `gy`, `gz`, `ax`, `ay`, `az`, `lat`, `lon`, `humidity`, `batteryVoltage`) and 3 derived fields (`pitch`, `roll`, `accelMag`), the following are computed:

- **Non-null count** $n_k$: rows for which field $k$ is numeric and finite.
- **Missing count** $m_k = N - n_k$.
- **Availability percentage**: $A_k = (n_k / N) \times 100\%$.
- **Observed range**: $[\min(k), \max(k)]$ over valid samples.
- **Out-of-range count**: samples outside the hardware operational envelope defined by sensor datasheets (Table 1).

**Table 1: Physical Sensor Operating Envelopes**

| Field | Sensor | Range |
|---|---|---|
| `temp` | BMP180/DHT11 | −50 to +85 °C |
| `pressure` | BMP180/BMP280 | 10 to 1150 hPa |
| `ax`, `ay`, `az` | MPU6050 | ±16.0 G |
| `gx`, `gy`, `gz` | MPU6050 | ±2000 °/s |
| `humidity` | DHT11/SHT31 | 0 to 100% |
| `batteryVoltage` | 1S LiPo | 3.00 to 4.35 V |
| `lat` | u-blox NEO-6M | −90° to +90° |
| `lon` | u-blox NEO-6M | −180° to +180° |

### 13.5 GNSS Fix Loss Detection

A GNSS fix loss event is detected when consecutive packets report coordinates `(lat, lon) = (0.0, 0.0)` within a tolerance of $10^{-5}$ degrees. The u-blox NEO-6M GPS module outputs `(0.0, 0.0)` when satellite lock has not been acquired or has been lost. Each contiguous run of $\geq 2$ such packets is reported as a dropout event with its start index, end index, duration, and packet count.

### 13.6 LiPo Voltage Sag Detection

A battery voltage sag event is defined as a contiguous run of $\geq 2$ consecutive packets with `batteryVoltage < 3.40 V`. This threshold corresponds to the low-voltage cutoff commonly associated with 1S LiPo cells under load, below which brownout-induced sensor instability and RF transmission degradation may occur. The minimum observed voltage within each sag window is reported.

### 13.7 Implications for Downstream ML and Post-Flight Analysis

Missing telemetry samples reduce effective training set size and introduce temporal irregularity into feature sequences used by the Random Forest flight phase classifier and Gradient Boosting apogee regressor. Timestamp gaps exceeding $2\Delta t_0$ disrupt the Savitzky-Golay velocity derivative, producing artifacts in the reconstructed velocity profile. GNSS fix loss periods prevent computation of lateral drift metrics used in touchdown coordinate regression. Battery sag events correlate with RF transmission instability, potentially causing additional missing packets not captured by the timestamp gap detector. Pre-flight data quality assessment flags these conditions before inference is invoked.

### 13.8 Limitations

The implemented checks are designed for the specific CanSat telemetry format (RFC 4180 CSV, 17 columns, ISO 8601 timestamps). The GNSS loss heuristic `(lat, lon) == (0.0, 0.0)` is specific to the u-blox NEO-6M behavior and does not generalize to GPS modules that output last-known coordinates on fix loss. The battery voltage sag threshold of 3.40 V is a fixed constant; actual brownout behavior is cell-chemistry and load-current dependent. Missing packet estimates are statistical approximations based on the nominal 0.8-second interval; RF burst retransmissions or clock drift may cause false positives. The analyzer does not perform signal-level integrity checks (e.g., CRC verification) as these are not preserved in the CSV format.

---

## 14. Experimental Evaluation of the Telemetry Quality Analyzer

The `TelemetryQualityAnalyzer` was applied to all 10 synthetic flight profiles in `test_cases/`. The following table reports exact measured values. All datasets use the RFC 4180 17-column CSV format with ISO 8601 timestamps at a nominal 0.8-second sampling interval.

**Table 2: Telemetry Data Quality Benchmark Across 10 Flight Scenarios**

| Scenario | Packets | Completeness | Mean Δt (s) | Jitter σ (s) | Duration (s) | Gaps (>2s) | GPS Avail. | Min Bat. (V) | Dropouts |
|---|---|---|---|---|---|---|---|---|---|
| 01 Nominal Sounding | 449 | 100.0% | 0.800 | 0.000 | 358.4 | 0 | 100.0% | 4.055 | 0 |
| 02 High Altitude Burst | 528 | 100.0% | 0.800 | 0.000 | 421.6 | 0 | 100.0% | 4.023 | 0 |
| 03 Severe Wind Shear | 375 | 100.0% | 0.800 | <0.001 | 299.2 | 0 | 100.0% | 4.027 | 0 |
| 04 Apogee Shock/Tumble | 350 | 100.0% | 0.800 | <0.001 | 279.2 | 0 | 100.0% | 3.988 | 0 |
| 05 Parachute Resonance | 325 | 100.0% | 0.800 | <0.001 | 259.2 | 0 | 100.0% | 4.041 | 0 |
| 06 Delayed Chute Deploy | 325 | 100.0% | 0.800 | <0.001 | 259.2 | 0 | 100.0% | 4.037 | 0 |
| 07 Thermal Inversion | 400 | 100.0% | 0.800 | <0.001 | 319.2 | 0 | 100.0% | 4.068 | 0 |
| **08 Sensor Glitch/GPS** | **325** | **100.0%** | **0.800** | **<0.001** | **259.2** | **0** | **100.0%** | **4.051** | **1** |
| **09 Low Battery Sag** | **300** | **100.0%** | **0.800** | **<0.001** | **239.2** | **0** | **100.0%** | **3.254** | **3** |
| 10 Ground Pad Static | 225 | 100.0% | 0.800 | 0.000 | 179.2 | 0 | 100.0% | 4.155 | 0 |

**Key findings from the empirical evaluation:**

- **Packet completeness**: All 10 scenarios achieved 100.0% packet completeness, with zero corrupted rows and zero timestamp gaps detected. This is consistent with the deterministic synthetic generation in `generate_test_cases.js`, which uses a fixed 0.8-second loop with no simulated packet loss.
- **Temporal continuity**: The mean sampling interval across all scenarios is exactly 0.800 s, confirming strict nominal-rate generation. Jitter values on the order of $10^{-16}$ s are floating-point arithmetic artifacts from IEEE 754 double-precision accumulation and are physically insignificant.
- **GNSS fix loss — Scenario 08**: A continuous GNSS dropout lasting **24.0 seconds** (31 packets, indices 126–156, from `T+100.8s` to `T+124.8s`) was correctly detected. This corresponds to the simulated GPS reacquisition window in `genSensorGlitchGpsRecovery()` where `outLat = 0.0`, `outLon = 0.0` for `t ∈ [100, 125]s`.
- **Battery voltage sag — Scenario 09**: Three distinct voltage sag events were detected below the 3.40 V threshold, with the most severe sustained event spanning **49.6 seconds** (63 packets, `T+189.6s` to `T+239.2s`) and reaching a minimum of **3.254 V**. This matches the RF burst discharge simulation in `genLowBatterySag()`.
- **Note on GPS availability metric**: All scenarios report 100.0% GPS *field* availability because the lat/lon values in scenario 08 are populated with `(0.0, 0.0)` rather than `NaN`. The GNSS fix loss is detected via the zero-coordinate heuristic and reported as a dropout event, not as a missing field. This is an intentional design distinction: field availability and fix validity are separately reported.

**Evaluation scope limitation**: These results are derived entirely from synthetic flight profiles generated by `tests/generate_test_cases.js`. Representative real-world hardware flight data have not been collected. Actual flight datasets may exhibit additional anomaly classes not present in these synthetic profiles, including CRC errors, RF burst packet collisions, GPS multipath, and MEMS sensor vibration-induced saturation.

---

## 15. Future Work
[Evidence required from experiment/data.]

## 16. Conclusion
[Evidence required from experiment/data.]

## References
[1] Bhuyan, Maneet and Senanayak, Rishi and Shubham and Vallabh M, Ganesh. "Autonomous Landing Site Selection for Sounding Pico-Satellites Using Quantized Edge TinyML", IEEE Aerospace and Electronic Systems Magazine (Preprint), 2026. (Source: `frontend/results.html`)
