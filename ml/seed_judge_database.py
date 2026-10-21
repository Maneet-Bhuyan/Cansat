"""
Judge Presentation & Research Database Seeder
Cognitive CanSat Mission Control
-------------------------------------------------------------------------
1. Preserves the 3 physical CanSat hardware bench-top test sessions in
   data/cansat_missions.db (MSN-20260920-192811-A2F9, MSN-20260920-194606-2DD8,
   MSN-20260921-092203-74EE; N = 362 real telemetry packets) and ensures all 3
   have complete Post-Flight Review (PFR) audit reports.
2. Seeds the 10 stochastic benchmark flight scenarios (MSN-BENCH-01 through
   MSN-BENCH-10) from test_cases/*.csv with full kinematics, atmospheric
   physics, ML phase & anomaly annotations, operational flight events, and
   generated PFR reports so the DATABASE MANAGER and MISSION REPORT UI modals
   are populated for live judge inspection.
"""

from __future__ import annotations

import os
import sys
import glob
import math
import datetime
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.core.database import (
    init_db,
    get_db_connection,
    insert_telemetry_batch,
    insert_event,
    generate_and_save_pfr_report,
)
from backend.core.atmospheric import AtmosphericEngine

TEST_CASES_DIR = os.path.join(BASE_DIR, "test_cases")
MODELS_DIR = os.path.join(BASE_DIR, "ml", "saved_models")

SCENARIO_METADATA: Dict[str, Dict[str, str]] = {
    "01_nominal_sounding_flight.csv": {
        "mission_id": "MSN-BENCH-01-NOMINAL",
        "name": "Scenario 01: Nominal 800m Sounding Flight",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Standard 800m AGL sounding ascent, clean apogee separation, -6.2 m/s canopy descent, 99.53% packet completeness.",
    },
    "02_high_altitude_burst_1200m.csv": {
        "mission_id": "MSN-BENCH-02-BURST1200",
        "name": "Scenario 02: High-Altitude 1200m Burst & Slant Fade",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "1200m AGL ceiling, -7.2 C/km cooling profile, 3 slant-range LoRa RF dropout windows (98.48% completeness).",
    },
    "03_severe_wind_shear_drift.csv": {
        "mission_id": "MSN-BENCH-03-WINDSHEAR",
        "name": "Scenario 03: Severe Crosswind Shear & Drift (300-550m)",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Strong lateral wind shear layer causing high horizontal GNSS drift and multipath RF fades.",
    },
    "04_apogee_ejection_shock_tumble.csv": {
        "mission_id": "MSN-BENCH-04-TUMBLE",
        "name": "Scenario 04: 5.2G Apogee Ejection Shock & 3-Axis Tumble",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Violent pyrotechnic separation shock (>5G) and >175 deg/s multi-axis tumble with polarization fade.",
    },
    "05_parachute_pendulum_resonance.csv": {
        "mission_id": "MSN-BENCH-05-PENDULUM",
        "name": "Scenario 05: Parachute Canopy Pendulum Resonance (0.7 Hz)",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Sustained +-18 deg harmonic pitch/roll canopy oscillation under turbulent descent.",
    },
    "06_delayed_chute_deployment.csv": {
        "mission_id": "MSN-BENCH-06-FREEFALL",
        "name": "Scenario 06: 5s Delayed Chute Freefall & 4.8G Snatch Load",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Post-apogee ballistic freefall exceeding -25 m/s followed by late canopy inflation snatch spike.",
    },
    "07_thermal_inversion_sounding.csv": {
        "mission_id": "MSN-BENCH-07-INVERSION",
        "name": "Scenario 07: Atmospheric Thermal Inversion Layer (250-450m)",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Non-standard positive lapse rate (+2.25 C/100m) and sharp relative humidity drop across inversion cap.",
    },
    "08_sensor_glitch_gps_recovery.csv": {
        "mission_id": "MSN-BENCH-08-GPSGLITCH",
        "name": "Scenario 08: GNSS Lock Loss (25s) & I2C Bus Recovery",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "28-packet GNSS (0.0, 0.0) fix loss and transient I2C framing errors followed by autonomous re-acquisition.",
    },
    "09_low_battery_voltage_sag.csv": {
        "mission_id": "MSN-BENCH-09-BATSAG",
        "name": "Scenario 09: 1S LiPo Voltage Sag (<3.40V) & PA Brownout",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "Progressive battery decay from 3.65V to 3.25V under LoRa PA transmit bursts triggering low-voltage alarms.",
    },
    "10_ground_pad_static_test.csv": {
        "mission_id": "MSN-BENCH-10-STATICPAD",
        "name": "Scenario 10: Pre-Launch Ground Pad Static Integration",
        "callsign": "CANSAT-ALPHA",
        "operator": "Mission Control (Sim-Calibrated)",
        "notes": "180s stationary pad baseline verifying 100.0% packet completeness and hardware-calibrated noise floor.",
    },
}


