# Telemetry Data Quality and Flight Reliability Analyzer

Module: backend/core/telemetry_analyzer.py
API: backend/app.py - /api/analysis/quality/{scenario_name}, /api/analysis/quality/analyze-csv
UI: frontend/analysis.html - Quality Inspector panel
Tests: tests/test_telemetry_analyzer.py

---

## Overview

The Telemetry Quality Analyzer performs deterministic, objective quality assessment on CanSat flight
telemetry CSVs before those datasets are used for machine learning inference or post-flight
reconstruction. It reports only measurable facts: raw packet counts, timing statistics, sensor
availability percentages, and detected anomaly event windows. It does not assign any subjective
quality score.

**Use cases:**
- Pre-analysis gate: Verify data integrity before invoking flight phase classifier, apogee regressor, or Savitzky-Golay velocity reconstruction.
- Ground station QA: Quick health check of incoming telemetry during or after a flight mission.
- Research reproducibility: Characterize the dataset used in ML experiments for inclusion in research papers.
- Ad-hoc inspection: Drag-and-drop any CSV to check compatibility and completeness.

---

## Input Format

- Format: RFC 4180 (comma-separated values, UTF-8)
- Header row: Required, must include all 13 primary field names (order-independent)
- Timestamp column: timestamp -- ISO 8601 date-time strings or Unix epoch floats
- Nominal sampling rate: 1.25 Hz (one packet every 0.800 seconds)

### Required Columns

| Column | Type | Unit | Description |
|---|---|---|---|
| timestamp | ISO 8601 / float | -- | Packet timestamp |
| temp | float | degC | Ambient temperature |
| pressure | float | hPa | Barometric pressure |
| altitude | float | m | GNSS/barometric altitude |
| gx, gy, gz | float | deg/s | Gyroscope axes |
| ax, ay, az | float | G | Accelerometer axes |
| lat | float | deg | GNSS latitude |
| lon | float | deg | GNSS longitude |
| humidity | float | % | Relative humidity |
| batteryVoltage | float | V | LiPo cell voltage |

---

## Configuration Constants

| Constant | Default | Description |
|---|---|---|
| NOMINAL_INTERVAL_S | 0.80 | Expected sample interval in seconds |
| GAP_THRESHOLD_S | 2.00 | Minimum interval classified as a timestamp gap |
| IRREGULAR_TOLERANCE | 0.20 | Fraction of median interval for irregular classification |
| GPS_ZERO_TOLERANCE | 1e-5 | Degree tolerance for GNSS zero-coordinate detection |
| VOLTAGE_SAG_THRESHOLD | 3.40 | LiPo voltage (V) below which sag is detected |
| MIN_DROPOUT_RUN | 2 | Minimum consecutive packets to constitute a dropout event |

---

## API Reference

### GET /api/analysis/quality/{scenario_name}

Analyzes a named scenario from the test_cases/ directory.

Path parameter: scenario_name -- filename without .csv extension.

Response: 200 OK -- JSON object matching the TelemetryQualityReport schema.

Error codes: 404 (file not found), 422 (parse failure), 500 (unexpected error).

### POST /api/analysis/quality/analyze-csv

Analyzes an uploaded CSV file. Request body: multipart/form-data with field "file".

Response: 200 OK -- JSON object matching the TelemetryQualityReport schema.

---

## Output Schema

The response JSON contains:

### Packet Integrity

| Field | Description |
|---|---|
| total_rows | Total CSV rows excluding header |
| valid_packets | Rows with all primary fields numeric and finite |
| corrupted_rows | Rows with non-numeric or infinite values |
| duplicate_packets | Exact duplicate rows or repeated timestamps |
| estimated_missing_packets | Estimated lost packets inferred from timestamp gaps |
| packet_completeness_pct | valid / (valid + corrupted + missing) x 100 |

### Temporal Integrity

| Field | Description |
|---|---|
| flight_duration_seconds | t_last - t_first in seconds |
| mean_interval_seconds | Mean of successive timestamp differences |
| median_interval_seconds | Median of successive timestamp differences |
| min_interval_seconds | Minimum observed interval |
| max_interval_seconds | Maximum observed interval |
| interval_jitter_seconds | Standard deviation of timestamp intervals |
| irregular_interval_count | Intervals deviating more than 20% from median |
| timestamp_gaps | List of gap events with index, times, gap_seconds, estimated_missing |

### Sensor Completeness

Per-field objects under sensor_completeness:

| Field | Description |
|---|---|
| available | Count of non-null, finite values |
| missing | Count of null or non-parsable values |
| availability_pct | available / total_rows x 100 |
| min | Minimum observed value |
| max | Maximum observed value |
| out_of_range | Values outside hardware datasheet operating envelope |

### Anomaly Events

