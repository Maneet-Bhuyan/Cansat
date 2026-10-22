# Cognitive CanSat Mission Control: Physics-Informed Telemetry Analytics, Quantized Edge TinyML Landing Safety, and Multi-Tier Vision Verification for Sounding Pico-Satellites

**Authors:** Maneet Bhuyan, Gurbashish Sena Nayak, Shubham Sharma, and Ganesh Vallabh M  
**Date:** October 2026  

---

## Abstract
Sounding pico-satellites (CanSats) operate under severe mass, volume, power, and radio-frequency (RF) bandwidth constraints during high-dynamic atmospheric descent. Conventional CanSat ground stations rely on uncalibrated barometric altimetry—which suffers from Bernoulli dynamic pressure bias during rapid descent—and lack autonomous terrain hazard avoidance or out-of-distribution (OOD) visual fault gating. This paper presents the **Cognitive CanSat Mission Control** architecture, an end-to-end cyber-physical platform integrating (i) an airborne dual-microcontroller avionics and TinyML vision payload, (ii) a physics-informed ground state estimation and machine learning (ML) analytics engine, and (iii) a deterministic telemetry reliability and distributed lakehouse pipeline. On the edge node (AI-Thinker ESP32-CAM, dual-core Xtensa LX6 at $240\,\text{MHz}$, $520\,\text{KB}$ SRAM), a quantized depthwise separable Convolutional Neural Network (**TinyLandingNet**, $7{,}320$ INT8 parameters, $7.15\,\text{KB}$ Flash ROM, $0.783\,\text{MMACs}$) evaluates $64 \times 64$ RGB sub-tiles across a $3 \times 3$ spatial grid within an estimated $16.3\,\text{ms}$ per tile to compute a real-time Safe Landing Area Index (SLAI) and directional evasion vector ($\text{EVADE }\theta^\circ$). To prevent closed-set softmax overconfidence on non-aerial camera inputs (such as ground-handling faces, lens occlusion, or motion blur), a 5-stage **Out-of-Distribution Aerial Vision Guard** gates inference before neural scoring, while heavier reference architectures (**MobileNetV3-Small** and **ResNet-18**) provide high-accuracy ground-station benchmark comparison. Because physical rocket or high-altitude balloon launches were not possible during the current evaluation cycle, we adopt a transparent **Three-Pillar Validation Methodology**: (1) physical bench-top hardware telemetry recorded from the assembled CanSat avionics ($N = 362$ packets across three stationary and dynamic 6-DOF handling sessions at $\sim 868\,\text{m}$ MSL) to extract empirical sensor noise floors ($\sigma_h = 0.423\,\text{m}$, $\sigma_P = 0.143\,\text{hPa}$, $\sigma_a = 0.022\,\text{G}$, $\sigma_g = 2.02\,^\circ/\text{s}$), (2) a 10-scenario stochastic flight test suite ($3{,}536$ packets) and a 100-flight held-out Monte Carlo statistical ensemble ($44{,}555$ frames, disjoint seed `20260921` vs. training seed `1001`) calibrated to the hardware noise floor, and (3) real-world satellite and drone descent imagery ($27{,}000$ EuroSAT multispectral patches plus top-down aerial video sequences). Across the 100-flight Monte Carlo ensemble, our **Hybrid Physics-Informed Kalman + ExtraTrees Sensor Calibrator** reduces vertical position RMSE from $1.776\,\text{m}$ (raw barometric altimetry) to $0.903\,\text{m}$ ($49.2\%$ error reduction), outperforming both standalone 1D Kalman filtering ($1.281\,\text{m}$) and standalone ExtraTrees calibration ($0.982\,\text{m}$), while the **Random Forest Flight Phase Classifier** achieves $97.96\%$ holdout accuracy ($94.37\%$ ensemble mean, $95\%\text{ CI}: [93.92\%, 94.82\%]$) and the **Gradient Boosting Time-to-Touchdown (TTD) Prognostics** model reduces countdown RMSE by $94.8\%$ compared to naive ballistic division ($2.33\,\text{s}$ vs. $44.46\,\text{s}$, $R^2 = 0.9963$, $81.27\%$ coverage on the $80\%$ prediction interval).

## Keywords
CanSat, Pico-Satellite Avionics, TinyML, Edge Computer Vision, Safe Landing Area Index (SLAI), Out-of-Distribution Detection, Adaptive Kalman Filtering, Telemetry Data Quality, Touchdown Prognostics

---

## 1. Introduction
Pico-satellite sounding missions—standardized under the CanSat form factor ($66\,\text{mm}$ diameter, $115\,\text{mm}$ height, $\le 350\,\text{g}$ mass)—serve as vital atmospheric profiling and aerospace systems engineering testbeds [1, 2]. Deployed from sounding rockets, high-altitude latex balloons, or multi-rotor carrier drones at altitudes between $400\,\text{m}$ and $1{,}500\,\text{m}$ Above Ground Level (AGL), a CanSat experiences a rapid sequence of extreme physical regimes within a 3-to-7-minute mission window: pre-launch pad standby, buoyant or powered ascent, pyrotechnic apogee separation ($> 5\,\text{G}$ shock and multi-axis tumbling exceeding $160\,^\circ/\text{s}$), parachute canopy inflation, turbulent pendulum descent ($\pm 18^\circ$ harmonic oscillation), and ground impact recovery [3].

Despite advances in low-power microcontrollers and Micro-Electro-Mechanical Systems (MEMS) sensors, traditional CanSat missions face three persistent engineering bottlenecks:
1. **Aerodynamic and Sensor Artifacts in State Estimation:** Low-cost barometric pressure sensors (BMP180/BMP280) mounted inside a vented cylindrical chassis experience Bernoulli static-port pressure depression ($\Delta P = -\frac{1}{2}\rho v_z^2$) during high-velocity ascent, freefall, and parachute descent. Furthermore, numerical differentiation of noisy barometric altitude ($\sigma_h \approx 0.34\text{--}0.50\,\text{m}$ at $1.25\,\text{Hz}$) amplifies high-frequency variance, corrupting vertical velocity ($v_z$) and apogee detection.
2. **Lack of Onboard Landing Hazard Awareness and Open-Set Vision Safety:** Standard CanSats descend passively without evaluating whether the sub-canopy terrain consists of open grassland (`SAFE_LZ`), dense forest canopy (`OBSTACLE_CANOPY`), urban structures/roads (`CRITICAL_HAZARD`), or rivers and lakes (`WATER_HAZARD`). Worse still, lightweight Convolutional Neural Networks (CNNs) trained on closed-set satellite datasets (such as EuroSAT [4]) suffer from severe softmax overconfidence when exposed to Out-of-Distribution (OOD) frames—such as close-up human faces during bench testing, indoor laboratory backgrounds, or camera lens occlusion—erroneously classifying non-aerial frames as optimal landing zones.
3. **Unquantified Telemetry Link Reliability:** Sub-GHz LoRa and 2.4 GHz ESP-NOW links operating over slant ranges up to $1.5\,\text{km}$ experience polarization fading during tumbling, power-amplifier (PA) brownouts when 1S LiPo voltage sags below $3.40\,\text{V}$, and UART framing corruption. Without deterministic data-quality gating prior to machine learning inference, missing packets and zero-coordinate GNSS dropouts `(0.0, 0.0)` propagate large errors into post-flight kinematic reconstruction.

To address these challenges holistically, we design and validate **Cognitive CanSat Mission Control**, an integrated edge-and-ground intelligence platform. This paper makes the following primary contributions:
- **Empirical Hardware Noise Characterization & Calibrated Stochastic Simulation:** We characterize the physical CanSat sensor suite across $N = 362$ bench-top hardware telemetry packets stored in our SQLite WAL flight database (`data/cansat_missions.db`) and use those exact noise floors to parameterize a 10-scenario benchmark suite and a 100-flight Monte Carlo ensemble.
- **Physics-Informed Hybrid State Estimation & Prognostics:** We fuse an adaptive 1D constant-velocity Kalman filter (`AltitudeKalmanFilter`) with a multi-output ExtraTrees aerodynamic compensator (`sensor_calibrator.joblib`) to eliminate Bernoulli dynamic pressure bias, paired with quantile Gradient Boosting regressors for calibrated Time-to-Touchdown (TTD) uncertainty bounds.
- **Three-Tier Aerial Vision Hierarchy with OOD Guard:** We pair an ultra-compact INT8 edge network (**TinyLandingNet**, $7.15\,\text{KB}$ Flash) with a 5-stage **Out-of-Distribution Aerial Vision Guard** (`ml/vision_guard.py`) and benchmark it against **MobileNetV3-Small** and **ResNet-18** across EuroSAT test imagery and top-down drone descent videos.
- **Deterministic Telemetry Quality Analyzer & Distributed Lakehouse:** We formulate an objective, non-heuristic telemetry quality verification engine (`backend/core/telemetry_analyzer.py`) alongside a Redpanda/Kafka, TimescaleDB, and MinIO S3 telemetry lakehouse.

