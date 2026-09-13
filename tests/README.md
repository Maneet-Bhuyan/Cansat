# Verification & Test Suites

This directory contains automated unit tests, verification suites, and synthetic flight data generators.

## Test Scripts

* **`selftest.ps1`**: Automated PowerShell test suite verifying mission elapsed time formatting, flight state machine phase progression across all 10 profiles, and mathematical bounds (17 assertions).
* **`selftest.js`**: Node.js offline unit tests verifying packet parsing, kinematics derivation (pitch, roll, vertical speed), and RFC 4180 CSV serialization.
* **`test_sm.ps1`**: Focused state machine transition verifier for rapid flight phase debugging.
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
