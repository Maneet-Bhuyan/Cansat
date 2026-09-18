# Verification & Test Suites

This directory contains automated unit tests, verification suites, and synthetic flight data generators.

## Test Scripts

* **`selftest.ps1`**: Automated PowerShell test suite verifying mission elapsed time formatting, flight state machine phase progression across all 10 profiles, and mathematical bounds (17 assertions).
* **`selftest.js`**: Node.js offline unit tests verifying packet parsing, kinematics derivation (pitch, roll, vertical speed), and RFC 4180 CSV serialization (27 assertions).
* **`test_backend_core.py`**: Python unit test suite verifying 1D Kalman state estimation, 6-DOF attitude fusion, atmospheric sounding physics, tare calibration, and ML inference (12 assertions).
* **`test_firmware_protocol.py`**: Python binary struct packing and ESP-NOW chunk slicing / reassembly verification (4 assertions).
* **`test_sm.ps1`**: Focused state machine transition verifier for rapid flight phase debugging (10 profiles).
* **`generate_test_cases.ps1` / `generate_test_cases.js`**: Generators that synthesize the 10 distinct flight profiles stored in `test_cases/`.

## Running the Tests

From PowerShell in the project root:
```powershell
powershell -ExecutionPolicy Bypass -File tests/selftest.ps1
```

From Node.js:
```bash
node tests/selftest.js
```