---

## 2. Problem Statement
Let the airborne pico-satellite state at discrete mission epoch $t_k$ ($\Delta t_0 = 0.8\,\text{s}$, $1.25\,\text{Hz}$ telemetry downlink) be represented by the 13-channel raw observation vector:

$$\mathbf{z}_k = \left[\, T_k,\; P_k,\; h_{\text{raw},k},\; \omega_{x,k},\; \omega_{y,k},\; \omega_{z,k},\; a_{x,k},\; a_{y,k},\; a_{z,k},\; \phi_k,\; \lambda_k,\; \text{RH}_k,\; V_{\text{bat},k} \,\right]^\top \in \mathbb{R}^{13}$$

 accompanied by an asynchronous $320 \times 240$ (QVGA) nadir camera frame $\mathbf{I}_k \in \{0, \ldots, 255\}^{240 \times 320 \times 3}$ captured by an onboard OV3660/OV2640 sensor. During mission execution, the system must solve four coupled estimation and decision problems in real time:
1. **Telemetry Integrity Verification:** Given a packet stream $\{\mathbf{z}_k\}_{k=1}^N$ subject to packet drop probability $p_{\text{drop}} \in [0.005, 0.065]$, UART clock jitter $\sigma_{\Delta t}$, non-numeric framing corruption, and GNSS fix loss $(\phi_k, \lambda_k) = (0, 0)$, objectively quantify packet completeness $C$, temporal gaps $\Delta t_k \ge \tau_{\text{gap}}$, and sensor dropout intervals before downstream ingestion.
2. **Debiased Kinematic Reconstruction:** Recover true altitude $h_k$ and vertical velocity $v_{z,k} = \dot{h}_k$ from raw barometric altitude $h_{\text{raw},k} = h_k + \frac{v_{z,k}^2}{2g} + \epsilon_{h,k}$, where $\frac{v_{z,k}^2}{2g}$ is the positive Bernoulli dynamic pressure altitude bias and $\epsilon_{h,k} \sim \mathcal{N}(0, \sigma_h^2)$ is barometric measurement noise.
3. **Autonomous Flight Phase, Anomaly, and Touchdown Prognostics:** Classify $\mathbf{z}_k$ into one of five operational flight stages $\mathcal{S} = \{\text{PAD\_IDLE}, \text{BALLOON\_ASCENT}, \text{APOGEE\_BURST}, \text{PARACHUTE\_DESCENT}, \text{TOUCHDOWN\_RECOVERY}\}$, compute an unsupervised structural/sensor anomaly score $s_{\text{anom},k} \in [0, 1]$, and estimate remaining Time-to-Touchdown $\hat{\tau}_{\text{TTD},k}$ with calibrated $[q_{10}, q_{90}]$ uncertainty bounds.
4. **Memory-Bounded, OOD-Safe Landing Zone Selection:** Partition $\mathbf{I}_k$ into a $3 \times 3$ spatial grid $\{\mathbf{I}_k^{(r,c)}\}_{r,c \in \{0,1,2\}}$, reject non-aerial or corrupted frames via an OOD guard $G(\mathbf{I}_k) \in \{0, 1\}$, and classify valid aerial sectors within the strict $520\,\text{KB}$ SRAM / $< 150\,\text{ms}$ latency budget of an ESP32 microcontroller to derive a safe steering heading $\theta_{\text{evade}}$.

---

## 3. Objectives
To solve the problem statement for both operational field deployment and rigorous academic evaluation, the specific engineering objectives of this work are:
1. **Hardware-Grounded Sensor Characterization:** Record and analyze real bench-top telemetry from the physical CanSat hardware across stationary and dynamic attitude regimes to establish empirical noise covariances for all onboard sensors.
2. **Sub-Meter State Estimation & Calibrated Prognostics:** Achieve $< 1.15\,\text{m}$ altitude RMSE across randomized flight profiles by combining adaptive Kalman filtering with physics-informed ML calibration, and achieve $> 90\%$ error reduction over naive ballistic TTD estimation during variable-drag descent.
3. **Microcontroller-Compliant Edge Vision with OOD Immunity:** Design an INT8-quantized CNN requiring $< 25\,\text{KB}$ Flash ROM and $< 25\,\text{ms}$ per-tile inference on the ESP32-CAM with $> 92\%$ accuracy on 4-class EuroSAT terrain classification, while achieving $100\%$ rejection of non-aerial OOD test inputs (human faces, solid occlusions, indoor clutter) and benchmarking against heavier ground-station backbones (`MobileNetV3-Small` and `ResNet-18`).
4. **Full-Stack Mission Control & Reproducible Auditability:** Provide an interactive, zero-install Web Serial / WebSocket Mission Control interface (`frontend/dashboard.html`) with live 10-scenario simulation streaming, automated SQLite WAL flight persistence (`data/cansat_missions.db`), and automated 300-DPI PDF/Markdown Post-Flight Review (PFR) reporting.

---

## 4. System Architecture
The Cognitive CanSat platform employs a dual-link, split-compute architecture separating hard real-time airborne sensing from high-throughput ground-station analytics (Figure 1):

```
+-----------------------------------------------------------------------------------+
|                        AIRBORNE CANSAT PAYLOAD (350g, 66x115mm)                   |
|                                                                                   |
|  +-----------------------------------+     +-----------------------------------+  |
|  |    Primary Avionics MCU (STM32/ESP)|     |  Edge Vision Node (ESP32-CAM)     |  |
|  | - BMP280 Baro (Pressure, Temp, Alt|     | - OV3660/OV2640 Camera (320x240)  |  |
|  | - SHT31 / DHT11 Humidity          |     | - TinyLandingNet INT8 (7.15 KB)   |  |
|  | - MPU6050 6-DOF IMU (Accel, Gyro) |     | - 3x3 Spatial Hazard Grid + VARI  |  |
|  | - u-blox NEO-6M GNSS (Lat, Lon)   |     | - Escape Vector (EVADE theta deg) |  |
|  +-----------------+-----------------+     +-----------------+-----------------+  |
|                    | 433/868/915 MHz LoRa                    | 2.4 GHz ESP-NOW    |
+--------------------|-----------------------------------------|--------------------+
                     v (1.25 Hz Telemetry CSV)                 v (QVGA JPEG + SLAI)
+-----------------------------------------------------------------------------------+
|                     GROUND RECEIVER & FASTAPI ML BACKEND                          |
|  - DualSerialManager (COM4 Telemetry @ 9600/115200 + COM5 Video @ 460800 baud)    |
|  - TelemetryQualityAnalyzer (Packet Completeness, Jitter, Dropouts, Bounds)       |
|  - KinematicsEngine (Adaptive 1D Kalman Filter + Complementary Attitude Fusion)   |
|  - AtmosphericEngine (Hypsometric Alt, Magnus-Tetens Dew Point, Moist Air Density)|
|  - Tabular ML Suite (RF Phase, PyOD IForest Anomaly, GBR Apogee/TTD, ExtraTrees)  |
|  - Vision Benchmark & OOD Guard (5-Stage Aerial Guard + TinyNet/MobileNet/ResNet) |
|  - Persistence & Lakehouse (SQLite WAL DB + Redpanda/Kafka + TimescaleDB + MinIO) |
+-----------------------------------------------------------------------------------+
```

1. **Airborne Avionics & Vision Subsystem:** The primary flight controller polls the barometric pressure/temperature transducer (BMP280), relative humidity sensor (DHT11/SHT31), 6-axis inertial measurement unit (MPU6050 configured at $\pm 16\,\text{G}$ and $\pm 2000\,^\circ/\text{s}$), u-blox NEO-6M GPS receiver, and 1S LiPo ADC divider every $800\,\text{ms}$ ($1.25\,\text{Hz}$). In parallel, an AI-Thinker ESP32-CAM module captures nadir QVGA frames, executes INT8 `TinyLandingNet` inference (`firmware/esp32_cam_airborne/model_data.h`), and transmits compressed MJPEG frames plus 3x3 SLAI telemetry over 2.4 GHz ESP-NOW.
2. **Ground Receiver & Dual Serial Bridge:** The ground station (`backend/core/serial_manager.py`) manages concurrent non-blocking threads for telemetry (`COM4`) and high-speed camera reception (`COM5` at $460{,}800$ baud), or connects directly to the browser via the Chromium Web Serial API (`navigator.serial.requestPort`).
3. **FastAPI Ground Analytics & Lakehouse Backend:** Incoming packets are validated by `TelemetryQualityAnalyzer`, filtered by `KinematicsEngine` and `AtmosphericEngine`, scored by the scikit-learn/PyOD tabular ML suite and PyTorch/ONNX vision engine (`backend/app.py`), persisted into an ACID-compliant SQLite Write-Ahead Logging (WAL) database (`backend/core/database.py`), and asynchronously streamed to a Redpanda/Kafka message broker (`backend/core/pipeline_bridge.py`).

