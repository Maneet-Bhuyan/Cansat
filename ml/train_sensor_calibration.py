"""
Cognitive CanSat - ML Sensor Telemetry Calibration & Super-Accuracy Model
-------------------------------------------------------------------------
Trains a multi-output physics-informed machine learning regressor that:
  1. Maps raw, noisy barometric and IMU telemetry to true, calibrated altitude & vertical speed.
  2. Trains a scale-invariant residual estimator f_ET(u_k) predicting aerodynamic Venturi
     dynamic-pressure depression (delta_h = h_raw - h_true) and velocity error across
     arbitrary sounding altitudes without extrapolation clipping.
  3. Maintains strict train/test flight separation (training seed=1001, disjoint from
     Monte Carlo evaluation seed=20261022).
"""

import os
import glob
import math
import json
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "test_cases")
MODELS_DIR = os.path.join(BASE_DIR, "ml", "saved_models")
METRICS_PATH = os.path.join(BASE_DIR, "ml", "model_metrics.json")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS = [
    'raw_altitude', 'pressure', 'temp', 'humidity',
    'ax', 'ay', 'az', 'accelMag',
    'gx', 'gy', 'gz', 'gyroMag',
    'vSpd_raw'
]

# Scale-invariant feature columns for residual aerodynamic depression prediction f_ET(u_k)
RESIDUAL_FEATURE_COLS = [
    'pressure', 'temp', 'humidity',
    'ax', 'ay', 'az', 'accelMag',
    'gx', 'gy', 'gz', 'gyroMag',
    'vSpd_raw', 'dynamic_pressure_proxy'
]

TARGET_COLS = [
    'calibrated_altitude',
    'calibrated_vspd'
]

RESIDUAL_TARGET_COLS = [
    'altitude_residual',
    'calibrated_vspd'
]


def compute_aerodynamic_venturi_bias(true_vz: np.ndarray, ax: np.ndarray, ay: np.ndarray, az: np.ndarray, cp_venturi: float = 0.48) -> np.ndarray:
    """
    Computes physical Venturi static-port depression bias delta_h (m) as a function of
    vertical airspeed, airframe angle-of-attack (tilt from IMU), and stochastic aerodynamic coefficient cp.
    """
    tilt_sin = np.clip(np.sqrt(ax**2 + ay**2) / np.maximum(0.2, np.sqrt(ax**2 + ay**2 + az**2)), 0.0, 1.0)
    effective_cp = cp_venturi * (1.0 + 0.30 * tilt_sin)
    bias_m = effective_cp * (true_vz ** 2) / 9.80665
    return np.clip(bias_m, 0.0, 15.0)


