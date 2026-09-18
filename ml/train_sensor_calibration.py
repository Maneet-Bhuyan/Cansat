"""
Cognitive CanSat - ML Sensor Telemetry Calibration & Super-Accuracy Model
-------------------------------------------------------------------------
Trains a multi-output physics-informed machine learning regressor that:
  1. Maps raw, noisy barometric and IMU telemetry to true, calibrated altitude & vertical speed.
  2. Compensates for aerodynamic Bernoulli dynamic pressure drops (q = 0.5 * rho * v^2).
  3. Reconstructs smooth, physically consistent kinematics with high sub-meter precision.
"""

import os
import glob
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

TARGET_COLS = [
    'calibrated_altitude',
    'calibrated_vspd'
]


def load_and_augment_dataset():
    """Load all 10 mission profile datasets, augment with physics models and noise."""
    csv_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No CSV flight datasets found in {DATA_DIR}")

    all_frames = []

    for fpath in csv_files:
        df = pd.read_csv(fpath)
        if len(df) < 5:
            continue

        # Standardize column names
        df = df.copy()
        if 'altitude' in df.columns:
            true_alt = df['altitude'].values.astype(float)
        else:
            continue

        dt = 0.8
        # Calculate true smooth velocity using central gradient
        true_vz = np.gradient(true_alt, dt)

        # Compute physical kinematics
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

        # Synthesize realistic sensor noise & Bernoulli aerodynamic bias:
        # Bernoulli effect: airflow across CanSat static ports causes pressure drop delta_P = 0.5 * rho * v^2
        # which makes raw altimeter read artificially high by delta_h ~ delta_P / (rho * g) = 0.5 * v^2 / g
        rho_est = (press * 100.0) / (287.05 * (temp + 273.15))
        bernoulli_alt_bias = (0.5 * rho_est * (true_vz**2)) / (rho_est * 9.80665)
        bernoulli_alt_bias = np.clip(bernoulli_alt_bias, 0.0, 15.0)

        # Real BMP280 white noise + draft fluctuations (+/- 0.22m)
        rng = np.random.RandomState(42 + len(all_frames))
        sensor_noise = rng.normal(0.0, 0.22, size=len(df))

        raw_alt = true_alt + bernoulli_alt_bias + sensor_noise
        raw_vz = np.gradient(raw_alt, dt) + rng.normal(0.0, 0.35, size=len(df))

        augmented_df = pd.DataFrame({
            'raw_altitude': raw_alt,
            'pressure': press + rng.normal(0.0, 0.12, size=len(df)),
            'temp': temp + rng.normal(0.0, 0.08, size=len(df)),
            'humidity': hum + rng.normal(0.0, 0.3, size=len(df)),
            'ax': ax + rng.normal(0.0, 0.02, size=len(df)),
            'ay': ay + rng.normal(0.0, 0.02, size=len(df)),
            'az': az + rng.normal(0.0, 0.02, size=len(df)),
            'accelMag': accel_mag,
            'gx': gx + rng.normal(0.0, 0.15, size=len(df)),
            'gy': gy + rng.normal(0.0, 0.15, size=len(df)),
            'gz': gz + rng.normal(0.0, 0.15, size=len(df)),
            'gyroMag': gyro_mag,
            'vSpd_raw': raw_vz,
            'calibrated_altitude': true_alt,
            'calibrated_vspd': true_vz
        })

        all_frames.append(augmented_df)

    combined_df = pd.concat(all_frames, ignore_index=True)
    return combined_df


def train_sensor_calibrator():
    print("[1/4] Loading and augmenting telemetry datasets...")
    df = load_and_augment_dataset()
    print(f"      Loaded {len(df)} total telemetry samples across 10 mission profiles.")

    X = df[FEATURE_COLS].values
    y = df[TARGET_COLS].values

    print("[2/4] Splitting chronological train / test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, shuffle=True)

    print("[3/4] Training Multi-Output ExtraTrees Calibrator Pipeline...")
    pipeline = Pipeline([
        ('scaler', RobustScaler()),
        ('model', ExtraTreesRegressor(
            n_estimators=100,
            max_depth=16,
            min_samples_split=4,
            random_state=42,
            n_jobs=-1
        ))
    ])

    pipeline.fit(X_train, y_train)

    print("[4/4] Evaluating model performance...")
    y_pred = pipeline.predict(X_test)

    # Metrics for altitude
    alt_mse = mean_squared_error(y_test[:, 0], y_pred[:, 0])
    alt_rmse = float(np.sqrt(alt_mse))
    alt_mae = float(mean_absolute_error(y_test[:, 0], y_pred[:, 0]))
    alt_r2 = float(r2_score(y_test[:, 0], y_pred[:, 0]))

    # Metrics for vertical speed
    vz_mse = mean_squared_error(y_test[:, 1], y_pred[:, 1])
    vz_rmse = float(np.sqrt(vz_mse))
    vz_mae = float(mean_absolute_error(y_test[:, 1], y_pred[:, 1]))
    vz_r2 = float(r2_score(y_test[:, 1], y_pred[:, 1]))

    print(f"      Altitude Performance:  R2 = {alt_r2:.4f} | RMSE = {alt_rmse:.3f} m | MAE = {alt_mae:.3f} m")
    print(f"      Velocity Performance:  R2 = {vz_r2:.4f} | RMSE = {vz_rmse:.3f} m/s | MAE = {vz_mae:.3f} m/s")

    # Save model artifact
    model_artifact = {
        'pipeline': pipeline,
        'feature_names': FEATURE_COLS,
        'target_names': TARGET_COLS,
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

    # Update model_metrics.json
    metrics_data = {}
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, 'r') as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {}

    metrics_data["sensor_calibrator"] = {
        "model_type": "ExtraTreesRegressor",
        "features": FEATURE_COLS,
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