---

## 5. Telemetry and Data Acquisition
### 5.1 Wire Protocol and Derived Kinematics
Each downlink telemetry frame is transmitted as an ASCII comma-separated line containing 13 primary sensor channels, which the ground station enriches with an ISO 8601 UTC timestamp and 3 derived attitude/acceleration norms to form the 17-column RFC 4180 archival schema (`timestamp,temp,pressure,altitude,gx,gy,gz,ax,ay,az,lat,lon,humidity,batteryVoltage,pitch,roll,accelMag`). Instantaneous resultant acceleration magnitude $|\mathbf{a}|$ (in $G$) and gravity-referenced attitude angles (pitch $\theta$, roll $\phi$ in degrees) are derived via:

$$|\mathbf{a}| = \sqrt{a_x^2 + a_y^2 + a_z^2}, \qquad \theta = \text{atan2}(a_y, a_z)\frac{180}{\pi}, \qquad \phi = \text{atan2}\!\left(-a_x, \sqrt{a_y^2 + a_z^2}\right)\frac{180}{\pi}$$

### 5.2 Atmospheric Physics Engine
Implemented in `backend/core/atmospheric.py`, the `AtmosphericEngine` computes three meteorological sounding metrics from each packet:
1. **Hypsometric Barometric Altimetry:** Using the International Standard Atmosphere (ISA) lapse rate $L = 0.0065\,\text{K/m}$, universal gas constant $R^* = 8.31432\,\text{N}\cdot\text{m}/(\text{mol}\cdot\text{K})$, molar mass of dry air $M = 0.0289644\,\text{kg/mol}$, and standard gravity $g_0 = 9.80665\,\text{m/s}^2$:

$$h_{\text{baro}} = \frac{T_0}{L}\left[1 - \left(\frac{P}{P_0}\right)^{\frac{R^* L}{g_0 M}}\right] = \frac{T_0}{0.0065}\left[1 - \left(\frac{P}{P_0}\right)^{0.190263}\right]$$

2. **Magnus-Tetens Dew Point ($T_d$):** With empirical constants $a = 17.27$ and $b = 237.7\,^\circ\text{C}$:

$$\gamma(T, \text{RH}) = \frac{a T}{b + T} + \ln\!\left(\frac{\text{RH}}{100}\right), \qquad T_d = \frac{b\,\gamma(T, \text{RH})}{a - \gamma(T, \text{RH})}$$

3. **Humid Air Density ($\rho_{\text{air}}$):** Accounting for water vapor partial pressure $e = \frac{\text{RH}}{100} \cdot 6.1078 \exp\!\left(\frac{17.27 T}{T + 237.3}\right)\,\text{hPa}$ and dry air partial pressure $P_d = P - e$:

$$\rho_{\text{air}} = \frac{100 P_d}{R_d (T + 273.15)} + \frac{100 e}{R_v (T + 273.15)}$$

where $R_d = 287.058\,\text{J}/(\text{kg}\cdot\text{K})$ and $R_v = 461.495\,\text{J}/(\text{kg}\cdot\text{K})$. Because $R_v > R_d$, humid air is less dense than dry air at identical pressure and temperature, directly affecting parachute terminal descent velocity $v_{\text{term}} = \sqrt{\frac{2 m g}{\rho_{\text{air}} C_d A}}$.

---

## 6. Signal Processing and State Estimation
### 6.1 Adaptive 1D Constant-Velocity Kalman Filter
To suppress barometric white noise without introducing excessive phase lag during apogee transition, `backend/core/kinematics.py` implements `AltitudeKalmanFilter` over the state vector $\mathbf{x}_k = [h_k,\; v_{z,k}]^\top$ with state transition matrix $\mathbf{F}_k$, control input matrix $\mathbf{B}_k$, and observation matrix $\mathbf{H}$:

$$\mathbf{F}_k = \begin{bmatrix} 1 & \Delta t_k \\ 0 & 1 \end{bmatrix}, \qquad \mathbf{B}_k = \begin{bmatrix} \frac{1}{2}\Delta t_k^2 \\ \Delta t_k \end{bmatrix}, \qquad \mathbf{H} = \begin{bmatrix} 1 & 0 \end{bmatrix}$$

Driven by earth-vertical inertial acceleration $u_k = (a_{z,k} - 1.0)g_0$ and discrete process noise covariance $\mathbf{Q}_k$:

$$\mathbf{Q}_k = \sigma_q^2 \begin{bmatrix} \frac{1}{4}\Delta t_k^4 & \frac{1}{2}\Delta t_k^3 \\ \frac{1}{2}\Delta t_k^3 & \Delta t_k^2 \end{bmatrix}$$

the filter executes the standard predict-update cycle:

$$\hat{\mathbf{x}}_{k|k-1} = \mathbf{F}_k \hat{\mathbf{x}}_{k-1|k-1} + \mathbf{B}_k u_k, \qquad \mathbf{P}_{k|k-1} = \mathbf{F}_k \mathbf{P}_{k-1|k-1} \mathbf{F}_k^\top + \mathbf{Q}_k$$

$$\mathbf{K}_k = \mathbf{P}_{k|k-1}\mathbf{H}^\top\left(\mathbf{H}\mathbf{P}_{k|k-1}\mathbf{H}^\top + R_k\right)^{-1}, \qquad \hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k\left(h_{\text{raw},k} - \mathbf{H}\hat{\mathbf{x}}_{k|k-1}\right)$$

To prevent filter divergence during violent pyrotechnic separation or delayed-chute freefall, the filter adapts its process variance $\sigma_q^2$ dynamically when $|\mathbf{a}_k| > 2.5\,\text{G}$ and fuses its state prediction with a learned `ExtraTreesRegressor` aerodynamic Venturi depression compensator $\hat{b}_k = f_{\text{ET}}(\mathbf{u}_k)$.

### 6.2 Complementary 3D Attitude Filter and Stationary Tare Calibration
High-frequency gyroscope integration ($\theta_{\text{gyro},k} = \theta_{k-1} + \omega_{x,k}\Delta t_k$) is fused with low-frequency accelerometer gravity vectors via a complementary factor $\alpha = 0.88$:

$$\hat{\theta}_k = \alpha\left(\hat{\theta}_{k-1} + (\omega_{x,k} - b_{\omega,x})\Delta t_k\right) + (1 - \alpha)\theta_{\text{acc},k}$$

During pre-launch ground preparation, an automated $N=20$-sample stationary tare routine (`start_tare()`) measures and nulls out the 3-axis MEMS gyroscope biases $(b_{\omega,x}, b_{\omega,y}, b_{\omega,z})$, static pitch/roll mounting offsets, and launch-pad AGL zero altitude $h_{\text{pad}}$.

---

## 7. Machine Learning Architecture
The machine learning subsystem is partitioned into a 5-model ground-station tabular analytics suite (`ml/train_models.py`, `ml/train_sensor_calibration.py`, `ml/train_touchdown_prognostics.py`) and a 3-tier aerial computer vision hierarchy (`ml/train_tinyml_vision.py`, `ml/benchmark_vision_models.py`, `ml/vision_guard.py`).

### 7.1 Flight Phase Classifier (Random Forest)
A balanced multi-class `RandomForestClassifier` ($120$ trees, maximum depth $12$, standardized via `StandardScaler`) ingests $17$ kinematic and thermodynamic features (`altitude`, `vSpd`, `pressure`, `temp`, `humidity`, `ax`, `ay`, `az`, `accelMag`, `gx`, `gy`, `gz`, `gyroMag`, `batteryVoltage`, `dAlt_pad`, `dTemp_pad`, `dPress_pad`) to classify each packet into `PAD_IDLE`, `BALLOON_ASCENT`, `APOGEE_BURST`, `PARACHUTE_DESCENT`, or `TOUCHDOWN_RECOVERY`. On the stratified 25% holdout split ($N = 884$ test samples from $3{,}536$ total frames), the classifier achieves **$97.96\%$ accuracy** and a **$0.980$ weighted F1-score** ($0.99$ F1 on both `BALLOON_ASCENT` and `PARACHUTE_DESCENT`). Top Gini feature importances are vertical velocity `vSpd` ($18.4\%$), pad-relative altitude `dAlt_pad` ($16.2\%$), `altitude` ($12.1\%$), and `batteryVoltage` ($11.7\%$).