**gnss_dropout_events** -- each entry:
  start_index, end_index, start_time, end_time, duration_seconds, packet_count

Detection rule: Consecutive packets with (lat, lon) within 1e-5 degrees of (0.0, 0.0),
indicating u-blox NEO-6M no-fix output. Minimum run length: 2 packets.

**voltage_sag_events** -- each entry:
  start_index, end_index, start_time, end_time, duration_seconds, packet_count, min_voltage

Detection rule: Consecutive packets with batteryVoltage < 3.40 V. Minimum run length: 2 packets.

---

## Empirical Benchmark Results (All 10 Synthetic Flight Scenarios)

| Scenario | Packets | Completeness | Mean dt (s) | Jitter (s) | Gaps | Dropouts |
|---|---|---|---|---|---|---|
| 01 Nominal Sounding | 449 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 02 High Altitude Burst | 528 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 03 Severe Wind Shear | 375 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 04 Apogee Shock/Tumble | 350 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 05 Parachute Resonance | 325 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 06 Delayed Chute Deploy | 325 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 07 Thermal Inversion | 400 | 100.0% | 0.800 | ~0 | 0 | 0 |
| 08 Sensor Glitch/GPS* | 325 | 100.0% | 0.800 | ~0 | 0 | 1 |
| 09 Low Battery Sag** | 300 | 100.0% | 0.800 | ~0 | 0 | 3 |
| 10 Ground Pad Static | 225 | 100.0% | 0.800 | ~0 | 0 | 0 |

* Scenario 08: 1 GNSS dropout event detected, 31 packets (24.0 seconds), T+100.8s to T+124.8s.
** Scenario 09: 3 battery sag events detected; minimum voltage 3.254 V, longest sag 49.6 seconds.

---

## Unit Tests

tests/test_telemetry_analyzer.py contains 11 deterministic test cases:

| Test | Description |
|---|---|
| test_perfect_data | No anomalies in clean synthetic data |
| test_corrupted_rows | Corrupt tokens correctly counted |
| test_missing_packets_estimated | Artificial gap produces correct missing-packet estimate |
| test_gnss_dropout_detected | Zero-lat/lon run produces correct event window |
| test_gnss_dropout_not_triggered_on_real_coords | No false positives on legitimate coordinates |
| test_voltage_sag_detected | Below-threshold run produces correct sag event |
| test_voltage_sag_single_packet_ignored | Single low-voltage packet: no event (min run = 2) |
| test_sensor_completeness_nan | NaN values reduce availability percentage |
| test_duplicate_detection | Duplicate rows correctly counted |
| test_out_of_range_detection | Values outside datasheet envelope flagged |
| test_empty_dataframe | Empty input handled gracefully without exceptions |

Run with:

  python -m pytest tests/test_telemetry_analyzer.py -v

Expected: 11 passed in under 1 second.

---

## Design Decisions

**No quality score.** The analyzer does not compute a composite score or flight health index.
Such scores require arbitrary weighting of incommensurable metrics (packet loss vs voltage sag
vs GPS dropout) and produce misleading results across different mission profiles.

**Stateless design.** The analyzer holds no per-request state, making it safe for concurrent
FastAPI handler execution without locking.

**GNSS zero-coordinate heuristic.** Detects (0.0, 0.0) lat/lon reflecting actual u-blox NEO-6M
firmware no-fix behavior. Known limitation: the true geographic coordinate (0 deg N, 0 deg E) in
the Gulf of Guinea would produce a false positive. Acceptable for Indian subcontinent launch sites.

**Battery threshold at 3.40 V.** Conservative cutoff for 1S LiPo cells under light load.
Actual brownout voltage is cell-chemistry and load-current dependent.

**Missing packet estimation.** The estimator floor(gap / nominal_interval) - 1 is a first-order
approximation. It underestimates if the transmitter burst-retransmits missed packets.

---

## Extending the Analyzer

To add a new anomaly detector:

1. Add a private method _detect_<anomaly>(self, df) -> List[Dict] to TelemetryQualityAnalyzer.
2. Add the corresponding field to the TelemetryQualityReport dataclass.
3. Call the method in analyze_dataframe() and store the result.
4. Add a serialization entry in the API handler in app.py.
5. Add at least one unit test in tests/test_telemetry_analyzer.py.
6. Update the rendering logic in frontend/analysis.html if needed.

---

## Related Files

| File | Role |
|---|---|
| backend/core/telemetry_analyzer.py | Core analysis logic |
| backend/app.py | FastAPI endpoint integration |
| frontend/analysis.html | Quality Inspector UI |
| tests/test_telemetry_analyzer.py | Unit test suite (11 tests) |
| test_cases/ | 10 synthetic flight CSVs used for benchmarking |
| docs/research_paper_draft.md | Sections 13-14: methodology and empirical results |