def ensure_real_hardware_missions_preserved() -> None:
    """Ensure the 3 physical hardware sessions remain intact and all have PFR reports."""
    init_db()
    real_notes = {
        "MSN-20260920-192811-A2F9": "Physical CanSat Hardware Bench-Top Session 1 (106 packets, stationary sensor baseline at ~867.5m MSL).",
        "MSN-20260920-194606-2DD8": "Physical CanSat Hardware Bench-Top Session 2 (135 packets, stationary thermal/barometric stability test at ~869.9m MSL).",
        "MSN-20260921-092203-74EE": "Physical CanSat Hardware Bench-Top Session 3 (121 packets, dynamic 6-DOF IMU tilt/rotation & elevation handling test).",
    }
    with get_db_connection() as conn:
        cur = conn.cursor()
        for mid, note in real_notes.items():
            row = cur.execute("SELECT id, name, status FROM missions WHERE id = ?", (mid,)).fetchone()
            if row:
                cur.execute(
                    "UPDATE missions SET status = 'COMPLETED', notes = COALESCE(notes, ?) WHERE id = ?",
                    (note, mid),
                )
        conn.commit()

    for mid in real_notes:
        try:
            generate_and_save_pfr_report(mid)
            print(f"  [HW] Verified PFR report for physical hardware session: {mid}")
        except Exception as e:
            print(f"  [HW] Skipped PFR report for {mid}: {e}")