### 7.2 Unsupervised Anomaly Detector (PyOD Isolation Forest)
Because novel mechanical or environmental failures (such as tangled shroud lines, thermal inversions, or EMI bus resets) cannot all be enumerated a priori, an unsupervised `PyOD.IForest` ensemble ($100$ isolation trees, contamination $\eta = 0.06$) is fitted exclusively on $1{,}883$ nominal flight frames (`01`, `02`, `06`, `07`, `10`). Raw decision scores $d(\mathbf{x}) \in [-0.1401, +0.2459]$ are min-max normalized into $[0, 1]$ and combined with deterministic kinematic safety envelopes ($|\mathbf{a}| > 4.0\,\text{G}$, $|\boldsymbol{\omega}| > 150\,^\circ/\text{s}$, $V_{\text{bat}} < 3.40\,\text{V}$). Across the 100-flight Monte Carlo ensemble, the Isolation Forest achieves an **ROC-AUC of $0.8407$** in isolating injected structural and electrical anomalies.

### 7.3 Apogee Predictor & Physics-Informed Sensor Calibrator
- **Apogee Regressor (`apogee_regressor.joblib`):** A `GradientBoostingRegressor` ($80$ estimators, depth $4$, learning rate $0.1$) predicts peak mission apogee during ascent, achieving $R^2 = 0.9753$ on the stochastic dataset ($R^2 = 0.9951$ under zero-dropout conditions).
- **Multi-Output Sensor Calibrator (`sensor_calibrator.joblib`):** A 120-tree `ExtraTreesRegressor` wrapped in a `RobustScaler` (`residual_pipeline`, trained on an independent 80-flight calibration ensemble with `seed=1001`) maps $13$ noisy barometric and IMU inputs to scale-invariant aerodynamic Venturi bias and vertical velocity, achieving **altitude $R^2 = 1.0000$ ($\text{RMSE} = 0.959\,\text{m}$)** on the 10-scenario suite and **$0.903\,\text{m}$ hybrid RMSE ($-49.2\%$ error reduction)** on the 100-flight unseen test ensemble (`seed=20260921`).

### 7.4 Descent Aerodynamics & Quantile Touchdown Prognostics
Trained on $1{,}577$ descent frames across $9$ airborne scenarios (`ml/train_touchdown_prognostics.py`), this pipeline extracts $21$ aerodynamic features including Ideal Gas Law air density $\rho_{\text{air}}$, dynamic pressure $q = \frac{1}{2}\rho_{\text{air}}v_z^2$, and kinetic energy $E_k = \frac{1}{2}m v_z^2$ ($m = 0.35\,\text{kg}$):
- **Point & Quantile TTD Regressors (`touchdown_prognostics.joblib`):** Three `GradientBoostingRegressor` models estimate median Time-to-Touchdown ($\alpha = 0.50$, squared error) and calibrated $10\text{th}$ / $90\text{th}$ percentile bounds ($\alpha \in \{0.10, 0.90\}$, pinball quantile loss). On the holdout test set ($N = 395$), the median regressor achieves **$R^2 = 0.9963$, $\text{RMSE} = 2.33\,\text{s}$, and $\text{MAE} = 1.17\,\text{s}$**—representing a **$94.8\%$ error reduction** over the naive physics baseline $\tau_{\text{naive}} = h / |v_z|$ ($\text{RMSE} = 44.46\,\text{s}, \text{MAE} = 9.71\,\text{s}$). The $[q_{10}, q_{90}]$ interval achieves an empirical **Prediction Interval Coverage Probability (PICP) of $81.27\%$** (target $80.0\%$).
- **Descent Regime Classifier:** A parallel Random Forest classifies descent stability into `NOMINAL_CANOPY`, `PENDULUM_OSCILLATION`, `BALLISTIC_FREEFALL`, and `TERMINAL_FLARE_TOUCHDOWN` with **$99.75\%$ test accuracy**.

### 7.5 Three-Tier Aerial Computer Vision & Out-of-Distribution (OOD) Guard
#### 7.5.1 TinyLandingNet Edge Architecture
To execute directly on the ESP32-CAM (`520 KB` SRAM), `TinyLandingNet` processes $64 \times 64 \times 3$ RGB inputs through a $3 \times 3$ stride-2 stem convolution ($16$ filters) followed by three Depthwise Separable Convolution blocks ($16 \to 32 \to 48 \to 64$ channels, stride 2), Global Average Pooling, and a 4-class linear head (`SAFE_LZ`, `OBSTACLE_CANOPY`, `CRITICAL_HAZARD`, `WATER_HAZARD`). Trained on $27{,}000$ EuroSAT Sentinel-2 patches mapped to landing safety classes, `TinyLandingNet` contains only **$6{,}996$ trainable FP32 parameters ($7{,}320$ quantized INT8 parameters)**, occupying **$7.15\,\text{KB}$ of Flash ROM** (`firmware/esp32_cam_airborne/model_data.h`, $52{,}937$ bytes C header) and requiring **$783{,}360$ MACs ($1.567\,\text{MFLOPs}$)**. On the $4{,}050$-image holdout test set, it achieves **$93.04\%$ accuracy** and **$93.21\%$ macro F1**, with an estimated **$16.3\,\text{ms}$ per-tile execution latency** on the $240\,\text{MHz}$ Xtensa LX6 ($0.055\,\text{ms}$ via ONNX Runtime on host CPU).

#### 7.5.2 Five-Stage Out-of-Distribution (OOD) Aerial Vision Guard
Because a 4-class softmax layer $\mathbf{p} = \text{softmax}(\mathbf{z}/T)$ must sum to $1.0$ even on non-aerial inputs, unguarded edge CNNs misclassify close-up human faces or laboratory interiors as `SAFE_LZ`. We implement `AerialVisionGuard` (`ml/vision_guard.py`) to gate every frame before and after neural evaluation using five fast statistical checks ($< 1.8\,\text{ms}$ overhead):
1. **Exposure & Occlusion Gate:** Rejects frames with mean luminance $\mu_Y < 18$ (lens cap/darkness), $\mu_Y > 245$ (sensor saturation), or dynamic range $\sigma_Y < 6.0$ (uniform surface occlusion).
2. **Portrait Skin-Tone & Central Blob Dominance Gate:** Transforms RGB into $YC_bC_r$ chrominance space ($C_b \in [77, 127], C_r \in [133, 173]$). Frames where central skin-tone pixel fraction exceeds $22\%$ with warm red-over-green dominance ($R > G + 12$) and negative Visible Atmospherically Resistant Index ($\text{VARI} = \frac{G - R}{G + R - B} < -0.04$) are rejected as close-up human faces (`OOD_PORTRAIT_OR_CLOSEUP_SUBJECT`).
3. **Laplacian Micro-Texture Density:** Nadir aerial terrain exhibits high spatial frequency variance $\text{Var}(\nabla^2 Y)$, whereas out-of-focus close-ups or indoor walls exhibit smooth gradients in the central $50\%$ FOV relative to the periphery.
4. **Energy-Based LogSumExp & Shannon Entropy Gate:** Following Liu et al. [8], we compute Helmholtz free energy $E(\mathbf{x}; T) = -T \ln \sum_{c=1}^4 \exp(z_c / T)$ and normalized Shannon entropy $H(\mathbf{p}) = -\frac{1}{\ln 4}\sum_{c=1}^4 p_c \ln p_c$. Frames with $H(\mathbf{p}) > 0.78$ or maximum temperature-scaled confidence $\max_c p_c < 0.48$ are flagged as `OOD_HIGH_ENTROPY_UNCERTAIN`.
5. **VARI Spectral Consistency Cross-Check:** If the CNN predicts `SAFE_LZ` (vegetated/open meadow) or `OBSTACLE_CANOPY` (forest) with $> 70\%$ confidence, but the physical spectral vegetation index is strongly negative ($\text{VARI} < -0.06$), the guard overrides the prediction as a spectral-neural contradiction.

---

## 8. Web-Based Mission Control Interface
The Mission Control web application (`frontend/dashboard.html`, `frontend/tinyml.html`, `frontend/models.html`, `frontend/analysis.html`, `frontend/results.html`, `frontend/pitch.html`) provides a responsive desktop and mobile telemetry environment:
- **12-Tile Real-Time HUD:** Synchronizes Chart.js time-series plots (3-axis acceleration, pitch/roll orientation, vertical speed, altitude, 3-axis gyroscope, dual-axis pressure/temperature, relative humidity), a Three.js WebGL 3D CanSat cylinder attitude model with one-click `TARE UPRIGHT`, a Leaflet/CartoDB dark-matter GNSS ground track mini-map with Haversine distance and Google Maps recovery deep-linking, and a live $320 \times 240$ aerial camera viewport with $3 \times 3$ SLAI hazard overlay.
- **Interactive 10-Scenario Live Streamer & Replay Scrubber:** Operators and judges can select any of the 10 benchmark flight scenarios (`01` through `10`) or procedural simulation directly from the sidebar dropdown (`#demo-scenario-select`) or scrub frame-by-frame at $0.5\times$ to $10\times$ speed.
- **Hybrid Cloud/Shared-Hosting Architecture:** Supports zero-config local execution (`localhost:8000`) as well as split frontend/backend cloud deployment (`?backend=https://...` query parameter persisted in `localStorage`) for hosting the static UI on Hostinger Shared Hosting while routing REST and WebSocket traffic to a containerized FastAPI backend on Hugging Face Spaces (`deploy/`).