def load_and_augment_dataset():
    """Load all 10 mission profile datasets plus a disjoint 40-flight training ensemble (seed=1001)."""
    csv_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No CSV flight datasets found in {DATA_DIR}")

    all_frames = []
    rng_base = np.random.default_rng(1001)

    for idx, fpath in enumerate(csv_files):
        df = pd.read_csv(fpath)
        if len(df) < 5:
            continue

        df = df.copy()
        for col in ['temp', 'pressure', 'altitude', 'gx', 'gy', 'gz', 'ax', 'ay', 'az', 'humidity']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.bfill().ffill()
        if 'altitude' in df.columns:
            true_alt = df['altitude'].values.astype(float)
        else:
            continue

        dt = 0.8
        true_vz = np.gradient(true_alt, dt)

        ax = df['ax'].values.astype(float) if 'ax' in df.columns else np.zeros(len(df))
        ay = df['ay'].values.astype(float) if 'ay' in df.columns else np.zeros(len(df))
        az = df['az'].values.astype(float) if 'az' in df.columns else np.ones(len(df))
        gx = df['gx'].values.astype(float) if 'gx' in df.columns else np.zeros(len(df))
        gy = df['gy'].values.astype(float) if 'gy' in df.columns else np.zeros(len(df))
        gz = df['gz'].values.astype(float) if 'gz' in df.columns else np.zeros(len(df))
        temp = df['temp'].values.astype(float) if 'temp' in df.columns else np.full(len(df), 25.0)
        press = df['pressure'].values.astype(float) if 'pressure' in df.columns else np.full(len(df), 1013.25)
        hum = df['humidity'].values.astype(float) if 'humidity' in df.columns else np.full(len(df), 50.0)

        accel_mag = np.sqrt(ax**2 + ay**2 + az**2)
        gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)

        cp_flight = float(rng_base.uniform(0.38, 0.62))
        bernoulli_alt_bias = compute_aerodynamic_venturi_bias(true_vz, ax, ay, az, cp_venturi=cp_flight)

        sensor_noise = rng_base.normal(0.0, 0.742, size=len(df))
        raw_alt = true_alt + bernoulli_alt_bias + sensor_noise
        raw_vz = np.gradient(raw_alt, dt)

        press_noisy = press + rng_base.normal(0.0, 0.143, size=len(df))
        temp_noisy = temp + rng_base.normal(0.0, 0.165, size=len(df))
        rho_est = (press_noisy * 100.0) / (287.058 * (temp_noisy + 273.15))
        q_proxy = 0.5 * rho_est * (raw_vz ** 2)

        augmented_df = pd.DataFrame({
            'flight_group': idx,
            'raw_altitude': raw_alt,
            'pressure': press_noisy,
            'temp': temp_noisy,
            'humidity': hum + rng_base.normal(0.0, 1.5, size=len(df)),
            'ax': ax + rng_base.normal(0.0, 0.012, size=len(df)),
            'ay': ay + rng_base.normal(0.0, 0.012, size=len(df)),
            'az': az + rng_base.normal(0.0, 0.012, size=len(df)),
            'accelMag': accel_mag,
            'gx': gx + rng_base.normal(0.0, 1.1, size=len(df)),
            'gy': gy + rng_base.normal(0.0, 1.1, size=len(df)),
            'gz': gz + rng_base.normal(0.0, 1.1, size=len(df)),
            'gyroMag': gyro_mag,
            'vSpd_raw': raw_vz,
            'dynamic_pressure_proxy': q_proxy,
            'calibrated_altitude': true_alt,
            'altitude_residual': raw_alt - true_alt,
            'calibrated_vspd': true_vz
        })
        all_frames.append(augmented_df)

    # Generate 40 synthetic training trajectories using seed=1001 (strictly disjoint from test seed=20261022)
    for synth_idx in range(40):
        apogee_m = float(rng_base.uniform(450.0, 1250.0))
        ascent_v = float(rng_base.uniform(3.8, 5.4))
        term_v = -float(rng_base.uniform(4.2, 6.2))
        cp_val = float(rng_base.uniform(0.38, 0.62))
        freefall_delay = float(rng_base.uniform(3.0, 8.5)) if synth_idx % 4 == 0 else 0.0

        dt = 0.8
        t_ap = apogee_m / ascent_v
        t_desc = apogee_m / abs(term_v)
        n_pts = int((t_ap + t_desc + 20.0) / dt)
        t_arr = np.arange(n_pts) * dt
        vz_t = np.zeros(n_pts)
        ax_t = np.zeros(n_pts)
        ay_t = np.zeros(n_pts)
        az_t = np.ones(n_pts)
        gx_t = np.zeros(n_pts)
        gy_t = np.zeros(n_pts)
        gz_t = np.zeros(n_pts)

        for i, t in enumerate(t_arr):
            if t < 10.0:
                vz_t[i] = 0.0
            elif t < 10.0 + t_ap:
                vz_t[i] = ascent_v + 0.25 * math.sin(0.2 * t)
                az_t[i] = 1.02
                gx_t[i] = 3.0 * math.sin(0.4 * t)
            elif t < 10.0 + t_ap + 3.2:
                frac = (t - (10.0 + t_ap)) / 3.2
                vz_t[i] = ascent_v * (1.0 - 2.0 * frac)
                az_t[i] = 2.6
                gx_t[i] = 95.0 * math.sin(4.0 * t)
                gy_t[i] = 80.0 * math.cos(4.0 * t)
            else:
                tau = t - (10.0 + t_ap + 3.2)
                if freefall_delay > 0 and tau < freefall_delay:
                    vz_t[i] = max(-26.0, -ascent_v - 7.5 * tau)
                    az_t[i] = 0.12
                    gx_t[i] = 55.0 * math.sin(tau * 3.0)
                    gy_t[i] = 48.0 * math.cos(tau * 3.0)
                else:
                    tau_c = tau - freefall_delay
                    v_ent = -22.0 if freefall_delay > 0 else -ascent_v
                    vz_t[i] = term_v + (v_ent - term_v) * math.exp(-tau_c / 2.2)
                    p_amp = 0.35 if synth_idx % 5 == 0 else 0.18
                    ax_t[i] = p_amp * math.sin(tau_c * 1.9)
                    ay_t[i] = p_amp * math.cos(tau_c * 1.9)
                    az_t[i] = 0.96
                    gx_t[i] = (60.0 if p_amp > 0.3 else 14.0) * math.sin(tau_c * 1.9)
                    gy_t[i] = (54.0 if p_amp > 0.3 else 12.0) * math.cos(tau_c * 1.9)

        alt_t = np.zeros(n_pts)
        alt_t[0] = 0.4
        for i in range(1, n_pts):
            alt_t[i] = alt_t[i - 1] + 0.5 * (vz_t[i - 1] + vz_t[i]) * dt
            if i > int((10.0 + t_ap) / dt) + 5 and alt_t[i] <= 0.25:
                alt_t[i] = 0.25
                vz_t[i] = 0.0
                ax_t[i], ay_t[i], az_t[i] = 0.0, 0.0, 1.0
                gx_t[i], gy_t[i], gz_t[i] = 0.0, 0.0, 0.0

        temp_t = 26.0 - (alt_t / 1000.0) * 6.5
        press_t = 1013.25 * np.power(1.0 - (0.0065 * alt_t) / 288.15, 5.255)
        hum_t = np.clip(56.0 + (alt_t / 1000.0) * 18.0, 10.0, 98.0)

        bias_t = compute_aerodynamic_venturi_bias(vz_t, ax_t, ay_t, az_t, cp_venturi=cp_val)
        raw_alt_t = alt_t + bias_t + rng_base.normal(0.0, 0.742 * 1.25, size=n_pts)
        raw_vz_t = np.gradient(raw_alt_t, dt)

        press_n = press_t + rng_base.normal(0.0, 0.143, size=n_pts)
        temp_n = temp_t + rng_base.normal(0.0, 0.165, size=n_pts)
        ax_n = ax_t + rng_base.normal(0.0, 0.0114, size=n_pts)
        ay_n = ay_t + rng_base.normal(0.0, 0.0114, size=n_pts)
        az_n = az_t + rng_base.normal(0.0, 0.0114, size=n_pts)
        gx_n = gx_t + rng_base.normal(0.0, 1.114, size=n_pts)
        gy_n = gy_t + rng_base.normal(0.0, 1.114, size=n_pts)
        gz_n = gz_t + rng_base.normal(0.0, 1.114, size=n_pts)

        accel_m = np.sqrt(ax_n**2 + ay_n**2 + az_n**2)
        gyro_m = np.sqrt(gx_n**2 + gy_n**2 + gz_n**2)
        rho_n = (press_n * 100.0) / (287.058 * (temp_n + 273.15))
        q_n = 0.5 * rho_n * (raw_vz_t ** 2)

        synth_df = pd.DataFrame({
            'flight_group': 100 + synth_idx,
            'raw_altitude': raw_alt_t,
            'pressure': press_n,
            'temp': temp_n,
            'humidity': hum_t + rng_base.normal(0.0, 1.518, size=n_pts),
            'ax': ax_n,
            'ay': ay_n,
            'az': az_n,
            'accelMag': accel_m,
            'gx': gx_n,
            'gy': gy_n,
            'gz': gz_n,
            'gyroMag': gyro_m,
            'vSpd_raw': raw_vz_t,
            'dynamic_pressure_proxy': q_n,
            'calibrated_altitude': alt_t,
            'altitude_residual': raw_alt_t - alt_t,
            'calibrated_vspd': vz_t
        })
        all_frames.append(synth_df)

    combined_df = pd.concat(all_frames, ignore_index=True)
    return combined_df