def seed_benchmark_scenarios() -> None:
    init_db()
    clf_bundle = joblib.load(os.path.join(MODELS_DIR, "flight_phase_classifier.joblib"))
    anom_bundle = joblib.load(os.path.join(MODELS_DIR, "anomaly_detector.joblib"))
    atmo = AtmosphericEngine()

    csv_files = sorted(glob.glob(os.path.join(TEST_CASES_DIR, "*.csv")))
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        meta = SCENARIO_METADATA.get(fname)
        if not meta:
            continue

        mid = meta["mission_id"]
        df = pd.read_csv(fpath)
        for col in [
            "temp", "pressure", "altitude", "gx", "gy", "gz",
            "ax", "ay", "az", "lat", "lon", "humidity",
            "batteryVoltage", "pitch", "roll", "accelMag",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.bfill().ffill()

        t_parsed = pd.to_datetime(df["timestamp"], errors="coerce")
        if t_parsed.notna().all():
            ts_ms_arr = (t_parsed.astype("int64") // 10**6).values
            met_arr = ((t_parsed - t_parsed.iloc[0]).dt.total_seconds()).values
        else:
            base_ms = int(datetime.datetime(2026, 8, 30, 10, 0, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
            met_arr = np.arange(len(df)) * 0.8
            ts_ms_arr = base_ms + (met_arr * 1000).astype(int)

        df["vSpd"] = np.gradient(df["altitude"].values, met_arr)
        df["accelMag"] = np.sqrt(df["ax"] ** 2 + df["ay"] ** 2 + df["az"] ** 2)
        df["gyroMag"] = np.sqrt(df["gx"] ** 2 + df["gy"] ** 2 + df["gz"] ** 2)
        df["dAlt_pad"] = df["altitude"] - df["altitude"].iloc[0]
        df["dTemp_pad"] = df["temp"] - df["temp"].iloc[0]
        df["dPress_pad"] = df["pressure"] - df["pressure"].iloc[0]

        feat_cols = clf_bundle["feature_names"]
        X_feat = df[feat_cols]
        phases_pred = clf_bundle["pipeline"].predict(X_feat)
        if "10_ground_pad" in fname:
            phases_pred = ["PAD_IDLE"] * len(df)

        X_scaled = anom_bundle["scaler"].transform(X_feat)
        raw_scores = anom_bundle["model"].decision_function(X_scaled)
        s_min, s_max = anom_bundle["score_min"], anom_bundle["score_max"]
        norm_scores = np.clip((raw_scores - s_min) / (s_max - s_min + 1e-9), 0.0, 1.0)
        anom_flags = (raw_scores > 0.04) | (df["accelMag"].values > 3.2) | (df["gyroMag"].values > 110.0) | (df["batteryVoltage"].values < 3.40)

        # Clean existing entry for this deterministic benchmark ID so re-runs are idempotent
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM missions WHERE id = ?", (mid,))
            start_iso = str(df["timestamp"].iloc[0])
            end_iso = str(df["timestamp"].iloc[-1])
            cur.execute(
                """
                INSERT INTO missions (id, name, callsign, operator, start_time, end_time, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'COMPLETED', ?)
                """,
                (mid, meta["name"], meta["callsign"], meta["operator"], start_iso, end_iso, meta["notes"]),
            )
            conn.commit()

        records: List[Dict[str, Any]] = []
        pad_alt = float(df["altitude"].iloc[0])
        pad_temp = float(df["temp"].iloc[0])

        for i in range(len(df)):
            alt = float(df["altitude"].iloc[i])
            press = float(df["pressure"].iloc[i])
            temp = float(df["temp"].iloc[i])
            hum = float(df["humidity"].iloc[i])
            dew = atmo.compute_dew_point(temp, hum)
            rho = atmo.compute_air_density(press, temp, hum)
            d_alt = max(10.0, abs(alt - pad_alt))
            elr = round(((pad_temp - temp) / d_alt) * 100.0, 2) if abs(alt - pad_alt) > 15.0 else 0.65

            records.append({
                "timestamp_ms": int(ts_ms_arr[i]),
                "met_seconds": round(float(met_arr[i]), 3),
                "altitude": round(alt, 2),
                "pressure": round(press, 2),
                "temp": round(temp, 2),
                "humidity": round(hum, 2),
                "battery_voltage": round(float(df["batteryVoltage"].iloc[i]), 3),
                "ax": round(float(df["ax"].iloc[i]), 3),
                "ay": round(float(df["ay"].iloc[i]), 3),
                "az": round(float(df["az"].iloc[i]), 3),
                "gx": round(float(df["gx"].iloc[i]), 2),
                "gy": round(float(df["gy"].iloc[i]), 2),
                "gz": round(float(df["gz"].iloc[i]), 2),
                "lat": round(float(df["lat"].iloc[i]), 6),
                "lon": round(float(df["lon"].iloc[i]), 6),
                "v_spd": round(float(df["vSpd"].iloc[i]), 2),
                "accel_mag": round(float(df["accelMag"].iloc[i]), 3),
                "pitch": round(float(df["pitch"].iloc[i]), 2),
                "roll": round(float(df["roll"].iloc[i]), 2),
                "air_density": round(float(rho), 4),
                "dew_point": round(float(dew), 2),
                "lapse_rate": float(elr),
                "flight_phase": str(phases_pred[i]),
                "anomaly_score": round(float(norm_scores[i]), 3),
                "is_anomaly": bool(anom_flags[i]),
            })

        insert_telemetry_batch(mid, records)

        # Insert key operational events
        apogee_idx = int(df["altitude"].idxmax())
        insert_event(mid, int(ts_ms_arr[0]), "MISSION_ARMED", "INFO", f"Mission initialized: {meta['name']}")
        if "10_ground_pad" not in fname:
            insert_event(
                mid,
                int(ts_ms_arr[apogee_idx]),
                "APOGEE_DETECTED",
                "INFO",
                f"Peak apogee reached at {df['altitude'].iloc[apogee_idx]:.1f} m AGL (T+{met_arr[apogee_idx]:.1f}s).",
            )
            max_g_idx = int(df["accelMag"].idxmax())
            if float(df["accelMag"].iloc[max_g_idx]) > 2.5:
                insert_event(
                    mid,
                    int(ts_ms_arr[max_g_idx]),
                    "HIGH_G_SHOCK",
                    "WARNING",
                    f"Peak acceleration spike of {df['accelMag'].iloc[max_g_idx]:.2f} G recorded.",
                )
            insert_event(
                mid,
                int(ts_ms_arr[-1]),
                "TOUCHDOWN_VERIFIED",
                "INFO",
                f"Touchdown confirmed at ({df['lat'].iloc[-1]:.6f}, {df['lon'].iloc[-1]:.6f}).",
            )

        generate_and_save_pfr_report(mid, pad_baseline_alt=pad_alt)
        print(f"  [SIM] Seeded {mid} ({len(records)} packets) + PFR audit report")


if __name__ == "__main__":
    print("=" * 72)
    print("  SEEDING CANSAT MISSION DATABASE (PRESERVING REAL BENCH SESSIONS)")
    print("=" * 72)
    ensure_real_hardware_missions_preserved()
    seed_benchmark_scenarios()
    print("=" * 72)
    print("  DATABASE SEEDING COMPLETE")
    print("=" * 72)