---

## 9. Experimental Methodology: Three-Pillar Validation
Because physical high-altitude rocket or balloon launches could not be conducted during the current development phase, we explicitly structure our experimental evaluation around a transparent **Three-Pillar Validation Methodology** that separates real hardware measurements from physics-calibrated simulation:
1. **Pillar 1 — Physical CanSat Hardware Bench-Top Characterization ($N = 362$ Real Packets):** The assembled CanSat avionics payload was operated across three logged sessions in `data/cansat_missions.db`: two stationary bench-top baseline runs (`MSN-20260920-192811-A2F9`, $106$ packets; `MSN-20260920-194606-2DD8`, $135$ packets) at an indoor elevation of $\sim 868\,\text{m}$ MSL ($P \approx 913.0\,\text{hPa}$), and one dynamic 6-DOF handling, tilt, and elevation excitation test (`MSN-20260921-092203-74EE`, $121$ packets). Together with the 10 archived flight scenario replays ($3{,}536$ frames), `data/cansat_missions.db` stores $3{,}898$ total telemetry packets. These real hardware recordings provide the exact empirical sensor noise standard deviations ($\sigma_h, \sigma_P, \sigma_T, \sigma_{\text{RH}}, \sigma_a, \sigma_g, \sigma_V$) used to calibrate our simulation engine.
2. **Pillar 2 — Hardware-Calibrated 10-Scenario Benchmark & 100-Flight Disjoint Monte Carlo Ensemble:** Using the empirical noise floors from Pillar 1, `tests/generate_test_cases.js` (seeded Mulberry32 PRNG) generates 10 canonical flight scenarios ($3{,}536$ packets) incorporating realistic UART/LoRa timing jitter ($\sigma_{\Delta t} \in [8\,\text{ms}, 199\,\text{ms}]$), slant-range and polarization RF packet dropouts, GNSS fix losses, and LiPo voltage sags. To establish rigorous statistical confidence intervals without train-test leakage, `ml/generate_monte_carlo_ensemble.py` (`seed=20260921`, strictly disjoint from `seed=1001` used in `ml/train_sensor_calibration.py`) simulates $N = 100$ randomized 6-DOF flights ($44{,}555$ frames) varying target apogee ($450\text{--}1{,}250\,\text{m}$), ascent velocity ($3.8\text{--}5.4\,\text{m/s}$), parachute drag coefficient ($C_d \in [0.68, 1.32]$), unknown per-flight Venturi coefficient ($c_p \in [0.38, 0.62]$), lateral wind speed ($1.2\text{--}17.5\,\text{m/s}$), and RF packet loss rate ($0.5\text{--}6.5\%$).
3. **Pillar 3 — Real-World Aerial Imagery & OOD Vision Stress Testing:** The computer vision pipeline is trained and evaluated exclusively on real optical data: $27{,}000$ Sentinel-2 satellite patches from the EuroSAT dataset [4], real top-down drone descent video sequences (`tinyml_test_videos/`), and synthetic/real Out-of-Distribution (OOD) test patterns (portrait faces, solid occlusions, high-frequency noise).

---

## 10. Results

### 10.1 Pillar 1: Physical CanSat Hardware Bench-Top Characterization
Table 1a summarizes the empirical sensor statistics extracted from the three physical hardware test missions preserved in `data/cansat_missions.db` (visualized in `reports/figures/paper_fig1_hardware_bench_characterization.png`).

**Table 1a: Empirical Characterization of Physical CanSat Hardware Sessions (`data/cansat_missions.db`)**

| Mission ID | Session Regime | Packets | Altitude Mean ± SD (m MSL) | Pressure Mean ± SD (hPa) | Temp Mean ± SD (°C) | Humidity Mean ± SD (%) | Accel Noise $\sigma_{ax},\sigma_{ay},\sigma_{az}$ (G) | Gyro Noise $\sigma_{gx},\sigma_{gy},\sigma_{gz}$ (°/s) | Battery Mean ± SD (V) |
|---|---|---|---|---|---|---|---|---|---|
| `MSN-20260920-192811-A2F9` | Stationary Bench 1 | 106 | $867.53 \pm 0.503$ | $913.00 \pm 0.001$ | $27.83 \pm 0.184$ | $67.34 \pm 1.522$ | $0.032, 0.019, 0.016$ | $1.75, 2.52, 5.55$ | $5.545 \pm 0.022$ |
| `MSN-20260920-194606-2DD8` | Stationary Bench 2 | 135 | $869.90 \pm 0.343$ | $912.91 \pm 0.285$ | $28.82 \pm 0.146$ | $67.79 \pm 1.509$ | $0.001, 0.001, 0.001$ | $0.001, 0.001, 0.001$ | $5.549 \pm 0.023$ |
| `MSN-20260921-092203-74EE` | Dynamic 6-DOF Tilt | 121 | $883.19 \pm 9.452$ | $911.02 \pm 1.292$ | $30.77 \pm 0.720$ | $74.26 \pm 5.587$ | $0.276, 0.244, 0.095$ | $30.18, 22.84, 24.41$ | $5.541 \pm 0.025$ |
| **Calibrated Noise Floor** | **Stationary Mean** | **241** | **$\sigma_h = 0.423\,\text{m}$** | **$\sigma_P = 0.143\,\text{hPa}$** | **$\sigma_T = 0.165\,^\circ\text{C}$** | **$\sigma_{\text{RH}} = 1.515\%$** | **$\sigma_a = 0.022\,\text{G}$** | **$\sigma_g = 2.02\,^\circ/\text{s}$** | **$\sigma_V = 0.022\,\text{V}$** |

In the stationary runs (`A2F9` and `2DD8`), the barometric altimeter exhibits a 1-sigma white noise floor of $\sigma_h = 0.423\,\text{m}$ around the $868.7\,\text{m}$ MSL laboratory elevation, while the u-blox NEO-6M GPS correctly reports `(0.0, 0.0)` indoors—confirming the physical mechanism behind our zero-coordinate GNSS dropout detector. In the dynamic bench session (`74EE`), manual 6-DOF pitch/roll rotations up to $\pm 42^\circ$ and angular rates from $-114.7\,^\circ/\text{s}$ to $+98.9\,^\circ/\text{s}$ verified real-time Three.js attitude tracking and complementary filter responsiveness without I2C bus lockup.

### 10.2 Pillar 2: 100-Flight Monte Carlo State Estimation & ML Benchmarks
Table 1b reports the statistical performance of the five altitude/velocity state estimation methods across the $N = 100$ held-out randomized Monte Carlo flights (`ml/monte_carlo_benchmarks.json`, visualized in `reports/figures/paper_fig2_monte_carlo_state_estimation.png`).

**Table 1b: 100-Flight Unbiased Monte Carlo State Estimation Ablation ($N = 100$ Disjoint Flights, $44{,}555$ Frames)**

| State Estimation Method | Altitude RMSE Mean ± SD (m) | Altitude RMSE Median [IQR] (m) | Altitude RMSE 95% CI (m) | Velocity RMSE Mean ± SD (m/s) | Velocity RMSE 95% CI (m/s) | Error Reduction vs. Raw |
|---|---|---|---|---|---|---|
| Raw Barometric Altimetry | $1.7759 \pm 0.2584$ | $1.7769\;[0.4150]$ | $[1.7252, 1.8265]$ | $1.4154 \pm 0.2544$ | $[1.3655, 1.4653]$ | Baseline ($0.0\%$) |
| Causal Savitzky-Golay ($N=11, p=2$) | $1.7782 \pm 0.2564$ | $1.7666\;[0.4167]$ | $[1.7279, 1.8284]$ | $1.3182 \pm 0.2286$ | $[1.2734, 1.3630]$ | $+0.1\%$ Alt / $-6.9\%$ Vel |
| Adaptive 1D EKF (No ML Compensation) | $1.2810 \pm 0.1449$ | $1.2725\;[0.2259]$ | $[1.2526, 1.3094]$ | $1.1066 \pm 0.1059$ | $[1.0858, 1.1273]$ | $-27.9\%$ Alt / $-21.8\%$ Vel |
| Pure ExtraTrees Calibrator (No EKF) | $0.9817 \pm 0.1463$ | $0.9614\;[0.2073]$ | $[0.9530, 1.0103]$ | $0.8962 \pm 0.0942$ | $[0.8777, 0.9147]$ | $-44.7\%$ Alt / **$-36.7\%$ Vel** |
| **Hybrid EKF + ExtraTrees ML** | **$0.9026 \pm 0.1303$** | **$0.8806\;[0.1930]$** | **$[0.8770, 0.9281]$** | **$0.9036 \pm 0.0884$** | **$[0.8863, 0.9209]$** | **$-49.2\%$ Alt / $-36.2\%$ Vel** |

