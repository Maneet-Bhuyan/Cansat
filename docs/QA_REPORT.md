# CanSat Mission Control — QA Report

**Project:** Cognitive CanSat Ground Station  
**Branch:** `ganesh/paper-docs`  
**Audit Type:** Static code and documentation review (read-only phase) + controlled contribution phase  
**Date:** 2026-09-20  
**Auditor:** Antigravity AI Code Review  

---

## Testing Scope

This QA report covers the following areas of the Cognitive CanSat repository:

- Frontend HTML pages: `index.html`, `dashboard.html`, `tinyml.html`, `models.html`, `analysis.html`, `results.html`
- Backend: `backend/app.py`, `backend/core/kinematics.py`, `backend/core/atmospheric.py`
- ML pipeline: `ml/model_metrics.json`, `ml/train_tinyml_vision.py`, `ml/train_models.py`, `ml/benchmark_inference.py`, `ml/README.md`
- Documentation: `readme.md`, `docs/project_log.txt`, `docs/architecture_and_ml.txt`, `docs/GPU_TRAINING_INSTRUCTIONS.md`
- Test data: `test_cases/*.csv` (10 flight profiles)
- Test suite: `tests/selftest.js`, `tests/test_backend_core.py`

---

## Environment

- **Audit method:** Static analysis (no live server execution; application was not run due to dependency installation requirement)
- **Repository state:** Clean working tree on `ganesh/paper-docs` branch prior to any changes (`git status: nothing to commit`)
- **OS:** Windows 11 (auditor machine)
- **Tools used:** ripgrep (file search), Python 3 (byte-level inspection), direct file read

---

## Pages Tested (Static Inspection)

| Page | File | Method |
|---|---|---|
| Overview & Architecture | `frontend/index.html` | Static HTML + JS read |
| TinyML Deep Dive | `frontend/tinyml.html` | Static HTML read |
| Mission Control | `frontend/dashboard.html` | Static HTML read |
| ML Models | `frontend/models.html` | Static HTML read |
| Flight Analysis | `frontend/analysis.html` | Static HTML read |
| Research & Results | `frontend/results.html` | Static HTML read |

---

## Functional Tests

| Test | Method | Result |
|---|---|---|
| Navigation links (all 6 pages) | Inspected `href` attributes | ✅ All links point to sibling HTML files in same directory |
| Download CSV button | Inspected `onclick="downloadCSV()"` | ✅ Function defined in inline JS |
| Connect/Disconnect serial | Inspected `toggleConnect()` | ✅ Defined; uses Web Serial API |
| Demo mode toggle | Inspected `toggleDemo()` | ✅ Defined; starts synthetic data injection |
| Replay suite | Inspected `toggleReplayDrawer()` | ✅ Drawer toggle works; scrubber defined |
| 3D model controls | Inspected `zoom3D()`, `tareAttitude()` | ✅ Defined; direction convention needs verification (see QA-002) |
| Google Maps recovery | Inspected `openGoogleMapsRecovery()` | ✅ Constructs maps URL from last GPS fix |
| PFR Report modal | Inspected `openModal('pfrModal')` | ✅ Modal defined in DOM |
| Help modal | Inspected `openModal('helpModal')` | ✅ Modal defined in DOM |
| AI modal | Inspected `openModal('aiModal')` | ✅ Modal defined in DOM |
| Phase classifier (backend) | Read `tests/test_backend_core.py` | ✅ Unit tests present for kinematics and atmospheric engines |

---

## UI/UX Findings

### QA-001 — Default serial connection dropdown labels specific COM ports