def compute_aerodynamic_venturi_bias(true_vz: np.ndarray, ax: np.ndarray, ay: np.ndarray, az: np.ndarray, cp_venturi: float = 0.48) -> np.ndarray:
    """
    Computes physical Venturi static-port depression bias delta_h (m) as a function of
    vertical airspeed, airframe angle-of-attack (tilt from IMU), and stochastic aerodynamic coefficient cp.
    """
    tilt_sin = np.clip(np.sqrt(ax**2 + ay**2) / np.maximum(0.2, np.sqrt(ax**2 + ay**2 + az**2)), 0.0, 1.0)
    effective_cp = cp_venturi * (1.0 + 0.30 * tilt_sin)
    bias_m = effective_cp * (true_vz ** 2) / 9.80665
    return np.clip(bias_m, 0.0, 15.0)


def train_sensor_calibrator():
    print("[1/4] Loading and augmenting telemetry datasets (strictly disjoint training seed=1001)...")
    df = load_and_augment_dataset()
    print(f"      Loaded {len(df)} total telemetry samples across {df['flight_group'].nunique()} training flight trajectories.")

    # Flight-level group split (held-out flights never seen in training)
    unique_flights = df['flight_group'].unique()
    train_flights = set(unique_flights[:-8])
    train_mask = df['flight_group'].isin(train_flights).values
    test_mask = ~train_mask

    X_train = df.loc[train_mask, FEATURE_COLS].values
    y_train = df.loc[train_mask, TARGET_COLS].values
    X_test = df.loc[test_mask, FEATURE_COLS].values
    y_test = df.loc[test_mask, TARGET_COLS].values

    print("[2/4] Training Direct & Scale-Invariant Residual ExtraTrees Calibrator Pipelines...")
    pipeline = Pipeline([
        ('scaler', RobustScaler()),
        ('model', ExtraTreesRegressor(
            n_estimators=80,
            max_depth=14,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        ))
    ])
    pipeline.fit(X_train, y_train)

    # Train scale-invariant residual pipeline f_ET(u_k) -> [delta_h, v_z_calibrated]
    X_res_train = df.loc[train_mask, RESIDUAL_FEATURE_COLS].values
    y_res_train = df.loc[train_mask, RESIDUAL_TARGET_COLS].values
    X_res_test = df.loc[test_mask, RESIDUAL_FEATURE_COLS].values
    y_res_test = df.loc[test_mask, RESIDUAL_TARGET_COLS].values

    residual_pipeline = Pipeline([
        ('scaler', RobustScaler()),
        ('model', ExtraTreesRegressor(
            n_estimators=80,
            max_depth=12,
            min_samples_split=6,
            random_state=42,
            n_jobs=-1
        ))
    ])
    residual_pipeline.fit(X_res_train, y_res_train)

    print("[3/4] Evaluating held-out flight generalization performance...")
    res_pred = residual_pipeline.predict(X_res_test)
    raw_alt_test = df.loc[test_mask, 'raw_altitude'].values
    true_alt_test = df.loc[test_mask, 'calibrated_altitude'].values
    pred_alt_test = raw_alt_test - res_pred[:, 0]

    alt_rmse = float(np.sqrt(mean_squared_error(true_alt_test, pred_alt_test)))
    alt_mae = float(mean_absolute_error(true_alt_test, pred_alt_test))
    alt_r2 = float(r2_score(true_alt_test, pred_alt_test))

    vz_rmse = float(np.sqrt(mean_squared_error(y_res_test[:, 1], res_pred[:, 1])))
    vz_mae = float(mean_absolute_error(y_res_test[:, 1], res_pred[:, 1]))
    vz_r2 = float(r2_score(y_res_test[:, 1], res_pred[:, 1]))

    print(f"      Held-Out Flight Altitude Performance: R2 = {alt_r2:.4f} | RMSE = {alt_rmse:.3f} m | MAE = {alt_mae:.3f} m")
    print(f"      Held-Out Flight Velocity Performance: R2 = {vz_r2:.4f} | RMSE = {vz_rmse:.3f} m/s | MAE = {vz_mae:.3f} m/s")

    model_artifact = {
        'pipeline': pipeline,
        'residual_pipeline': residual_pipeline,
        'feature_names': FEATURE_COLS,
        'residual_feature_names': RESIDUAL_FEATURE_COLS,
        'target_names': TARGET_COLS,
        'residual_target_names': RESIDUAL_TARGET_COLS,
        'metrics': {
            'altitude_r2': alt_r2,
            'altitude_rmse': alt_rmse,
            'altitude_mae': alt_mae,
            'vspd_r2': vz_r2,
            'vspd_rmse': vz_rmse,
            'vspd_mae': vz_mae
        }
    }

    out_path = os.path.join(MODELS_DIR, "sensor_calibrator.joblib")
    joblib.dump(model_artifact, out_path)
    print(f"      Saved calibrated model to: {out_path}")

    metrics_data = {}
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, 'r') as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {}

    metrics_data["sensor_calibrator"] = {
        "model_type": "ExtraTreesRegressor (Scale-Invariant Residual f_ET)",
        "features": FEATURE_COLS,
        "residual_features": RESIDUAL_FEATURE_COLS,
        "targets": TARGET_COLS,
        "altitude_r2": round(alt_r2, 4),
        "altitude_rmse_m": round(alt_rmse, 3),
        "altitude_mae_m": round(alt_mae, 3),
        "vspd_r2": round(vz_r2, 4),
        "vspd_rmse_mps": round(vz_rmse, 3),
        "vspd_mae_mps": round(vz_mae, 3)
    }

    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics_data, f, indent=2)
    print(f"      Updated metrics in: {METRICS_PATH}")

    return model_artifact


if __name__ == "__main__":
    train_sensor_calibrator()