Because standard causal linear filters (Causal Savitzky-Golay) smooth white noise around the Venturi-biased barometric signal $h_{\text{raw}} = h_{\text{true}} + c_p \frac{v_z^2}{2g}(1 + 0.15\sin^2\psi)$, they cannot remove the systematic positive altitude offset during rapid ascent and descent. By learning the aerodynamic Venturi residual on a strictly disjoint training ensemble (`seed=1001`) and fusing with the 1D constant-velocity Kalman filter, our **Hybrid Physics-Informed EKF + ExtraTrees** estimator reduces altitude RMSE by **$49.2\%$** ($0.903\,\text{m}$ vs. $1.776\,\text{m}$), outperforming both the standalone 1D EKF ($1.281\,\text{m}$) and the standalone ExtraTrees regressor ($0.982\,\text{m}$).

Table 1c summarizes the tabular machine learning suite performance across both the 10-scenario stratified holdout split and the 100-flight unseen Monte Carlo ensemble.

**Table 1c: Tabular Machine Learning Performance Summary**

| Subsystem Model | Algorithm | 10-Scenario Holdout Metric | 100-Flight Monte Carlo Ensemble Mean ± SD [95% CI] |
|---|---|---|---|
| **Flight Phase Classifier** | `RandomForestClassifier` (120 trees) | **$97.96\%$ Accuracy** ($0.980$ Weighted F1) | **$94.37\% \pm 2.30\%$** ($[93.92\%, 94.82\%]$) |
| **Unsupervised Anomaly Detector** | `PyOD.IForest` (100 trees, $\eta=0.06$) | $100\%$ Shock/Tumble/Sag Event Detection | **$\text{ROC-AUC} = 0.8407$** across $44{,}555$ frames |
| **Physics Sensor Calibrator** | Multi-Output `ExtraTreesRegressor` | **$R^2 = 1.0000$**, $\text{RMSE} = 0.959\,\text{m}$ | **$0.903\,\text{m}$** Hybrid Altitude RMSE ($-49.2\%$) |
| **Touchdown TTD Prognostics** | Quantile `GradientBoostingRegressor` | **$R^2 = 0.9963$**, $\text{RMSE} = 2.33\,\text{s}$ ($81.27\%$ PICP) | **$74.8\% \pm 18.0\%$** Unpadded $[P10, P90]$ Coverage |
| **Descent Regime Classifier** | `RandomForestClassifier` (4 regimes) | **$99.75\%$ Accuracy** ($N=395$ test frames) | **$96.8\% \pm 1.9\%$** Regime Accuracy |

### 10.3 Sensor Suite Ablation Study
To evaluate graceful degradation under partial hardware failure, we conducted a 4-tier sensor ablation study (`ml/ablation_benchmarks.json`) across all 10 flight scenarios comparing `Full_Suite` (Baro + IMU + Env + GPS), `No_IMU` (MPU6050 failure), `No_Env_Sensors` (BMP280/DHT11 temperature/humidity failure), and `GPS_Only`. Across nominal and moderate-drift flights (`01`, `02`, `04`–`07`, `09`), horizontal touchdown coordinate regression maintains sub-meter accuracy ($\text{MAE} \in [0.29\,\text{m}, 0.58\,\text{m}]$, $R^2 = 1.0000$) across all four feature subsets. Under severe wind shear (`03_severe_wind_shear_drift`, $\text{MAE} = 3.68\,\text{m}$) and 25-second GNSS blackout (`08_sensor_glitch_gps_recovery`, $\text{MAE} = 2.93\,\text{m}$), inertial and barometric dead-reckoning bound localization drift to $< 3.7\,\text{m}$ during satellite loss.

### 10.4 Pillar 3: Three-Tier Vision Hierarchy & Out-of-Distribution (OOD) Guard
Table 1d compares the airborne edge model (`TinyLandingNet`) against the two ground-station reference backbones (`MobileNetV3-Small` and `ResNet-18`, trained for 15 epochs on $27{,}000$ EuroSAT RGB patches on an NVIDIA GeForce RTX 4060 Laptop GPU, `ml/gpu_training_summary.json`) and the 5-stage `AerialVisionGuard` (`ml/vision_model_comparison.json`, visualized in `reports/figures/paper_fig4_vision_hierarchy_and_ood_guard.png`).

**Table 1d: Three-Tier Computer Vision Architecture & OOD Guard Benchmark (Trained on NVIDIA RTX 4060 CUDA)**

| Vision Model Tier | Deployment Target | Parameters | FP32 / INT8 Size | MACs | EuroSAT 4-Class Acc. | Macro F1 | Host CPU / Edge Latency | OOD Non-Aerial Rejection |
|---|---|---|---|---|---|---|---|---|
| **Tier 1: TinyLandingNet (INT8)** | Airborne ESP32-CAM ($240\,\text{MHz}$) | $6{,}996$ | $27.3\,\text{KB}$ / **$7.15\,\text{KB}$** | $0.78\,\text{M}$ | **$93.04\%$** ($93.80\%$ val) | **$93.21\%$** | **$0.055\,\text{ms}$** (ONNX) / $2.55\,\text{ms}$ (PyTorch CPU) / $16.3\,\text{ms}$ (MCU) | **$100\%$** (with `AerialVisionGuard`) |
| **Tier 2: MobileNetV3-Small** | Companion / Ground Laptop (Fast) | $1{,}521{,}956$ | $5{,}806\,\text{KB}$ / $1{,}486.3\,\text{KB}$ | $56.4\,\text{M}$ | **$99.68\%$** (Epoch 11/15) | **$99.66\%$** | **$25.09\,\text{ms}$** ($39.9\,\text{FPS}$ PyTorch CPU) | **$100\%$** (with `AerialVisionGuard`) |
| **Tier 3: ResNet-18** | Ground Station Server (Heavy) | $11{,}178{,}564$ | $42{,}643\,\text{KB}$ / $10{,}916.6\,\text{KB}$ | $1{,}814.0\,\text{M}$ | **$99.73\%$** (Epoch 15/15) | **$99.71\%$** | **$31.86\,\text{ms}$** ($31.4\,\text{FPS}$ PyTorch CPU) | **$100\%$** (with `AerialVisionGuard`) |

While `MobileNetV3-Small` ($99.68\%$ val accuracy, $1{,}158.3\,\text{s}$ CUDA training time) and `ResNet-18` ($99.73\%$ val accuracy, $1{,}060.3\,\text{s}$ CUDA training time) achieve a $+6.64\%$ to $+6.69\%$ accuracy gain over `TinyLandingNet` ($93.04\%$ holdout test / $93.80\%$ val), `ResNet-18` requires **$1{,}597\times$ more parameters** ($11.18\,\text{M}$ vs. $6{,}996$) and **$2{,}315\times$ more MACs**, exceeding the ESP32-CAM $520\,\text{KB}$ SRAM ceiling by $> 80\times$. Crucially, testing on non-aerial OOD inputs (close-up human portraits/faces, solid dark occlusions, uniform bright surfaces, and random noise) demonstrated that *all* unguarded closed-set CNNs produce false `SAFE_LZ` or `CRITICAL_HAZARD` classifications, whereas prepending the 5-stage `AerialVisionGuard` achieves **$100\%$ OOD detection and rejection** across all tested non-aerial failure modes while passing $100\%$ of valid top-down drone descent video sequences (`tinyml_test_videos/`).

---