- **Severity:** Low
- **Page/File:** `frontend/dashboard.html` line 577
- **Feature:** Serial connection mode selector
- **Steps to reproduce:** Open `dashboard.html` in a browser. Observe the connection mode dropdown default option.
- **Expected:** A hardware-agnostic label for the default dual-bridge mode.
- **Actual:** Label reads `DUAL BRIDGE (COM4 + COM5)` — COM port numbers are hard-coded and vary per system.
- **Evidence:** `dashboard.html:577` → `<option value="bridge" selected>DUAL BRIDGE (COM4 + COM5)</option>`; `docs/project_log.txt` shows this is an intentional development default.
- **Recommended fix:** Update label to `DUAL BRIDGE (Python COM Bridge)` to be informative without implying specific port numbers.
- **Status:** Open — deliberate development default; functional impact is cosmetic label confusion only

---

### QA-002 — 3D model zoom button polarity requires live verification

- **Severity:** Medium (requires live testing to confirm)
- **Page/File:** `frontend/dashboard.html` lines 890–892
- **Feature:** 3D CanSat orientation tile zoom buttons
- **Steps to reproduce:** Launch dashboard with a live or demo session. Click the `+` zoom button, then the `−` button.
- **Expected:** `+` zooms in (camera closer), `−` zooms out (camera farther).
- **Actual (code):** `+` calls `zoom3D(0.88)`, `−` calls `zoom3D(1.12)`. Direction appears correct if `zoom3D` multiplies camera distance, but needs live verification.
- **Evidence:** `dashboard.html:890-892`
- **Recommended fix:** Add a code comment confirming the direction convention; verify visually.
- **Status:** Unverified — could not run live session during static audit

---

## Console/Network Findings

> **Note:** A live browser session was not executed during this audit. The following are statically identified potential conditions.

### QA-003 — ML backend API calls will silently fail if Python server is not running

- **Severity:** Medium (expected behavior, but no clear user-facing error state)
- **Page/File:** `frontend/dashboard.html` (fetch + WebSocket calls)
- **Feature:** Python ML Server connection badge (`#ml-server-badge`)
- **Steps to reproduce:** Open `dashboard.html` without starting the FastAPI backend.
- **Expected:** Clear "Backend offline" warning; graceful degradation.
- **Actual (code):** Badge starts in STANDBY state; API calls will return `net::ERR_CONNECTION_REFUSED` with no error modal.
- **Evidence:** `dashboard.html:692-695` — badge defaults to `bg-zinc-500 (STANDBY)`.
- **Recommended fix:** Add a `fetch` error handler updating the badge to a red "OFFLINE" state.
- **Status:** Open — known limitation; README requires manual backend start

---

## Content/Documentation Findings

### QA-004 — RF Classifier accuracy and Macro F1 wrong in `readme.md`

- **Severity:** High
- **Page/File:** `readme.md` line 369
- **Feature:** ML model performance table
- **Steps to reproduce:** Compare `readme.md:369` against `ml/model_metrics.json:5,41`.
- **Expected:** `98.56% Accuracy (Weighted F1: 0.985; Macro F1: 0.902)`
- **Actual:** `98.4% Accuracy (Macro F1: 0.98)` — accuracy is rounded down; F1 cited (0.98) is the weighted average, not macro (which is 0.90)
- **Evidence:** `model_metrics.json:5` → `0.9855715871254163`; `model_metrics.json:41` → macro avg f1 = `0.9023`
- **Recommended fix:** Correct to `98.56% Accuracy (Weighted F1: 0.985; Macro F1: 0.902)`
- **Status:** ✅ **FIXED** (readme.md line 369)

---

### QA-005 — Apogee Regressor RMSE stated as ±14.2 m, actual is ±24.2 m

- **Severity:** High
- **Page/File:** `readme.md` line 371
- **Feature:** ML model performance table (Gradient Boosting Apogee Regressor)
- **Steps to reproduce:** Compare `readme.md:371` against `ml/model_metrics.json:88`.
- **Expected:** `R²: 0.9951, RMSE: ±24.2 m`
- **Actual:** `RMSE: +/- 14.2 m` — understates error by ~10 m (~40%)
- **Evidence:** `model_metrics.json:88` → `"rmse_meters": 24.167643268856494`
- **Recommended fix:** Update to `R²: 0.9951, RMSE: ±24.2 m`
- **Status:** ✅ **FIXED** (readme.md line 371)

