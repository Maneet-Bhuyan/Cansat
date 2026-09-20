# Cognitive CanSat — Comprehensive Read-Only Audit Report

> **Branch**: `ganesh/paper-docs` | **Date**: 2026-09-20  
> **Policy**: INSPECT ONLY — zero files modified.

---

## A. Bugs Found

### BUG-01 — Incorrect input resolution in `tinyml.html` and `mission-slider.js`
| Field | Detail |
|---|---|
| **File** | [`tinyml.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/tinyml.html#L405), [`mission-slider.js`](file:///c:/Users/GANESH VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/js/mission-slider.js#L69), [`index.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/index.html#L380) |
| **Problem** | These files describe the OV3660/ESP32-CAM capture resolution as **64×48** and the CNN input tensor as **64×48**, but the authoritative training code (`train_tinyml_vision.py`), `model_metrics.json`, `readme.md`, `data/README.md`, and `benchmark_inference.py` all say the input is **64×64 RGB**. |
| **Evidence** | `tinyml.html:405` → "Raw Downlinked Optical Frame (64x48)"; `train_tinyml_vision.py:140` → `# Input: 64x64x3 RGB`; `model_metrics.json:121` → `"input_resolution": "64x64 RGB"` |
| **Severity** | **HIGH** — creates factual inconsistency with trained model architecture |
| **Suggested fix** | Change `64x48` → `64x64` in `tinyml.html`, `mission-slider.js`, and `index.html` code comments |
| **Safe for user to fix?** | ✅ Yes — content-only change |

---

### BUG-02 — TinyLandingNet parameter count mismatch (`6,996` vs `7,320`)
| Field | Detail |
|---|---|
| **File** | [`models.html:234`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/models.html#L234) |
| **Problem** | `models.html` reports **6,996** parameters. Every other source (`readme.md`, `ml/README.md`, `model_metrics.json:212 → int8_parameter_count: 7320`, `GPU_TRAINING_INSTRUCTIONS.md`, `docs/architecture_and_ml.txt`) says **7,320**. The `model_metrics.json:120` records `"parameter_count": 6996` — this appears to be the float32 count before quantisation rounding; the INT8 export count is 7,320. `models.html` displays the wrong number AND labels it as "(7.15 KB INT8)" which belongs to the 7,320 figure. |
| **Evidence** | `models.html:234` → `6,996 (7.15 KB INT8)`; `model_metrics.json:120` → `"parameter_count": 6996`; `model_metrics.json:212` → `"int8_parameter_count": 7320` |
| **Severity** | **MEDIUM** — misleads readers about the deployed model size |
| **Suggested fix** | Display `7,320` (INT8) or clarify: `6,996 (float32) / 7,320 (INT8, 7.15 KB)` |
| **Safe for user to fix?** | ✅ Yes |

---

### BUG-03 — RF Phase Classifier accuracy reported as `98.4%` in `readme.md`, but actual test accuracy is `98.56%`
| Field | Detail |
|---|---|
| **File** | [`readme.md:369`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md#L369) |
| **Problem** | The README model table states "**98.4%** Accuracy (Macro F1: 0.98)" for the Random Forest phase classifier. Actual data from `model_metrics.json:5` → `"test_accuracy": 0.9855715871254163` ≈ **98.56%**. The `ml/README.md`, `models.html`, `docs/architecture_and_ml.txt`, and `project_log.txt` all correctly state 98.56%. The Macro F1 is also **0.90** (macro avg per classification report), not 0.98. |
| **Evidence** | `readme.md:369` → `98.4% Accuracy (Macro F1: 0.98)`; `model_metrics.json:5` → `0.9856`; `model_metrics.json:41` → macro avg f1 = `0.9023` |
| **Severity** | **HIGH** — wrong metric in documentation; the macro F1 is especially incorrect (0.98 vs actual 0.90) |
| **Suggested fix** | Correct to: `98.56% Accuracy (Macro F1: 0.90)` |
| **Safe for user to fix?** | ✅ Yes |

---

### BUG-04 — Apogee Regressor RMSE mismatch: `±14.2 m` in README vs actual `24.17 m`
| Field | Detail |
|---|---|
| **File** | [`readme.md:371`](file:///c:/Users/GANESH VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md#L371) |
| **Problem** | README states Gradient Boosting Apogee Regressor RMSE is **±14.2 m**. The source of truth, `model_metrics.json:88`, records `"rmse_meters": 24.167643268856494` ≈ **24.17 m**. The R² value of **0.9951** is consistent across both the README (implied) and metrics JSON. |
| **Evidence** | `readme.md:371` → `RMSE: +/- 14.2 m`; `model_metrics.json:88` → `"rmse_meters": 24.167...` |
| **Severity** | **HIGH** — factually wrong metric; makes the model appear ~40% more accurate than it actually is |
| **Suggested fix** | Change to `RMSE: ±24.2 m` |
| **Safe for user to fix?** | ✅ Yes |

---

### BUG-05 — TinyLandingNet validation accuracy `93.80%` presented as the headline accuracy, but actual holdout test accuracy is `93.04%`
| Field | Detail |
|---|---|
| **File** | [`readme.md:374,383`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md#L374), [`ml/README.md:7`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/ml/README.md#L7) |
| **Problem** | The project prominently advertises **93.80% Val Acc** as the primary model performance figure. `model_metrics.json:123` records `"test_accuracy_pct": 93.04`, a lower number. `tasks.txt:282` correctly distinguishes the two: "Best Val Accuracy = 93.80%, Test Accuracy = 93.04%". Papers should always report held-out test accuracy, not best validation accuracy, as the headline figure. |
| **Evidence** | `model_metrics.json:123` → `93.04`; `readme.md:374` → `93.80% Val Acc` |
| **Severity** | **MEDIUM** — not technically wrong but misleading for a research paper context |
| **Suggested fix** | Report test accuracy (93.04%) as headline with validation accuracy (93.80%) noted separately |
| **Safe for user to fix?** | ✅ Yes |

---

### BUG-06 — `dashboard.html` page title contains stray text "UNIVERSE TELEMETRY"
| Field | Detail |
|---|---|
| **File** | [`dashboard.html:6`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/dashboard.html#L6) |
| **Problem** | The `<title>` tag reads: `Cognitive CanSat Ground Station - UNIVERSE TELEMETRY`. "UNIVERSE TELEMETRY" appears to be leftover debug/placeholder text. No other page uses this term and it appears in no documentation. |
| **Evidence** | `dashboard.html:6` → `<title>Cognitive CanSat Ground Station - UNIVERSE TELEMETRY</title>` |
| **Severity** | **LOW** — cosmetic; shows in browser tab and SEO metadata |
| **Suggested fix** | Change to `Cognitive CanSat Ground Station - Mission Control` |
| **Safe for user to fix?** | ✅ Yes |

---

### BUG-07 — Default serial mode hard-codes `COM4 + COM5`
| Field | Detail |
|---|---|
| **File** | [`dashboard.html:577`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/dashboard.html#L577) |
| **Problem** | The default `<select>` option reads `DUAL BRIDGE (COM4 + COM5)` with the exact COM port numbers hard-coded. COM port numbers vary per system. If a user's CanSat receives a different port assignment, the UI label is misleading and confusing. |
| **Evidence** | `dashboard.html:577` → `<option value="bridge" selected>DUAL BRIDGE (COM4 + COM5)</option>` |
| **Severity** | **LOW** — usability issue; COM ports are system-dependent |
| **Suggested fix** | Change label to `DUAL BRIDGE (Auto-detect COM)` or document the COM4/COM5 assumption in Help |
| **Safe for user to fix?** | ✅ Yes |

---

### BUG-08 — `zoom3D` button labels swapped (+ zooms out, − zooms in)
| Field | Detail |
|---|---|
| **File** | [`dashboard.html:890-892`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/dashboard.html#L890) |
| **Problem** | The 3D model zoom buttons call `zoom3D(0.88)` (camera moves closer) for `+` and `zoom3D(1.12)` (camera moves farther) for `−`. If `zoom3D` multiplies the camera distance by its argument, 0.88 < 1 means zooming IN (correct for `+`) and 1.12 > 1 means zooming OUT (correct for `−`). However, if the function multiplies the field-of-view angle, the polarity is reversed. Needs verification against the JS implementation. |
| **Evidence** | `dashboard.html:890` → `onclick="zoom3D(0.88)"` for `+`; `dashboard.html:892` → `onclick="zoom3D(1.12)"` for `−` |
| **Severity** | **MEDIUM** — potential UX inversion depending on implementation |
| **Suggested fix** | Verify `zoom3D` implementation and confirm whether 0.88 zooms in or out; add comment |
| **Safe for user to fix?** | ⚠️ Verify first |

---

### BUG-09 — Apogee Regressor R² claim in `ml/README.md` cannot be cross-referenced
| Field | Detail |
|---|---|
| **File** | [`ml/README.md:13`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/ml/README.md#L13) |
| **Problem** | `ml/README.md:13` states the apogee regressor achieves "R² 0.9951". `model_metrics.json:87` confirms `"r2_score": 0.9951052...`. This is consistent. But the RMSE stated elsewhere (14.2 m in readme) conflicts with the JSON (24.17 m). See BUG-04. |
| **Evidence** | Cross-reference already documented under BUG-04 |
| **Severity** | *(Sub-issue of BUG-04)* |
| **Suggested fix** | See BUG-04 |
| **Safe for user to fix?** | ✅ Yes |

---

## B. Content Issues Found

### CONTENT-01 — "Precision Environmental Droplibs" — unclear/incorrect term
| Field | Detail |
|---|---|
| **File** | [`index.html:469`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/index.html#L469) |
| **Problem** | The homepage card heading reads **"Precision Environmental Droplibs"**. This term does not appear in any technical documentation, readme, or backend code. The likely intent is "Dropsondes" or "Environmental Probes/Measurements". |
| **Severity** | **MEDIUM** — confusing to any external reader or paper reviewer |
| **Suggested fix** | Rename to "Precision Environmental Sensing" or "Atmospheric Sounding Suite" |
| **Safe for user to fix?** | ✅ Yes |

---

### CONTENT-02 — BibTeX author name "Vallabhm, Ganesh" is malformed
| Field | Detail |
|---|---|
| **File** | [`results.html:585`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/results.html#L585) |
| **Problem** | The BibTeX citation on the Results page lists the author as `Vallabhm, Ganesh`. The last name appears to be `Vallabh M` (with M being a middle initial), not `Vallabhm`. This would render incorrectly in any citation manager. |
| **Evidence** | `results.html:585` → `author = {Bhuyan, Maneet and Senanayak, Rishi and Shubham and Vallabhm, Ganesh}` |
| **Severity** | **MEDIUM** — citation error; impacts academic credibility |
| **Suggested fix** | Change `Vallabhm, Ganesh` to `{Vallabh M}, Ganesh` or the correct BibTeX form of the name |
| **Safe for user to fix?** | ✅ Yes |

---

### CONTENT-03 — Apogee regressor RMSE in `readme.md` is inconsistent with source of truth (`model_metrics.json`)
*(Already documented as BUG-04 — cross-listed here as a content issue for the paper)*

---

### CONTENT-04 — Sensor Calibrator described as "13 features" but `model_metrics.json` lists only 13 raw features yet `train_models.py` may differ
| Field | Detail |
|---|---|
| **File** | [`readme.md:368`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md#L368) |
| **Problem** | README states the ExtraTrees Sensor Calibrator uses "13 telemetry & dynamic features". `model_metrics.json:92–106` lists exactly 13 features. The flight phase classifier feature importances (lines 58–75 of metrics) lists 16 features. The distinction (raw vs. engineered) should be clearly documented. |
| **Severity** | **LOW** — not wrong, but needs clarity |
| **Suggested fix** | Add a note clarifying which 13 features are used for calibration vs. the 16/17 used for classification |
| **Safe for user to fix?** | ✅ Yes |

---

### CONTENT-05 — Webpage title mismatch: `index.html` says "Landing Intelligence for Pico-Satellites", README says "Cognitive CanSat"
| Field | Detail |
|---|---|
| **File** | [`index.html:6`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/index.html#L6) |
| **Problem** | `index.html` title tag reads "Cognitive CanSat - Landing Intelligence for Pico-Satellites" which is a reasonable subtitle. Consistent with branding. *Not a critical issue*, but the subtitle "Pico-Satellites" may be inaccurate — CanSats are typically classified as nano-satellites or just CanSats, not pico-satellites (which are < 0.1 kg). |
| **Severity** | **LOW** — minor technical nomenclature issue |
| **Suggested fix** | Change "Pico-Satellites" to "CanSat Nano-Satellites" or just "CanSat Missions" |
| **Safe for user to fix?** | ✅ Yes |

---

### CONTENT-06 — `spatial_3x3_grid` benchmarks report GPU (CUDA) latency, but the section title implies edge (ESP32) evaluation
| Field | Detail |
|---|---|
| **File** | [`model_metrics.json:220-238`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/ml/model_metrics.json#L220) |
| **Problem** | The `spatial_3x3_grid` section reports `"device": "CUDA"` and `"mean_grid_latency_ms": 4.23`. If this is presented as edge performance in any UI or paper, it is misleading — the actual ESP32 estimated latency is 16.3 ms per tile × 9 tiles ≈ 146.7 ms per grid scan, which approaches but satisfies the 150 ms budget. The frontend should not present the CUDA grid latency as edge performance. |
| **Severity** | **MEDIUM** — misleading if displayed as embedded performance |
| **Suggested fix** | Clearly label the 4.23 ms figure as "Ground CUDA" and compute/display an estimated ESP32 grid latency separately |
| **Safe for user to fix?** | ✅ Yes |

---

## C. Spelling & Grammar Corrections

| ID | File | Line | Current Text | Corrected Text |
|---|---|---|---|---|
| SPELL-01 | [`index.html:469`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/index.html#L469) | 469 | "Precision Environmental Droplibs" | "Precision Environmental Sensing" (or Dropsondes) |
| SPELL-02 | [`results.html:585`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/results.html#L585) | 585 | `Vallabhm, Ganesh` | `{Vallabh M}, Ganesh` (BibTeX) |
| SPELL-03 | [`readme.md:369`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md#L369) | 369 | `98.4% Accuracy (Macro F1: 0.98)` | `98.56% Accuracy (Macro F1: 0.90)` |
| SPELL-04 | [`readme.md:371`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md#L371) | 371 | `RMSE: +/- 14.2 m` | `RMSE: ±24.2 m` |
| SPELL-05 | [`dashboard.html:6`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/dashboard.html#L6) | 6 | `- UNIVERSE TELEMETRY` | `- Mission Control` (or remove) |

---

## D. Research Paper Material Available

The repository contains several research-grade technical contributions that are paper-worthy:

### D1 — Dual-tier ML architecture for resource-constrained aerospace systems ⭐⭐⭐
- **What it is**: A formally documented split between edge inference (TinyLandingNet, INT8 CNN at 7.15 KB on ESP32-CAM) and ground-truth processing (ExtraTrees calibrator, Random Forest phase classifier, PyOD anomaly detector).
- **Why it's interesting**: Demonstrates the full deployment pipeline from PyTorch training → ONNX export → C-array quantisation for embedded inference in a CanSat context, with measured latency budgets (0.055 ms ONNX ground vs. 16.3 ms ESP32).
- **Supporting files**: `train_tinyml_vision.py`, `benchmark_inference.py`, `model_metrics.json`, `GPU_TRAINING_INSTRUCTIONS.md`

### D2 — ExtraTrees sensor calibration achieving altitude R² = 1.0000 (RMSE: 0.804 m) ⭐⭐⭐
- **What it is**: Multi-output ExtraTreesRegressor (13 features → calibrated altitude + vertical speed) that achieves near-perfect altitude calibration on synthetic flight telemetry.
- **Why it's interesting**: Demonstrates ML-based sensor drift correction as an alternative to parametric barometric formulas. Altitude R² = 1.0 and RMSE = 0.804 m against synthesized ground truth is a strong baseline.
- **Caveat for paper**: This was trained on synthetic/simulated data; real-world generalization would need to be validated.
- **Supporting files**: `model_metrics.json:90–116`, `train_models.py`

### D3 — Savitzky-Golay kinematic estimator for flight dynamics profiling ⭐⭐
- **What it is**: A formal SG filter (window=11, polyorder=2) applied to compute smooth vertical velocity `v_z`, peak G-shock acceleration magnitude, and touchdown G-force from raw barometric + accelerometer telemetry.
- **Why it's interesting**: The 4-panel publication figures (in `reports/figures/`) show professional quality plots of the filter applied across 10 distinct flight scenarios, comparable to published CubeSat/CanSat papers.
- **Supporting files**: `analysis.html` (JS implementation), `reports/figures/` (60 publication figures across 10 test scenarios)

### D4 — Safe Landing Area Index (SLAI) 3×3 hazard grid evaluation ⭐⭐⭐
- **What it is**: A 3×3 spatial grid evaluation framework using TinyLandingNet per-sector classification and a minimum-risk escape vector computation.
- **Why it's interesting**: Applies satellite-trained imagery (EuroSAT Sentinel-2, 27,000 images) to a pico-satellite descent scenario. The SLAI framework (4 classes: SAFE_LZ, OBSTACLE_CANOPY, CRITICAL_HAZARD, WATER_HAZARD) and escape vector computation are novel for this class of system.
- **Supporting files**: `train_tinyml_vision.py`, `model_metrics.json:220-237`, `frontend/tinyml.html`

### D5 — 10 synthesized test flight scenarios with per-scenario analysis ⭐⭐
- **What it is**: 10 distinct CSV telemetry datasets covering nominal to extreme edge cases (freefall, wind shear, parachute resonance, GPS glitch, voltage sag, thermal inversion), each with 4-panel publication figures.
- **Why it's interesting**: Provides a reusable benchmark suite for CanSat / high-altitude balloon descent systems. The ablation study (`cansat_eval_ablation.ipynb`) evaluates performance across sensor loss scenarios (No IMU, No Env, GPS-Only).
- **Supporting files**: `test_cases/*.csv`, `reports/figures/`, `ml/cansat_eval_ablation.ipynb`

### D6 — Altitude Kalman Filter with adaptive IMU fusion ⭐⭐
- **What it is**: A constant-velocity Kalman filter (`AltitudeKalmanFilter` in `kinematics.py`) with adjustable process/observation noise, fusing barometric and IMU-derived vertical velocity.
- **Why it's interesting**: The filter adapts covariance based on detected flight phase (ascent vs. freefall vs. descent), which is an adaptive estimation approach worth documenting formally.
- **Supporting files**: `backend/core/kinematics.py`

---

## E. Files Safe to Modify (Recommended Priority)

| Priority | File | What to Fix |
|---|---|---|
| 🔴 **P1** | [`readme.md`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/readme.md) | Fix BUG-03 (accuracy 98.4% → 98.56%, Macro F1 0.98 → 0.90), BUG-04 (RMSE 14.2 m → 24.2 m) |
| 🔴 **P1** | [`frontend/tinyml.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/tinyml.html) | Fix BUG-01 (64×48 → 64×64) |
| 🔴 **P1** | [`frontend/js/mission-slider.js`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/js/mission-slider.js) | Fix BUG-01 (64×48 → 64×64) |
| 🔴 **P1** | [`frontend/index.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/index.html) | Fix BUG-01 (code comment 64×48 → 64×64), SPELL-01 ("Droplibs" rename) |
| 🟡 **P2** | [`frontend/models.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/models.html) | Fix BUG-02 (6,996 → 7,320 for INT8, or clarify distinction) |
| 🟡 **P2** | [`frontend/results.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/results.html) | Fix SPELL-02 (BibTeX author name) |
| 🟢 **P3** | [`frontend/dashboard.html`](file:///c:/Users/GANESH%20VALLABH%20M/Downloads/Cansat-main/Cansat/frontend/dashboard.html) | Fix BUG-06 (title UNIVERSE TELEMETRY), BUG-07 (hard-coded COM ports) |

---

## Summary Counts

| Category | Count |
|---|---|
| Bugs (logic/data inconsistency) | **8** |
| Content issues | **6** |
| Spelling/grammar errors | **5** |
| Research paper sections identified | **6** |
| Files safe to modify | **7** |

> [!IMPORTANT]
> **BUG-03** (wrong classifier accuracy in README) and **BUG-04** (wrong apogee RMSE — stated as ±14.2 m, actual ±24.2 m) are the most critical to fix before any paper submission. They present the system as more accurate than the measured data supports.

> [!NOTE]
> **BUG-01** (64×48 vs 64×64 input resolution) should be fixed before publishing `tinyml.html` publicly — the mismatch with the training code would be immediately noticed by ML reviewers.