## 11. Discussion
The experimental findings highlight three key architectural insights for resource-constrained aerospace cyber-physical systems:
1. **Physics-Informed Debiasing Outperforms Pure Signal Smoothing:** As shown in Table 1b, neither a standalone causal Savitzky-Golay filter nor a standard constant-velocity Kalman filter can eliminate the positive altitude bias caused by Bernoulli static-port suction ($\Delta h \approx c_p \frac{v_z^2}{2g}$) during high-speed descent. Combining Kalman velocity estimation with tree-based aerodynamic residual compensation reduces vertical position error by $49.2\%$.
2. **Domain-Specific OOD Gating is Mandatory for Edge TinyML Safety:** When deploying compact classifiers trained on nadir satellite patches (EuroSAT) to embedded cameras that undergo bench-top testing and pre-launch handling, model accuracy on in-distribution test sets ($93.04\%$) is insufficient for operational safety. The hybrid spectral-statistical `AerialVisionGuard` ($YC_bC_r$ portrait detection, Laplacian micro-texture variance, LogSumExp free energy, and VARI vegetation cross-checking) eliminates false landing clearances on human faces and occluded frames with negligible compute cost.
3. **Quantile Uncertainty Bounds Transform Countdown Reliability:** During turbulent parachute descent (`05_parachute_pendulum_resonance`) or delayed canopy deployment (`06_delayed_chute_deployment`), instantaneous vertical velocity fluctuates rapidly, causing naive $h / |v_z|$ countdown timers to oscillate by $> 40\,\text{s}$. Quantile Gradient Boosting (`touchdown_prognostics.joblib`) provides stable countdown predictions ($\text{RMSE} = 2.33\,\text{s}$) with an $81.27\%$-accurate $[q_{10}, q_{90}]$ confidence band on the holdout split ($74.8\%$ unpadded across the 100-flight Monte Carlo ensemble) for camera high-rate burst triggering.

---

## 12. Limitations and Methodological Transparency
In accordance with rigorous scientific reporting standards, we explicitly note the following limitations of the current study:
1. **Absence of Physical Rocket or High-Altitude Balloon Flight Tests:** While the sensor noise floors, biases, and 6-DOF IMU dynamics in Table 1a were recorded directly from the physical CanSat hardware across $N = 362$ bench-top packets (`data/cansat_missions.db`), the full-altitude flight trajectories (`01` through `10` and the 100-flight Monte Carlo ensemble) are physics-grounded stochastic simulations calibrated to those empirical hardware parameters. Full airborne drop tests from a carrier drone or sounding rocket are required to validate aerodynamic wake interactions and long-range LoRa multipath fading in free flight.
2. **ESP32-CAM Cycle-Budget Estimation:** While host ONNX Runtime latency ($0.055\,\text{ms}$) and CPU/GPU benchmarks for `TinyLandingNet`, `MobileNetV3-Small`, and `ResNet-18` were directly timed in hardware, the $16.3\,\text{ms}$ per-tile ESP32-CAM execution latency is derived analytically from the exact layer-wise MAC count ($783{,}360$ MACs at $5$ cycles/MAC on the $240\,\text{MHz}$ Xtensa LX6 DSP pipeline).
3. **Heuristic Thresholds in OOD and Telemetry Diagnostics:** The `AerialVisionGuard` thresholds ($YC_bC_r$ skin ratio $> 0.22$, Shannon entropy $> 0.78$) and `TelemetryQualityAnalyzer` thresholds ($V_{\text{bat}} < 3.40\,\text{V}$, GNSS loss at `(0.0, 0.0)`) are tailored to the OV3660/OV2640 camera, 1S LiPo chemistry, and u-blox NEO-6M GPS receiver used in our hardware design.

---

## 13. Telemetry Data Quality and Reliability Assessment

### 13.1 Motivation and Scope
Reliable post-flight analysis and real-time machine learning inference are contingent on the integrity of the underlying telemetry dataset. Corrupted packets, timestamp discontinuities, GNSS lock losses, and sensor dropouts introduce systematic bias into downstream models. For instance, the Random Forest flight phase classifier (Section 7.1) uses altitude, acceleration magnitude, and vertical velocity derived directly from raw telemetry fields; missing or erroneous samples propagate errors through kinematic integration steps. Similarly, the Savitzky-Golay filter used in post-flight reconstruction requires temporally uniform samples to preserve the spectral properties of the velocity signal.

This section describes an objective, deterministic data quality assessment pipeline implemented in `backend/core/telemetry_analyzer.py` and exposed via REST endpoints `/api/analysis/quality/{scenario_name}` and `/api/analysis/quality/analyze-csv`. The analyzer reports only measurable facts and does not assign subjective quality scores.

### 13.2 Packet Integrity
Each row in the telemetry CSV constitutes one packet. The analyzer reports:
- **Total rows** $N$: the count of lines excluding the RFC 4180 header.
- **Valid packets** $N_v$: rows in which all 13 primary telemetry channels are numeric, finite, and parsable.
- **Corrupted rows** $N_c$: rows with non-numeric tokens (e.g., `"CORRUPT"`, `"ERR"`), empty cells, floating-point infinities, or pandas parse failures.
- **Duplicate packets** $N_d$: exact row duplicates or repeated ISO 8601 timestamps detected via pandas `.duplicated()`.
- **Missing packets estimate** $\hat{N}_m$: estimated sequence losses derived from temporal gap analysis (see Section 13.3).

Packet completeness is defined as:

$$C = \frac{N_v}{N_v + N_c + \hat{N}_m} \times 100\%$$

### 13.3 Temporal Integrity
The CanSat telemetry system operates at a fixed nominal sampling interval of $\Delta t_0 = 0.8\,\text{s}$ ($1.25\,\text{Hz}$). Temporal integrity is evaluated by computing pairwise successive timestamp differences:

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
For each of the 13 primary telemetry fields (`temp`, `pressure`, `altitude`, `gx`, `gy`, `gz`, `ax`, `ay`, `az`, `lat`, `lon`, `humidity`, `batteryVoltage`) and 3 derived fields (`pitch`, `roll`, `accelMag`), the analyzer computes non-null count $n_k$, missing count $m_k = N - n_k$, availability percentage $A_k = (n_k / N) \times 100\%$, observed range $[\min(k), \max(k)]$, and out-of-range count against hardware datasheet envelopes (Table 1).

**Table 1: Physical Sensor Operating Envelopes**

| Field | Sensor | Range |
|---|---|---|
| `temp` | BMP180/DHT11 | $-50$ to $+85\,^\circ\text{C}$ |
| `pressure` | BMP180/BMP280 | $10$ to $1150\,\text{hPa}$ |
| `ax`, `ay`, `az` | MPU6050 | $\pm 16.0\,\text{G}$ |
| `gx`, `gy`, `gz` | MPU6050 | $\pm 2000\,^\circ/\text{s}$ |
| `humidity` | DHT11/SHT31 | $0$ to $100\%$ |
| `batteryVoltage` | 1S LiPo | $3.00$ to $4.35\,\text{V}$ |
| `lat` | u-blox NEO-6M | $-90^\circ$ to $+90^\circ$ |
| `lon` | u-blox NEO-6M | $-180^\circ$ to $+180^\circ$ |

### 13.5 GNSS Fix Loss and LiPo Voltage Sag Detection
A GNSS fix loss event is detected when consecutive packets report coordinates `(lat, lon) = (0.0, 0.0)` within a tolerance of $10^{-5}$ degrees across $\ge 2$ consecutive packets. Similarly, a battery voltage sag event is defined as a contiguous run of $\ge 2$ consecutive packets with `batteryVoltage < 3.40 V`, corresponding to the 1S LiPo under-load brownout threshold.

---

## 14. Experimental Evaluation of the Telemetry Quality Analyzer

The `TelemetryQualityAnalyzer` was applied to all 10 hardware-calibrated stochastic flight profiles in `test_cases/` (visualized in `reports/figures/paper_fig3_10scenario_kinematics_envelope.png`). Table 2 reports the exact measured telemetry reliability metrics across the $3{,}536$ total packets.

**Table 2: Telemetry Data Quality Benchmark Across 10 Stochastic Flight Scenarios**

| Scenario | Raw Rows | Valid Packets | Corrupt Rows | Est. Lost Packets | Completeness (%) | Mean $\Delta t$ (s) | Jitter $\sigma_{\Delta t}$ (s) | Gaps ($>2\text{s}$) | Min Bat. (V) | Dropouts |
|---|---|---|---|---|---|---|---|---|---|---|
| `01_nominal_sounding_flight` | 423 | 423 | 0 | 2 | $99.53\%$ | $0.804$ | $0.079$ | 1 | $4.051$ | 0 |
| `02_high_altitude_burst_1200m` | 517 | 517 | 0 | 8 | $98.48\%$ | $0.812$ | $0.169$ | 3 | $3.982$ | 0 |
| `03_severe_wind_shear_drift` | 370 | 370 | 0 | 5 | $98.67\%$ | $0.811$ | $0.151$ | 2 | $4.015$ | 0 |
| `04_apogee_ejection_shock_tumble` | 344 | 343 | 1 | 6 | $98.00\%$ | $0.814$ | $0.185$ | 2 | $3.996$ | 0 |
| `05_parachute_pendulum_resonance` | 323 | 323 | 0 | 2 | $99.38\%$ | $0.805$ | $0.091$ | 1 | $4.039$ | 0 |
| `06_delayed_chute_deployment` | 320 | 320 | 0 | 5 | $98.46\%$ | $0.813$ | $0.165$ | 2 | $4.049$ | 0 |
| `07_thermal_inversion_sounding` | 398 | 398 | 0 | 2 | $99.50\%$ | $0.804$ | $0.082$ | 1 | $4.045$ | 0 |
| **`08_sensor_glitch_gps_recovery`** | **322** | **320** | **2** | **3** | **$98.46\%$** | **$0.807$** | **$0.136$** | **1** | **$4.050$** | **1 (GNSS 28 pkts)** |
| **`09_low_battery_voltage_sag`** | **294** | **294** | **0** | **6** | **$98.00\%$** | **$0.816$** | **$0.199$** | **2** | **$3.250$** | **3 (Bat Sag)** |
| `10_ground_pad_static_test` | 225 | 225 | 0 | 0 | $100.00\%$ | $0.800$ | $0.008$ | 0 | $4.156$ | 0 |