---

### QA-006 — TinyLandingNet CNN input resolution inconsistency (64×48 vs 64×64)

- **Severity:** High
- **Page/File:** `frontend/index.html` lines 380–383, `frontend/tinyml.html` line 405, `frontend/js/mission-slider.js` line 69
- **Feature:** TinyML pipeline pseudocode and documentation
- **Steps to reproduce:** Compare `train_tinyml_vision.py:140` and `model_metrics.json:121` against the above frontend files.
- **Expected:** All references to model input resolution say 64×64.
- **Actual:** Pseudocode passed `(64, 48)` to inference; frame label said `(64x48)`; camera descriptor said "64x48 frames"
- **Evidence:** `train_tinyml_vision.py:140` → `# Input: 64x64x3 RGB`; `model_metrics.json:121` → `"input_resolution": "64x64 RGB"`
- **Recommended fix:** Update all pseudocode and labels to reflect 64×64 model input (camera captures at QVGA, tiles resized to 64×64)
- **Status:** ✅ **FIXED** (index.html ×2 occurrences, tinyml.html, mission-slider.js)

---

### QA-007 — TinyLandingNet parameter count label conflates float32 and INT8 counts

- **Severity:** Medium
- **Page/File:** `frontend/models.html` line 234
- **Feature:** TinyLandingNet model specification card
- **Steps to reproduce:** Compare `models.html:234` against `model_metrics.json:120` and `model_metrics.json:212`.
- **Expected:** Clear distinction between float32 (6,996) and INT8 (7,320, 7.15 KB).
- **Actual:** `6,996 (7.15 KB INT8)` — the 7.15 KB figure belongs to the 7,320-parameter INT8 model
- **Evidence:** `model_metrics.json:120` → `"parameter_count": 6996`; `model_metrics.json:212` → `"int8_parameter_count": 7320`
- **Recommended fix:** Display `6,996 (float32) / 7,320 (INT8, 7.15 KB Flash)`
- **Status:** ✅ **FIXED** (models.html line 234)

---

### QA-008 — `ml/README.md` presents validation accuracy as headline instead of held-out test accuracy

- **Severity:** Medium
- **Page/File:** `ml/README.md` line 7
- **Feature:** TinyLandingNet description
- **Steps to reproduce:** Read `ml/README.md:7` vs `model_metrics.json:123`.
- **Expected:** "93.04% holdout test accuracy (best validation accuracy: 93.80%)"
- **Actual:** "Achieved 93.80% validation accuracy" as the lead metric with no test accuracy stated
- **Evidence:** `model_metrics.json:123` → `"test_accuracy_pct": 93.04`; `tasks.txt:282` → distinguishes the two correctly
- **Recommended fix:** Lead with holdout test accuracy (93.04%) and note validation (93.80%) separately
- **Status:** ✅ **FIXED** (ml/README.md line 7)

---

### QA-009 — BibTeX author name `Vallabhm, Ganesh` is malformed

- **Severity:** Medium
- **Page/File:** `frontend/results.html` line 585
- **Feature:** BibTeX citation block
- **Steps to reproduce:** Open `results.html`; inspect the BibTeX author field; paste into a BibTeX tool.
- **Expected:** `Vallabh M, Ganesh`
- **Actual:** `Vallabhm, Ganesh` — missing space between `Vallabh` and `M`
- **Evidence:** `results.html:585`; `tasks.txt:16` → `@ganeshvallabhm` (GitHub handle confirms name structure)
- **Recommended fix:** Change to `Vallabh M, Ganesh`
- **Status:** ✅ **FIXED** (results.html line 585)

---

### QA-010 — "Precision Environmental Droplibs" — not a recognized technical term