**Key findings from the empirical evaluation:**
- **Stochastic RF Packet Completeness & Slant-Range Fading:** Unlike idealized zero-loss loops, the stochastic test suite captures realistic LoRa link degradation ranging from $100.00\%$ completeness on the short-range static pad baseline (`10_ground_pad_static_test`, $\sigma_{\Delta t} = 8\,\text{ms}$) to $98.48\%$ during the $1{,}200\,\text{m}$ high-altitude burst (`02_high_altitude_burst_1200m`, $3$ slant-range dropout gaps totaling $8$ lost packets) and $98.00\%$ during violent 3-axis tumbling (`04_apogee_ejection_shock_tumble`, $2$ antenna polarization fade gaps totaling $6$ lost packets plus $1$ pyrotechnic I2C pressure glitch).
- **EMI & Framing Corruption Detection (`08_sensor_glitch_gps_recovery`):** The analyzer accurately isolated $2$ transient sensor framing corruptions ($1$ missing humidity sample at `T+96.0s` and $1$ non-numeric `"ERR"` temperature token at `T+131.2s`), $1$ RF dropout gap ($3$ lost packets during the EMI burst at `T+114.4s`), and a continuous $28$-packet GNSS fix loss `(0.0, 0.0)` spanning $24.8\,\text{s}$.
- **PA Brownout & LiPo Sag Correlation (`09_low_battery_voltage_sag`):** Three distinct voltage sag intervals below $3.40\,\text{V}$ were logged (minimum $3.250\,\text{V}$), accompanied by $2$ RF transmission dropout gaps ($6$ lost packets) induced by power-amplifier current spikes under depleted cell voltage.

---

## 15. Future Work
Future development will advance the Cognitive CanSat platform along four directions:
1. **Tethered Drone & Sounding Rocket Field Campaigns:** Conducting physical drop tests from a multi-rotor UAV at $400\,\text{m}$ AGL and a high-power sounding rocket at $1{,}000\,\text{m}$ AGL to validate the hybrid Kalman-ExtraTrees Bernoulli compensator against centimeter-grade RTK-GNSS reference trajectories.
2. **Closed-Loop Parafoil Actuation:** Coupling the 3x3 SLAI directional evasion vector ($\text{EVADE }\theta^\circ$) and quantile TTD countdown directly to dual micro-servo parafoil toggle lines to demonstrate closed-loop autonomous hazard avoidance during descent.
3. **ESP-DL Hardware Cycle Profiling & Vision Distillation:** Profiling cycle-exact hardware execution times on the ESP32-S3 vector extensions (ESP-NN / ESP-DL) and applying knowledge distillation from the ground-station `ResNet-18` teacher ($99.73\%$ accuracy) into the airborne `TinyLandingNet` student.
4. **CRC-16 Frame Checksums & Forward Error Correction:** Extending the 13-field ASCII CSV wire protocol with binary Reed-Solomon / CRC-16 framing to distinguish RF bit errors from I2C sensor bus glitches at the physical layer.

---

## 16. Conclusion
This paper presented the design, mathematical formulation, and three-pillar empirical validation of **Cognitive CanSat Mission Control**, an end-to-end telemetry analytics and autonomous landing safety platform for sounding pico-satellites. By calibrating our stochastic flight simulator against $N = 362$ physical CanSat hardware bench-top packets (`data/cansat_missions.db`) and evaluating across both a 10-scenario stress suite ($3{,}536$ packets) and a 100-flight Monte Carlo statistical ensemble, we demonstrated that:
1. Fusing an adaptive 1D Kalman filter with a physics-informed `ExtraTreesRegressor` sensor calibrator compensates for Bernoulli dynamic pressure depression and reduces altitude RMSE by **$40.4\%$** ($1.08\,\text{m}$ vs. $1.81\,\text{m}$ raw barometric altimetry).
2. A multi-model tabular ML pipeline achieves **$97.96\%$ holdout flight phase accuracy** ($93.00\%$ across 100 unseen randomized flights), **$0.8616$ ROC-AUC** in unsupervised anomaly detection, and a **$94.8\%$ reduction in Time-to-Touchdown RMSE** ($2.33\,\text{s}$ vs. $44.46\,\text{s}$ naive baseline) with calibrated $81.27\%$ prediction interval coverage.
3. On the edge vision node, `TinyLandingNet` achieves **$93.04\%$ holdout accuracy** ($93.80\%$ validation) on 4-class EuroSAT terrain evaluation within a **$7.15\,\text{KB}$ INT8 Flash footprint**, while our 5-stage `AerialVisionGuard` provides **$100\%$ rejection of non-aerial Out-of-Distribution inputs** (such as close-up human faces and camera occlusions) alongside heavier CUDA-trained ground-station `MobileNetV3-Small` ($99.68\%$) and `ResNet-18` ($99.73\%$) reference models.

---

## References
[1] R. Walker et al., "ESA Hands-On Space Education Project Activities for University Students: Attracting and Training the Next Generation of Space Engineers," *IEEE Transactions on Education*, vol. 53, no. 4, pp. 608–617, Nov. 2010.  
[2] S. Nakasuka et al., "Evolution from Education to Practical Use in University of Tokyo's Nano-Satellite Activities," *Acta Astronautica*, vol. 66, no. 7–8, pp. 1099–1105, 2010.  
[3] M. Bhuyan, R. Senanayak, Shubham, and G. Vallabh M, "Autonomous Landing Site Selection for Sounding Pico-Satellites Using Quantized Edge TinyML," *IEEE Aerospace and Electronic Systems Magazine (Preprint)*, 2026.  
[4] P. Helber, B. Bischke, A. Dengel, and D. Borth, "EuroSAT: A Novel Dataset and Deep Learning Benchmark for Land Use and Land Cover Classification," *IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing*, vol. 12, no. 7, pp. 2217–2226, July 2019.  
[5] A. G. Howard et al., "Searching for MobileNetV3," in *Proc. IEEE/CVF International Conference on Computer Vision (ICCV)*, Seoul, Korea, 2019, pp. 1314–1324.  
[6] K. He, X. Zhang, S. Ren, and J. Sun, "Deep Residual Learning for Image Recognition," in *Proc. IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*, Las Vegas, NV, USA, 2016, pp. 770–778.  
[7] B. Jacob et al., "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference," in *Proc. IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*, Salt Lake City, UT, USA, 2018, pp. 2704–2713.  
[8] W. Liu, X. Wang, J. Owens, and Y. Li, "Energy-Based Out-of-Distribution Detection," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 21464–21475, 2020.  
[9] A. A. Gitelson, Y. J. Kaufman, R. Stark, and D. Rundquist, "Novel Algorithms for Remote Estimation of Vegetation Fraction," *Remote Sensing of Environment*, vol. 80, no. 1, pp. 76–87, 2002.  
[10] F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation Forest," in *Proc. 8th IEEE International Conference on Data Mining (ICDM)*, Pisa, Italy, 2008, pp. 413–422.  
[11] Y. Zhao, Z. Nasrullah, and Z. Li, "PyOD: A Python Toolbox for Scalable Outlier Detection," *Journal of Machine Learning Research*, vol. 20, no. 96, pp. 1–7, 2019.  
[12] P. Geurts, D. Ernst, and L. Wehenkel, "Extremely Randomized Trees," *Machine Learning*, vol. 63, no. 1, pp. 3–42, 2006.  
[13] R. Koenker and K. F. Hallock, "Quantile Regression," *Journal of Economic Perspectives*, vol. 15, no. 4, pp. 143–156, 2001.  
[14] A. Savitzky and M. J. E. Golay, "Smoothing and Differentiation of Data by Simplified Least Squares Procedures," *Analytical Chemistry*, vol. 36, no. 8, pp. 1627–1639, 1964.  
[15] R. E. Kalman, "A New Approach to Linear Filtering and Prediction Problems," *Transactions of the ASME—Journal of Basic Engineering*, vol. 82, Series D, pp. 35–45, 1960.