- **Severity:** Medium
- **Page/File:** `frontend/index.html` line 469
- **Feature:** Applications section, card 3
- **Steps to reproduce:** Search entire repository for "Droplibs". Read the card body text.
- **Expected:** Recognized aeronautical term — "Dropsondes" (sensor packages deployed from aircraft for atmospheric sounding)
- **Actual:** "Droplibs" — appears only in `index.html`, absent from all technical documentation
- **Evidence:** grep result: 2 matches in `index.html` only; no match in README, docs, firmware, or backend
- **Recommended fix:** Change to "Precision Environmental Dropsondes"
- **Status:** ✅ **FIXED** (index.html lines 466, 469)

---

### QA-011 — Dashboard `<title>` "UNIVERSE TELEMETRY" — confirmed intentional

- **Severity:** None (previously misclassified)
- **Page/File:** `frontend/dashboard.html` line 6
- **Feature:** Page title metadata
- **Steps to reproduce:** Search codebase for "UNIVERSE TELEMETRY".
- **Expected:** Intentional project subtitle → retain unchanged.
- **Actual:** Confirmed intentional — documented in `docs/project_log.txt:14` and **asserted by `tests/selftest.js:102`**. Changing it would break the automated test suite.
- **Evidence:** `docs/project_log.txt:14` → `Title: Ground Station - UNIVERSE TELEMETRY`; `tests/selftest.js:102` → assertion for exact string
- **Recommended fix:** No change. Previous classification as bug was incorrect.
- **Status:** ⛔ **NOT FIXED** — intentional; protected by test assertion

---

### QA-012 — COM4 + COM5 labels in serial dropdown

- **Severity:** Low
- **Page/File:** `frontend/dashboard.html` line 577
- **Feature:** Connection mode dropdown
- **Steps to reproduce:** Open dashboard on a machine with different COM port assignments.
- **Actual:** Label shows specific port numbers `COM4 + COM5`; these are system-dependent
- **Evidence:** Development machine default in `docs/project_log.txt`
- **Recommended fix:** Label-only change to `DUAL BRIDGE (Python COM Bridge)`
- **Status:** Open — cosmetic; functional routing unaffected

---

## Reproduction Steps

All findings were reproduced by:
1. Static file read using file inspection and ripgrep search
2. Cross-referencing values between source files (training code, metrics JSON, documentation, HTML)
3. No live browser session was possible without installing Python dependencies

---

## Severity Classification

| Severity | Definition | Count |
|---|---|---|
| **High** | Factually incorrect metric in documentation (impacts paper credibility) | 3 |
| **Medium** | Inconsistency between files that could mislead readers or reviewers | 5 |
| **Low** | Cosmetic or convenience issue; no functional impact | 2 |
| **None** | Previously classified issue; found to be intentional after investigation | 1 |

---

## Recommended Fixes (Summary)

| ID | Status | Priority |
|---|---|---|
| QA-004 | ✅ Fixed | P1 |
| QA-005 | ✅ Fixed | P1 |
| QA-006 | ✅ Fixed | P1 |
| QA-007 | ✅ Fixed | P2 |
| QA-008 | ✅ Fixed | P2 |
| QA-009 | ✅ Fixed | P2 |
| QA-010 | ✅ Fixed | P2 |
| QA-001 | Open | P3 |
| QA-002 | Open (requires live test) | P3 |
| QA-003 | Open (known limitation) | P3 |
| QA-011 | Closed (intentional) | N/A |
| QA-012 | Open (cosmetic) | P3 |

---

## Limitations

1. **No live session tested.** The application requires `pip install -r requirements.txt` and `uvicorn backend.app:app`. WebSocket behavior, Chart.js rendering, Leaflet map, and Three.js orientation were not validated in a running browser.
2. **Synthetic test data only.** All 10 test case CSV files are synthetically generated. No real hardware flight data was available.
3. **Firmware not compiled.** ESP32-CAM firmware was inspected but not compiled or flashed. Camera framesize and model inference pipeline at runtime was not verified.
4. **No external dataset access.** `data/EuroSAT_RGB.zip` is tracked via Git LFS and was not downloaded. Training reproducibility was not verified.
5. **No cross-browser testing.** Web Serial API requires Chrome/Edge; other browsers were not tested.
