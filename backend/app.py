"""
Cognitive CanSat FastAPI Real-Time Machine Learning Backend Server
Serves real-time inference using trained scikit-learn and PyOD models.
"""
import os
import sys

# Ensure repository root is on sys.path so direct script execution (python backend/app.py) works
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import math
import json
import time
import warnings
from typing import Dict, Any, Optional, List, Tuple
from collections import deque
import numpy as np
import pandas as pd
import joblib

import io
import zipfile
import base64
from PIL import Image

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import re

from backend.core.telemetry_analyzer import TelemetryQualityAnalyzer
from backend.core import database
from backend.core.pipeline_bridge import get_pipeline_bridge

# Initialize telemetry pipeline bridge (Redpanda / TimescaleDB / MinIO)
pipeline_bridge = get_pipeline_bridge()

# Suppress minor version warnings for clean telemetry logs
warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "ml", "saved_models")
METRICS_PATH = os.path.join(BASE_DIR, "ml", "model_metrics.json")
TEST_CASES_REALPATH = os.path.realpath(os.path.join(BASE_DIR, "test_cases"))

def _resolve_safe_scenario_csv(scenario_name: str) -> Tuple[str, str]:
    """Sanitize scenario identifier and prevent directory traversal outside test_cases/."""
    clean_name = os.path.basename(scenario_name.strip()).replace(".csv", "")
    if not clean_name or not re.match(r"^[A-Za-z0-9_\-]+$", clean_name):
        raise HTTPException(status_code=400, detail="Invalid scenario name format")
    csv_path = os.path.realpath(os.path.join(TEST_CASES_REALPATH, f"{clean_name}.csv"))
    if not csv_path.startswith(TEST_CASES_REALPATH) or not os.path.isfile(csv_path):
        raise HTTPException(status_code=404, detail=f"Scenario {clean_name} not found")
    return clean_name, csv_path

def _sanitize_filename_token(token: str) -> str:
    """Strip unsafe header characters from filenames used in Content-Disposition."""
    cleaned = re.sub(r"[^A-Za-z0-9_\-]", "_", str(token or "mission"))
    return cleaned[:80] or "mission"

# Initialize persistent SQLite telemetry & mission database
try:
    database.init_db()
    print("[Database] SQLite telemetry & mission database initialized in WAL mode.")
except Exception as db_err:
    print(f"[Database] Warning: Could not initialize database: {db_err}")

app = FastAPI(
    title="Cognitive CanSat ML Telemetry Server",
    description="Real-Time Machine Learning Inference API for Sounding Pico-Satellite Telemetry",
    version="2.0.0"
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response

# Enable GZip compression for high-performance response streaming (HTML/CSS/JS/JSON)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Enable CORS for local file execution and browser dashboard
allowed_origins_env = os.environ.get("CANSAT_ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] if allowed_origins_env != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model state
models_loaded = False
phase_classifier = None
anomaly_detector = None
apogee_regressor = None
model_metrics = {}

def load_models():
    global models_loaded, phase_classifier, anomaly_detector, apogee_regressor, model_metrics
    try:
        clf_path = os.path.join(MODELS_DIR, "flight_phase_classifier.joblib")
        anom_path = os.path.join(MODELS_DIR, "anomaly_detector.joblib")
        reg_path = os.path.join(MODELS_DIR, "apogee_regressor.joblib")

        if os.path.exists(clf_path):
            phase_classifier = joblib.load(clf_path)
        if os.path.exists(anom_path):
            anomaly_detector = joblib.load(anom_path)
        if os.path.exists(reg_path):
            apogee_regressor = joblib.load(reg_path)
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, "r") as f:
                model_metrics = json.load(f)

        models_loaded = (phase_classifier is not None and anomaly_detector is not None)
        print(f"[ML Server] Models successfully loaded. Status: {models_loaded}")
    except Exception as e:
        print(f"[ML Server] Error loading models: {e}")
        models_loaded = False

load_models()

# Global vision model state
vision_guard = None
tinylandingnet_model = None
mobilenet_v3_small_model = None
resnet18_model = None

def load_vision_models():
    global vision_guard, tinylandingnet_model, mobilenet_v3_small_model, resnet18_model
    try:
        from ml.vision_guard import AerialVisionGuard
        from ml.train_tinyml_vision import TinyLandingNet
        import torch
        import torch.nn as nn
        from torchvision import models
        vision_guard = AerialVisionGuard()

        pth_path = os.path.join(MODELS_DIR, "tinylandingnet_best.pth")
        if os.path.exists(pth_path):
            net = TinyLandingNet(num_classes=4)
            net.load_state_dict(torch.load(pth_path, map_location="cpu"))
            net.eval()
            tinylandingnet_model = net
            print("[ML Server] TinyLandingNet vision model successfully loaded.")
        else:
            print("[ML Server] Notice: tinylandingnet_best.pth not found; vision inference in fallback mode.")

        mb_pth = os.path.join(MODELS_DIR, "mobilenet_v3_small_best.pth")
        if os.path.exists(mb_pth):
            mb = models.mobilenet_v3_small(weights=None)
            mb.classifier[3] = nn.Linear(mb.classifier[3].in_features, 4)
            mb.load_state_dict(torch.load(mb_pth, map_location="cpu"))
            mb.eval()
            mobilenet_v3_small_model = mb
            print("[ML Server] MobileNetV3-Small vision model successfully loaded.")

        res_pth = os.path.join(MODELS_DIR, "resnet18_best.pth")
        if os.path.exists(res_pth):
            res18 = models.resnet18(weights=None)
            res18.fc = nn.Linear(res18.fc.in_features, 4)
            res18.load_state_dict(torch.load(res_pth, map_location="cpu"))
            res18.eval()
            resnet18_model = res18
            print("[ML Server] ResNet-18 vision model successfully loaded.")
    except Exception as e:
        print(f"[ML Server] Warning: Could not initialize vision models: {e}")

load_vision_models()

class TelemetryPayload(BaseModel):
    temp: float = Field(..., description="Ambient temperature in °C")
    pressure: float = Field(..., description="Barometric pressure in hPa")
    altitude: float = Field(..., description="Barometric/GPS Altitude in meters")
    gx: float = Field(0.0, description="Gyro X in °/s")
    gy: float = Field(0.0, description="Gyro Y in °/s")
    gz: float = Field(0.0, description="Gyro Z in °/s")
    ax: float = Field(0.0, description="Accel X in G")
    ay: float = Field(0.0, description="Accel Y in G")
    az: float = Field(1.0, description="Accel Z in G")
    lat: float = Field(22.5727, description="GPS Latitude")
    lon: float = Field(88.3655, description="GPS Longitude")
    humidity: float = Field(50.0, description="Relative Humidity in %")
    batteryVoltage: float = Field(4.10, description="Cell Voltage in Volts")
    vSpd: Optional[float] = Field(None, description="Vertical Velocity in m/s")
    padAlt: Optional[float] = Field(0.0, description="Launch pad baseline altitude")
    padTemp: Optional[float] = Field(25.0, description="Launch pad baseline temperature")
    padPress: Optional[float] = Field(1013.25, description="Launch pad baseline pressure")

def compute_physics_soundings(temp_c: float, press_hpa: float, hum_pct: float, alt_m: float, pad_alt: float, pad_temp: float):
    # Magnus-Tetens Dew Point
    a, b = 17.625, 243.04
    clamped_hum = max(1.0, min(100.0, hum_pct))
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(clamped_hum / 100.0)
    dew_point = (b * alpha) / (a - alpha)

    # Ideal Gas Law Air Density
    p_pa = press_hpa * 100.0
    t_kelvin = temp_c + 273.15
    r_specific = 287.058
    air_density = p_pa / (r_specific * t_kelvin)

    # Environmental Lapse Rate (ELR)
    lapse_rate = 0.65
    if abs(alt_m - pad_alt) > 15.0:
        d_alt = alt_m - pad_alt
        d_temp = temp_c - pad_temp
        lapse_rate = -(d_temp / d_alt) * 100.0

    return dew_point, air_density, lapse_rate

live_telemetry_history = deque(maxlen=20)

def run_ml_inference(payload: TelemetryPayload) -> Dict[str, Any]:
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Machine Learning models not loaded")

    # Feature extraction
    v_spd = payload.vSpd if payload.vSpd is not None else 0.0
    accel_mag = math.sqrt(payload.ax**2 + payload.ay**2 + payload.az**2)
    gyro_mag = math.sqrt(payload.gx**2 + payload.gy**2 + payload.gz**2)

    live_telemetry_history.append({
        "time": time.time(),
        "temp": payload.temp,
        "pressure": payload.pressure,
        "altitude": payload.altitude,
        "ax": payload.ax,
        "ay": payload.ay,
        "az": payload.az,
        "gx": payload.gx,
        "gy": payload.gy,
        "gz": payload.gz,
        "lat": payload.lat,
        "lon": payload.lon,
        "humidity": payload.humidity,
        "batteryVoltage": payload.batteryVoltage,
        "vSpd": v_spd
    })
    if len(live_telemetry_history) % 20 == 0:
        print(f"[LIVE AUDIT]: Temp={payload.temp:.1f}C, Press={payload.pressure:.1f}hPa, Alt={payload.altitude:.1f}m, Bat={payload.batteryVoltage:.2f}V, vSpd={v_spd:.2f}m/s")
    pad_alt = payload.padAlt if (payload.padAlt is not None and payload.padAlt > 0) else payload.altitude
    pad_temp = payload.padTemp if payload.padTemp is not None else payload.temp
    pad_press = payload.padPress if payload.padPress is not None else 1013.25

    d_alt = payload.altitude - pad_alt
    d_temp = payload.temp - pad_temp
    d_press = payload.pressure - pad_press

    # Normalize altitude & battery for model features (trained on 1S LiPo and relative sounding heights)
    ml_alt = max(0.0, d_alt) if abs(d_alt) < 2500.0 else payload.altitude
    ml_battery = min(4.20, max(3.30, payload.batteryVoltage)) if payload.batteryVoltage <= 4.30 else 3.85
    ml_press = 1013.25 * math.pow(max(0.1, 1.0 - (0.0065 * ml_alt) / 288.15), 5.255)

    feature_dict = {
        'altitude': [ml_alt],
        'vSpd': [v_spd],
        'pressure': [ml_press],
        'temp': [payload.temp],
        'humidity': [payload.humidity],
        'ax': [payload.ax],
        'ay': [payload.ay],
        'az': [payload.az],
        'accelMag': [accel_mag],
        'gx': [payload.gx],
        'gy': [payload.gy],
        'gz': [payload.gz],
        'gyroMag': [gyro_mag],
        'batteryVoltage': [ml_battery],
        'dAlt_pad': [d_alt],
        'dTemp_pad': [d_temp],
        'dPress_pad': [d_press]
    }

    feature_names = phase_classifier['feature_names']
    input_df = pd.DataFrame(feature_dict)[feature_names]

    # 1. Flight Phase Classifier Prediction (Random Forest)
    pipeline = phase_classifier['pipeline']
    predicted_phase = str(pipeline.predict(input_df)[0])
    probabilities = pipeline.predict_proba(input_df)[0]
    classes = phase_classifier['classes']
    prob_dict = {str(c): float(round(p, 4)) for c, p in zip(classes, probabilities)}

    # 2. Anomaly Detection (PyOD IForest)
    anom_scaler = anomaly_detector['scaler']
    anom_model = anomaly_detector['model']
    input_scaled = anom_scaler.transform(input_df)
    raw_anom_score = float(anom_model.decision_function(input_scaled)[0])
    
    score_min = anomaly_detector['score_min']
    score_max = anomaly_detector['score_max']
    normalized_anom_score = max(0.0, min(1.0, (raw_anom_score - score_min) / (score_max - score_min + 1e-9)))

    # Identify specific outlier heuristic category if elevated
    anomaly_type = "NOMINAL"
    is_anomaly = False

    if normalized_anom_score > 0.65 or raw_anom_score > 0.15:
        is_anomaly = True
        if gyro_mag > 120.0:
            anomaly_type = "GYRO_TUMBLE"
        elif accel_mag > 4.0:
            anomaly_type = "HIGH_G_SHOCK"
        elif payload.batteryVoltage < 3.55:
            anomaly_type = "VOLTAGE_SAG"
        elif predicted_phase == "PARACHUTE_DESCENT" and v_spd < -11.0:
            anomaly_type = "BALLISTIC_DESCENT"
        elif accel_mag < 0.20 and predicted_phase == "PARACHUTE_DESCENT":
            anomaly_type = "FREEFALL_ANOMALY"
        else:
            anomaly_type = "OUT_OF_ENVELOPE"

    # 3. Apogee Regressor
    predicted_apogee = payload.altitude
    if apogee_regressor is not None:
        try:
            reg_pipeline = apogee_regressor['pipeline']
            reg_pred = float(reg_pipeline.predict(input_df)[0])
            predicted_apogee = max(payload.altitude, reg_pred)
        except Exception:
            predicted_apogee = payload.altitude

    # 4. Thermodynamic Sounding
    dew_point, air_density, lapse_rate = compute_physics_soundings(
        payload.temp, payload.pressure, payload.humidity, payload.altitude, pad_alt, pad_temp
    )

    # 5. Non-blocking Stream to Telemetry Pipeline (Redpanda / TimescaleDB / MinIO)
    try:
        pipeline_bridge.publish_telemetry({
            "temp": payload.temp,
            "pressure": payload.pressure,
            "altitude": payload.altitude,
            "ax": payload.ax, "ay": payload.ay, "az": payload.az,
            "gx": payload.gx, "gy": payload.gy, "gz": payload.gz,
            "lat": payload.lat, "lon": payload.lon,
            "humidity": payload.humidity,
            "batteryVoltage": payload.batteryVoltage,
            "vSpd": v_spd,
            "flight_phase": predicted_phase,
            "anomaly_score": normalized_anom_score,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "dew_point": dew_point,
            "air_density": air_density,
            "lapse_rate": lapse_rate
        })
        if is_anomaly and anomaly_type != "NOMINAL":
            pipeline_bridge.publish_event(
                event_type=f"AI_ANOMALY_{anomaly_type}",
                severity="WARNING",
                description=f"Cognitive AI Alert: {anomaly_type} detected at alt {payload.altitude:.1f}m",
                metric_value=normalized_anom_score
            )
    except Exception:
        pass

    return {
        "status": "success",
        "predicted_phase": predicted_phase,
        "phase_confidence": float(round(prob_dict.get(predicted_phase, 1.0), 4)),
        "phase_probabilities": prob_dict,
        "anomaly_score": float(round(normalized_anom_score, 4)),
        "raw_anomaly_score": float(round(raw_anom_score, 4)),
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type,
        "predicted_apogee_m": float(round(predicted_apogee, 2)),
        "dew_point_c": float(round(dew_point, 2)),
        "air_density_kg_m3": float(round(air_density, 4)),
        "lapse_rate_c_100m": float(round(lapse_rate, 2))
    }

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/index.html")
@app.get("/home.html")
def serve_index_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/tinyml.html")
def serve_tinyml_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "tinyml.html"))

@app.get("/dashboard.html")
def serve_dashboard_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/models.html")
@app.get("/models")
def serve_models_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "models.html"))

@app.get("/analysis.html")
@app.get("/analysis")
def serve_analysis_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "analysis.html"))

@app.get("/results.html")
def serve_results_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "results.html"))

@app.get("/pitch.html")
@app.get("/pitch")
def serve_pitch_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "pitch.html"))

@app.get("/api/artifacts/pitch-deck")
def download_pitch_deck_pptx():
    """Download the 12-slide Executive & Judge PowerPoint Pitch Deck (.pptx)."""
    pptx_path = os.path.join(BASE_DIR, "reports", "Cognitive_CanSat_Pitch_Deck.pptx")
    if not os.path.exists(pptx_path):
        raise HTTPException(status_code=404, detail="Pitch deck PPTX not found")
    return FileResponse(
        path=pptx_path,
        filename="Cognitive_CanSat_Pitch_Deck.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

@app.get("/api/artifacts/ieee-paper")
def download_ieee_paper_tex():
    """Download the complete compilable IEEEtran conference LaTeX manuscript (.tex)."""
    tex_path = os.path.join(BASE_DIR, "paper", "ieee_cansat_paper.tex")
    if not os.path.exists(tex_path):
        raise HTTPException(status_code=404, detail="IEEE LaTeX paper not found")
    return FileResponse(
        path=tex_path,
        filename="ieee_cansat_paper.tex",
        media_type="application/x-tex"
    )


css_dir = os.path.join(FRONTEND_DIR, "css")
if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")

js_dir = os.path.join(FRONTEND_DIR, "js")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")


test_cases_dir = os.path.join(BASE_DIR, "test_cases")
if os.path.exists(test_cases_dir):
    app.mount("/test_cases", StaticFiles(directory=test_cases_dir), name="test_cases")

reports_dir = os.path.join(BASE_DIR, "reports")
if os.path.exists(reports_dir):
    app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")

tinyml_videos_dir = os.path.join(BASE_DIR, "tinyml_test_videos")
if os.path.exists(tinyml_videos_dir):
    app.mount("/tinyml_test_videos", StaticFiles(directory=tinyml_videos_dir), name="tinyml_test_videos")

@app.get("/api/tinyml/sample-videos")
def get_tinyml_sample_videos():
    """Returns curated flight test video presets categorized by terrain hazard profile."""
    return [
        {
            "id": "farmland",
            "title": "01 Farmland & Pasture (Nominal LZ)",
            "category": "01_farmland_and_pasture",
            "filename": "aerial_hemp_field_descent.webm",
            "url": "/tinyml_test_videos/01_farmland_and_pasture/aerial_hemp_field_descent.webm",
            "expected_class": "SAFE_LZ",
            "desc": "Overhead descent over green crops, pasture, and dirt trails with high vegetative index (VARI > +0.15)."
        },
        {
            "id": "urban",
            "title": "02 Village Roads & Buildings (Hazard)",
            "category": "02_urban_roads_and_buildings",
            "filename": "aerial_village_roads_and_rooftops.webm",
            "url": "/tinyml_test_videos/02_urban_roads_and_buildings/aerial_village_roads_and_rooftops.webm",
            "expected_class": "CRITICAL_HAZARD",
            "desc": "Overhead flight above buildings, commercial rooftops, asphalt road, and parking area with structural shadows."
        },
        {
            "id": "river",
            "title": "03 River & Dense Canopy (Water/Canopy)",
            "category": "03_water_hazards_and_canopy",
            "filename": "aerial_beaverhead_river_canopy.webm",
            "url": "/tinyml_test_videos/03_water_hazards_and_canopy/aerial_beaverhead_river_canopy.webm",
            "expected_class": "WATER_HAZARD",
            "desc": "Aerial drone flight tracking a winding river surrounded by dense tree and shrub thickets."
        },
        {
            "id": "coastline",
            "title": "04 Coastline & Ocean Surf (Immersion)",
            "category": "03_water_hazards_and_canopy",
            "filename": "aerial_rocky_coastline_waves.mp4",
            "url": "/tinyml_test_videos/03_water_hazards_and_canopy/aerial_rocky_coastline_waves.mp4",
            "expected_class": "WATER_HAZARD",
            "desc": "Vertical nadir view of breaking ocean surf and coastal rock shelves."
        }
    ]



# -----------------------------------------------------------------------------
# Post-Flight Telemetry & Sensor Suite Ablation API Endpoints
# -----------------------------------------------------------------------------
class AblationRunRequest(BaseModel):
    scenario: str = Field(default="01_nominal_sounding_flight")
    feature_set: str = Field(default="Full_Suite")
    dataset_mode: str = Field(default="testing")

@app.get("/api/analysis/reports-zip")
def download_reports_zip():
    """Packages all 10 verified PDF flight reports and all_missions_summary.csv into a ZIP."""
    pdf_dir = os.path.join(BASE_DIR, "reports", "pdf")
    summary_csv = os.path.join(BASE_DIR, "reports", "all_missions_summary.csv")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(summary_csv):
            zf.write(summary_csv, arcname="all_missions_summary.csv")
        if os.path.exists(pdf_dir):
            for fname in sorted(os.listdir(pdf_dir)):
                if fname.endswith(".pdf"):
                    zf.write(os.path.join(pdf_dir, fname), arcname=os.path.join("pdf_reports", fname))
    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=Cognitive_CanSat_Flight_Reports.zip"}
    )

_CACHE_ABLATION: Optional[Dict[str, Any]] = None
_CACHE_SCENARIO_TELEMETRY: Dict[str, Dict[str, Any]] = {}
_CACHE_SCENARIO_QUALITY: Dict[str, Dict[str, Any]] = {}
_CACHE_VISION_COMPARISON: Optional[Dict[str, Any]] = None

def _load_ablation_cached() -> Optional[Dict[str, Any]]:
    global _CACHE_ABLATION
    if _CACHE_ABLATION is not None:
        return _CACHE_ABLATION
    ablation_file = os.path.join(BASE_DIR, "ml", "ablation_benchmarks.json")
    if os.path.exists(ablation_file):
        with open(ablation_file, "r", encoding="utf-8") as f:
            _CACHE_ABLATION = json.load(f)
        return _CACHE_ABLATION
    return None

@app.get("/api/analysis/ablation-data")
def get_ablation_benchmarks():
    """Return precomputed sensor suite ablation benchmarks for training and testing data."""
    try:
        data = _load_ablation_cached()
        if data is not None:
            return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Ablation data not found")

@app.get("/api/analysis/scenarios")
def list_flight_scenarios():
    """Return list of all 10 flight scenarios and key summary metrics."""
    summary_path = os.path.join(BASE_DIR, "reports", "all_missions_summary.csv")
    if os.path.exists(summary_path):
        try:
            df = pd.read_csv(summary_path)
            return {"status": "success", "scenarios": df.to_dict(orient="records")}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "error", "message": "Summary CSV not found"}

@app.get("/api/analysis/scenario/{scenario_name}")
def get_scenario_telemetry(scenario_name: str):
    """Return time-series telemetry and calculated kinematics for interactive graphing."""
    clean_name, csv_path = _resolve_safe_scenario_csv(scenario_name)
    if clean_name in _CACHE_SCENARIO_TELEMETRY:
        return _CACHE_SCENARIO_TELEMETRY[clean_name]

    try:
        df = pd.read_csv(csv_path).bfill().ffill()
        n = len(df)
        dt = 0.8
        time_arr = (np.arange(n) * dt).tolist()

        from scipy.signal import savgol_filter
        alt_raw = df['altitude'].values
        if n >= 7:
            w = min(11, n // 2 * 2 + 1)
            p = min(3, w - 2)
            alt_smooth = savgol_filter(alt_raw, w, p)
        else:
            alt_smooth = alt_raw

        vel = np.gradient(alt_smooth, dt)
        accel_mag = (np.sqrt(df['ax']**2 + df['ay']**2 + df['az']**2)).values if {'ax', 'ay', 'az'}.issubset(df.columns) else np.ones(n)

        p0 = 1013.25
        p = np.clip(df['pressure'].values, 10.0, 1500.0)
        t_k = df['temp'].values + 273.15
        pot_temp = t_k * (p0 / p) ** 0.286 - 273.15

        stride = max(1, n // 200)
        indices = list(range(0, n, stride))
        if (n - 1) not in indices:
            indices.append(n - 1)

        result = {
            "status": "success",
            "scenario": clean_name,
            "total_samples": n,
            "time": [round(float(time_arr[i]), 1) for i in indices],
            "altitude_raw": [round(float(alt_raw[i]), 1) for i in indices],
            "altitude_smoothed": [round(float(alt_smooth[i]), 1) for i in indices],
            "velocity": [round(float(vel[i]), 2) for i in indices],
            "accel_mag": [round(float(accel_mag[i]), 2) for i in indices],
            "temp": [round(float(df['temp'].iloc[i]), 1) for i in indices],
            "pressure": [round(float(df['pressure'].iloc[i]), 1) for i in indices],
            "potential_temp": [round(float(pot_temp[i]), 1) for i in indices],
            "kpis": {
                "max_altitude_m": round(float(np.max(alt_smooth)), 1),
                "time_to_apogee_s": round(float(time_arr[int(np.argmax(alt_smooth))]), 1),
                "max_ascent_vel_mps": round(float(np.max(vel)), 1),
                "avg_descent_vel_mps": round(float(np.mean(vel[vel < 0])), 1) if np.any(vel < 0) else 0.0,
                "peak_g_shock": round(float(np.max(accel_mag)), 2),
                "touchdown_impact_g": round(float(accel_mag[-1]), 2)
            }
        }
        _CACHE_SCENARIO_TELEMETRY[clean_name] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analysis/run-ablation")
def run_live_ablation(req: AblationRunRequest):
    """Simulates live model ablation / sensor dropout on selected scenario testing data."""
    data = _load_ablation_cached()
    if data is not None:
        mode = req.dataset_mode if req.dataset_mode in ["training", "testing"] else "testing"
        records = [r for r in data[mode] if r["scenario"] == req.scenario.replace(".csv", "")]
        selected = next((r for r in records if r["feature_set"] == req.feature_set), None)
        return {
            "status": "success",
            "scenario": req.scenario,
            "feature_set": req.feature_set,
            "dataset_mode": mode,
            "result": selected,
            "all_suites_for_scenario": records,
            "module_impact": data.get("module_impact", {})
        }
    raise HTTPException(status_code=404, detail="Ablation data unavailable")

# -----------------------------------------------------------------------------
# Telemetry Data Quality & Flight Reliability Analysis API
# -----------------------------------------------------------------------------
class TelemetryQualityRequest(BaseModel):
    csv_content: str = Field(..., description="Raw CSV string content of flight telemetry")
    nominal_interval_sec: Optional[float] = Field(0.8, description="Expected sampling interval in seconds")
    gap_threshold_sec: Optional[float] = Field(2.0, description="Outage duration threshold in seconds")

@app.get("/api/analysis/quality/{scenario_name}")
def get_scenario_quality(scenario_name: str, nominal_dt: float = 0.8, gap_threshold: float = 2.0):
    """Analyze telemetry data quality, packet completeness, and temporal reliability for a scenario."""
    clean_name, csv_path = _resolve_safe_scenario_csv(scenario_name)
    cache_key = f"{clean_name}:{nominal_dt}:{gap_threshold}"
    if cache_key in _CACHE_SCENARIO_QUALITY:
        return _CACHE_SCENARIO_QUALITY[cache_key]

    analyzer = TelemetryQualityAnalyzer(nominal_interval_sec=nominal_dt, gap_threshold_sec=gap_threshold)
    report = analyzer.analyze_file(csv_path)
    data = report.to_dict()
    data["scenario"] = clean_name
    _CACHE_SCENARIO_QUALITY[cache_key] = data
    return data

@app.post("/api/analysis/quality/analyze-csv")
def analyze_custom_csv_quality(req: TelemetryQualityRequest):
    """Analyze data quality and integrity on custom uploaded flight CSV content."""
    if len(req.csv_content) > 10_000_000:
        raise HTTPException(status_code=413, detail="CSV payload exceeds 10 MB maximum limit")
    analyzer = TelemetryQualityAnalyzer(
        nominal_interval_sec=req.nominal_interval_sec or 0.8,
        gap_threshold_sec=req.gap_threshold_sec or 2.0
    )
    report = analyzer.analyze_csv_string(req.csv_content)
    return report.to_dict()

# -----------------------------------------------------------------------------
# Mission Database & Post-Flight Review (PFR) Persistence API
# -----------------------------------------------------------------------------
class MissionStartRequest(BaseModel):
    name: str = Field(default="Live Flight Test", description="Human-readable mission name")
    callsign: str = Field(default="CANSAT-1", description="Vehicle radio callsign")
    operator: str = Field(default="Flight Controller", description="Operator callsign / name")
    notes: Optional[str] = Field(None, description="Pre-flight briefing or weather notes")
    mission_id: Optional[str] = Field(None, description="Custom mission ID")

class TelemetryBatchRequest(BaseModel):
    mission_id: str
    records: List[Dict[str, Any]]

class MissionFinishRequest(BaseModel):
    pad_baseline_alt: Optional[float] = None

class EventLogPayload(BaseModel):
    timestamp_ms: int
    event_type: str
    severity: str = "INFO"
    description: str

@app.post("/api/db/missions/start")
def start_db_mission(req: MissionStartRequest):
    """Arm and create a new mission session in SQLite."""
    try:
        mission = database.create_mission(
            name=req.name,
            callsign=req.callsign,
            operator=req.operator,
            notes=req.notes,
            mission_id=req.mission_id
        )
        return {"status": "success", "mission_id": mission["id"], "mission": mission}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/missions/telemetry")
def ingest_mission_telemetry(req: TelemetryBatchRequest):
    """Ingest a batch of telemetry packets into database for the specified mission."""
    try:
        count = database.insert_telemetry_batch(req.mission_id, req.records)
        # Asynchronously mirror batch to the distributed telemetry pipeline
        try:
            for rec in req.records:
                pipeline_bridge.publish_telemetry(rec, mission_id=req.mission_id)
        except Exception:
            pass
        return {"status": "success", "mission_id": req.mission_id, "inserted": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/missions/{mission_id}/events")
def log_mission_event(mission_id: str, payload: EventLogPayload):
    """Log an operational event or anomaly during a mission."""
    try:
        event_id = database.insert_event(
            mission_id=mission_id,
            timestamp_ms=payload.timestamp_ms,
            event_type=payload.event_type,
            severity=payload.severity,
            description=payload.description
        )
        try:
            pipeline_bridge.publish_event(
                event_type=payload.event_type,
                severity=payload.severity,
                description=payload.description,
                mission_id=mission_id
            )
        except Exception:
            pass
        return {"status": "success", "event_id": event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/missions/{mission_id}/finish")
def finish_db_mission(mission_id: str, req: Optional[MissionFinishRequest] = None):
    """Finalize a mission, run SQL aggregations, and generate/store the PFR audit report."""
    try:
        pad_alt = req.pad_baseline_alt if req else None
        report = database.finalize_mission(mission_id)
        return {"status": "success", "mission_id": mission_id, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/missions")
def list_db_missions():
    """List all stored missions with duration, apogee, and report status."""
    try:
        missions = database.list_missions()
        return {"status": "success", "missions": missions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/missions/{mission_id}")
def get_db_mission(mission_id: str):
    """Retrieve metadata for a single mission."""
    mission = database.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"status": "success", "mission": mission}

@app.get("/api/db/missions/{mission_id}/report")
def get_db_mission_report(mission_id: str):
    """Retrieve the stored Post-Flight Review (PFR) audit report for a mission."""
    report = database.get_mission_report(mission_id)
    if not report:
        try:
            report = database.generate_and_save_pfr_report(mission_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Report not found for this mission")
    return {"status": "success", "report": report.get("parsed_json", report), "raw": report}

@app.get("/api/db/missions/{mission_id}/telemetry")
def get_db_mission_telemetry(mission_id: str, limit: Optional[int] = None):
    """Retrieve time-series telemetry records for historic replay and charting."""
    records = database.get_mission_telemetry(mission_id, limit=limit)
    return {"status": "success", "mission_id": mission_id, "count": len(records), "records": records, "telemetry": records}

@app.delete("/api/db/missions/{mission_id}")
def delete_db_mission(mission_id: str):
    """Delete a mission and all associated records and reports."""
    deleted = database.delete_mission(mission_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"status": "success", "deleted": True, "deleted_mission_id": mission_id}

@app.delete("/api/db/missions")
def purge_all_db_missions():
    """Purge all recorded flight missions, resetting telemetry, reports, and events."""
    try:
        deleted_count = database.purge_all_missions()
        return {"status": "success", "deleted_missions": deleted_count, "purged": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/stats")
def get_db_stats():
    """Retrieve overall SQLite database storage metrics, row counts, and health."""
    try:
        stats = database.get_database_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/db/download")
def download_sqlite_database():
    """Download the raw SQLite database file (cansat_missions.db) for external analysis."""
    db_path = database.DEFAULT_DB_PATH
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found on disk")
    return FileResponse(
        path=db_path,
        filename="cansat_missions.db",
        media_type="application/x-sqlite3"
    )

@app.get("/api/db/missions/{mission_id}/export/csv")
def export_mission_telemetry_csv(mission_id: str):
    """Download standard CanSat CSV formatted telemetry for the specified mission."""
    csv_content = database.export_mission_csv(mission_id)
    if not csv_content:
        raise HTTPException(status_code=404, detail="No telemetry records found for this mission")
    safe_id = _sanitize_filename_token(mission_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={safe_id}_telemetry.csv"
        }
    )

@app.get("/api/latest_telemetry")
def get_latest_telemetry():
    return {
        "status": "success",
        "count": len(live_telemetry_history),
        "packets": list(live_telemetry_history)
    }

@app.get("/api/health")
def get_health():
    db_ok = os.path.exists(database.DEFAULT_DB_PATH)
    vision_ok = (tinylandingnet_model is not None and vision_guard is not None)
    return {
        "status": "online" if models_loaded else "degraded",
        "version": "2.0.0",
        "models_loaded": models_loaded,
        "vision_models_loaded": vision_ok,
        "database_ready": db_ok,
        "security_headers_enabled": True,
        "timestamp": time.time()
    }

@app.get("/api/models/info")
def get_models_info():
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Models not loaded")
    return {
        "models": {
            "flight_phase_classifier": {
                "type": "RandomForestClassifier",
                "features": phase_classifier['feature_names'],
                "classes": phase_classifier['classes'],
                "metrics": model_metrics.get("flight_phase_classifier", {})
            },
            "anomaly_detector": {
                "type": "PyOD.IForest",
                "metrics": model_metrics.get("anomaly_detector", {})
            },
            "apogee_regressor": {
                "type": "GradientBoostingRegressor",
                "metrics": model_metrics.get("apogee_regressor", {})
            }
        }
    }

@app.post("/api/predict")
def predict_telemetry(payload: TelemetryPayload):
    return run_ml_inference(payload)

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected to live ML telemetry stream.")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                payload = TelemetryPayload(**msg)
                result = run_ml_inference(payload)
                await websocket.send_json(result)
            except Exception as parse_err:
                await websocket.send_json({"status": "error", "message": str(parse_err)})
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")

# --- REAL-TIME DUAL-PORT HARDWARE SERIAL BRIDGE & PYTHON CORE ENGINES ---
import asyncio
import threading
from backend.core.serial_manager import DualSerialManager, list_available_ports
from backend.core.kinematics import KinematicsEngine, KinematicState
from backend.core.atmospheric import AtmosphericEngine, AtmosphericSounding

serial_subscribers: List[WebSocket] = []
subscribers_lock = threading.Lock()

# Core computation engines
kinematics_engine = KinematicsEngine()
atmospheric_engine = AtmosphericEngine()

# Thread-safe cache of latest processed states
latest_kinematic_state: Optional[KinematicState] = None
latest_sounding_state: Optional[AtmosphericSounding] = None
state_lock = threading.Lock()

async def broadcast_serial_line(line: str):
    with subscribers_lock:
        targets = list(serial_subscribers)
    for ws in targets:
        try:
            await ws.send_text(line)
        except Exception:
            pass

def on_serial_line_dispatcher(label: str, line: str, loop: asyncio.AbstractEventLoop):
    # Broadcast raw line directly to all active WebSocket clients (index.html HUD)
    asyncio.run_coroutine_threadsafe(broadcast_serial_line(line), loop)

def on_telemetry_csv_processor(line: str):
    """Process incoming 13-field (or 14-field) CSV through Kinematics and Atmospheric engines."""
    global latest_kinematic_state, latest_sounding_state
    try:
        parts = [float(x.strip()) for x in line.split(",")]
        if len(parts) >= 13:
            temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, volt = parts[:13]
            kin_state = kinematics_engine.process_packet(
                alt, ax, ay, az, gx, gy, gz,
                pressure=press, temp=temp, humidity=hum
            )
            atmo_state = atmospheric_engine.process_sounding(press, temp, hum, alt)
            with state_lock:
                latest_kinematic_state = kin_state
                latest_sounding_state = atmo_state
            live_telemetry_history.append({
                "time": time.time(),
                "temp": temp,
                "pressure": press,
                "altitude": alt,
                "calibrated_altitude": kin_state.calibrated_altitude if kin_state else alt,
                "ax": ax, "ay": ay, "az": az,
                "gx": gx, "gy": gy, "gz": gz,
                "lat": lat, "lon": lon,
                "humidity": hum,
                "batteryVoltage": volt,
                "vSpd": kin_state.vertical_speed if kin_state else 0.0,
                "calibrated_vspd": kin_state.calibrated_vspd if kin_state else 0.0,
            })
            # Stream enriched packet to telemetry data lakehouse
            try:
                pipeline_bridge.publish_telemetry({
                    "time": time.time(),
                    "temp": temp,
                    "pressure": press,
                    "altitude": alt,
                    "calibrated_altitude": kin_state.calibrated_altitude if kin_state else alt,
                    "ax": ax, "ay": ay, "az": az,
                    "gx": gx, "gy": gy, "gz": gz,
                    "lat": lat, "lon": lon,
                    "humidity": hum,
                    "batteryVoltage": volt,
                    "vSpd": kin_state.vertical_speed if kin_state else 0.0,
                    "calibrated_vspd": kin_state.calibrated_vspd if kin_state else 0.0,
                    "pitch": kin_state.pitch if kin_state else 0.0,
                    "roll": kin_state.roll if kin_state else 0.0,
                    "dew_point": atmo_state.dew_point_c if atmo_state else None,
                    "air_density": atmo_state.air_density_kg_m3 if atmo_state else None,
                    "lapse_rate": atmo_state.lapse_rate_c_100m if atmo_state else None,
                })
            except Exception:
                pass
    except Exception:
        pass

# Global serial manager instance
dual_serial_manager: Optional[DualSerialManager] = None

class HardwareConfigRequest(BaseModel):
    telemetry_port: Optional[str] = None
    telemetry_baud: Optional[int] = None
    video_port: Optional[str] = None
    video_baud: Optional[int] = None

def get_or_create_serial_manager(loop: asyncio.AbstractEventLoop) -> DualSerialManager:
    global dual_serial_manager
    if dual_serial_manager is None:
        telemetry_port = os.environ.get("CANSAT_TELEMETRY_PORT", "COM4")
        telemetry_baud = int(os.environ.get("CANSAT_TELEMETRY_BAUD", "9600"))
        video_port = os.environ.get("CANSAT_VIDEO_PORT", "COM5")
        video_baud = int(os.environ.get("CANSAT_VIDEO_BAUD", "460800"))
        dual_serial_manager = DualSerialManager(
            telemetry_port=telemetry_port,
            telemetry_baud=telemetry_baud,
            video_port=video_port,
            video_baud=video_baud,
            on_line_received=lambda label, line: on_serial_line_dispatcher(label, line, loop),
            on_telemetry_csv=on_telemetry_csv_processor,
        )
    return dual_serial_manager

def _get_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

@app.get("/hardware/ports")
def get_hardware_ports():
    """Enumerate all serial ports on the host system."""
    return {"ports": list_available_ports()}

@app.get("/hardware/config")
def get_hardware_config():
    """Return active serial port and baud rate configuration."""
    loop = _get_loop()
    mgr = get_or_create_serial_manager(loop)
    conn_status = mgr.get_connection_status()
    return {
        "status": "success",
        "telemetry": {
            "port": mgr.telemetry_cfg.port,
            "baud_rate": mgr.telemetry_cfg.baud_rate,
            "connected": conn_status.get(mgr.telemetry_cfg.label, False),
        },
        "video": {
            "port": mgr.video_cfg.port,
            "baud_rate": mgr.video_cfg.baud_rate,
            "connected": conn_status.get(mgr.video_cfg.label, False),
        },
        "is_running": mgr.is_running,
        "available_ports": list_available_ports(),
    }

@app.post("/hardware/config")
def set_hardware_config(cfg: HardwareConfigRequest):
    """Reconfigure serial ports and baud rates dynamically at runtime."""
    loop = _get_loop()
    mgr = get_or_create_serial_manager(loop)
    mgr.reconfigure(
        telemetry_port=cfg.telemetry_port,
        telemetry_baud=cfg.telemetry_baud,
        video_port=cfg.video_port,
        video_baud=cfg.video_baud,
    )
    conn_status = mgr.get_connection_status()
    return {
        "status": "reconfigured",
        "telemetry_port": mgr.telemetry_cfg.port,
        "telemetry_baud": mgr.telemetry_cfg.baud_rate,
        "telemetry_connected": conn_status.get(mgr.telemetry_cfg.label, False),
        "video_port": mgr.video_cfg.port,
        "video_baud": mgr.video_cfg.baud_rate,
        "video_connected": conn_status.get(mgr.video_cfg.label, False),
    }

@app.get("/analytics/kinematics")
def get_latest_kinematics():
    """Return latest real-time Kinematics state (Kalman altitude, attitude, alarms)."""
    with state_lock:
        if latest_kinematic_state is None:
            return {"status": "waiting_for_data"}
        return {"status": "active", "data": latest_kinematic_state.__dict__}

@app.get("/analytics/sounding")
def get_latest_sounding():
    """Return latest Atmospheric Thermodynamics state (dew point, air density, ELR)."""
    with state_lock:
        if latest_sounding_state is None:
            return {"status": "waiting_for_data"}
        return {"status": "active", "data": latest_sounding_state.__dict__}

@app.post("/hardware/tare")
def trigger_hardware_tare(samples: int = 15):
    """Trigger stationary pad tare calibration across baro and IMU sensors."""
    kinematics_engine.start_tare(num_samples=samples)
    return {
        "status": "taring_started",
        "samples_target": samples,
        "is_taring": kinematics_engine.is_taring
    }

@app.get("/hardware/tare")
def get_hardware_tare_status():
    """Get current tare calibration state."""
    return {
        "status": "success",
        "is_calibrated": kinematics_engine.tare.is_calibrated,
        "is_taring": kinematics_engine.is_taring,
        "samples_count": kinematics_engine.tare.samples_count,
        "tare": {
            "gyro_bias_x": round(kinematics_engine.tare.gyro_bias_x, 3),
            "gyro_bias_y": round(kinematics_engine.tare.gyro_bias_y, 3),
            "gyro_bias_z": round(kinematics_engine.tare.gyro_bias_z, 3),
            "pad_altitude": round(kinematics_engine.tare.pad_altitude, 2),
            "tare_pitch": round(kinematics_engine.tare.tare_pitch, 2),
            "tare_roll": round(kinematics_engine.tare.tare_roll, 2),
        }
    }

@app.websocket("/ws/serial")
async def websocket_serial_bridge(websocket: WebSocket):
    await websocket.accept()
    with subscribers_lock:
        serial_subscribers.append(websocket)
        count = len(serial_subscribers)
    print(f"[WebSocket] Serial bridge client connected. (Total subscribers: {count})")
    
    loop = asyncio.get_running_loop()
    manager = get_or_create_serial_manager(loop)
    if not manager.is_running:
        manager.start()

    # Send initial hardware link status to HUD
    init_msg = (
        f"# [HARDWARE] Active dual bridge: Telemetry ({manager.telemetry_cfg.port} @ "
        f"{manager.telemetry_cfg.baud_rate} baud) | Video ({manager.video_cfg.port} @ "
        f"{manager.video_cfg.baud_rate} baud)"
    )
    await websocket.send_text(init_msg)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        with subscribers_lock:
            if websocket in serial_subscribers:
                serial_subscribers.remove(websocket)
            remaining = len(serial_subscribers)
        if remaining == 0:
            manager.stop()


# -----------------------------------------------------------------------------
# Distributed Telemetry Pipeline (Redpanda / TimescaleDB / MinIO / Grafana) API
# -----------------------------------------------------------------------------
class PipelineConfigRequest(BaseModel):
    broker: Optional[str] = None
    enabled: Optional[bool] = None

class ScenarioStreamRequest(BaseModel):
    scenario: str = Field(default="01_nominal_sounding_flight")
    rate_hz: float = Field(default=10.0, ge=0.5, le=100.0)
    mission_id: Optional[str] = None

@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Return status of the Redpanda message broker, TimescaleDB, and MinIO lakehouse."""
    status = pipeline_bridge.get_status()
    timescale_online = False
    try:
        import psycopg
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "telemetry_db")
        db_user = os.environ.get("DB_USER", "cansat_admin")
        db_pass = os.environ.get("DB_PASS", "cansat_password")
        with psycopg.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_pass, connect_timeout=1) as conn:
            timescale_online = True
    except Exception:
        timescale_online = False

    status["timescaledb_online"] = timescale_online
    status["grafana_url"] = "http://localhost:3000"
    status["minio_console_url"] = "http://localhost:9001"
    return {"status": "success", "pipeline": status}

@app.post("/api/pipeline/config")
def update_pipeline_config(req: PipelineConfigRequest):
    """Update pipeline broker URL or enable/disable live streaming."""
    pipeline_bridge.reconfigure(broker=req.broker, enabled=req.enabled)
    return {"status": "success", "pipeline": pipeline_bridge.get_status()}

@app.post("/api/pipeline/stream-scenario")
def trigger_scenario_pipeline_stream(req: ScenarioStreamRequest):
    """
    Stream any of the 10 flight scenario CSVs through the pipeline in real-time.
    Runs asynchronously in a background thread.
    """
    clean_name, csv_path = _resolve_safe_scenario_csv(req.scenario)

    m_id = req.mission_id or f"SIM_{clean_name.upper()}"

    def _worker():
        try:
            df = pd.read_csv(csv_path)
            dt = 1.0 / req.rate_hz
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                row_dict["mission_id"] = m_id
                row_dict["packet_id"] = idx + 1
                pipeline_bridge.publish_telemetry(row_dict, mission_id=m_id)
                time.sleep(dt)
        except Exception as e:
            print(f"[Pipeline] Error streaming scenario to pipeline: {e}")

    th = threading.Thread(target=_worker, name=f"ScenarioStreamer-{clean_name}", daemon=True)
    th.start()
    return {
        "status": "started",
        "scenario": clean_name,
        "mission_id": m_id,
        "rate_hz": req.rate_hz,
        "message": f"Streaming {clean_name} to topic {pipeline_bridge.telemetry_topic} @ {req.rate_hz} Hz"
    }

@app.get("/api/pipeline/timescale-summary")
def get_timescale_summary(limit: int = 20):
    """Query recent rows and continuous aggregates from TimescaleDB hot path."""
    try:
        import psycopg
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "telemetry_db")
        db_user = os.environ.get("DB_USER", "cansat_admin")
        db_pass = os.environ.get("DB_PASS", "cansat_password")
        with psycopg.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_pass, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT time, mission_id, packet_id, altitude_m, velocity_mps, accel_z_g, battery_v, flight_stage, status, anomaly_score
                    FROM raw_telemetry
                    ORDER BY time DESC
                    LIMIT %s;
                """, (limit,))
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                telemetry = [dict(zip(cols, [(r.isoformat() if hasattr(r, 'isoformat') else r) for r in row])) for row in rows]

                cur.execute("""
                    SELECT time, mission_id, event_type, severity, description, metric_value
                    FROM flight_events
                    ORDER BY time DESC
                    LIMIT 10;
                """)
                ev_rows = cur.fetchall()
                ev_cols = [desc[0] for desc in cur.description]
                events = [dict(zip(ev_cols, [(r.isoformat() if hasattr(r, 'isoformat') else r) for r in row])) for row in ev_rows]

                return {
                    "status": "online",
                    "telemetry_count": len(telemetry),
                    "telemetry": telemetry,
                    "recent_events": events
                }
    except Exception as e:
        return {
            "status": "offline",
            "message": f"TimescaleDB connection failed: {str(e)}",
            "telemetry": [],
            "recent_events": []
        }

# -----------------------------------------------------------------------------
# TinyML & Safe Landing AI (SLAI) Aerial Vision Inference API
# -----------------------------------------------------------------------------
_VISION_PREPROCESS_64 = None
_VISION_PREPROCESS_224 = None

def _get_vision_preprocessors():
    global _VISION_PREPROCESS_64, _VISION_PREPROCESS_224
    if _VISION_PREPROCESS_64 is None or _VISION_PREPROCESS_224 is None:
        from torchvision import transforms
        norm = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        _VISION_PREPROCESS_64 = transforms.Compose([transforms.Resize((64, 64)), transforms.ToTensor(), norm])
        _VISION_PREPROCESS_224 = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), norm])
    return _VISION_PREPROCESS_64, _VISION_PREPROCESS_224

class VisionFrameRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded JPEG/PNG frame or data URL")
    model_tier: Optional[str] = Field("tinylandingnet", description="Model architecture: tinylandingnet, mobilenet_v3_small, resnet18, or all")
    run_ood_guard: Optional[bool] = Field(True, description="Enable Out-of-Distribution guard against human faces/indoor scenes")
    bypass_ood_guard: Optional[bool] = Field(False, description="Optional override to bypass OOD guard")

@app.post("/api/vision/classify-frame")
def classify_vision_frame(req: VisionFrameRequest):
    """
    Classify downlinked optical CanSat camera frame with Out-of-Distribution safety guard.
    Supports single tier ('tinylandingnet', 'mobilenet_v3_small', 'resnet18') or 'all' for 3-tier comparison.
    """
    global vision_guard, tinylandingnet_model, mobilenet_v3_small_model, resnet18_model
    if len(req.image_base64) > 15_000_000:
        raise HTTPException(status_code=413, detail="Base64 image payload exceeds 15 MB limit")
    try:
        raw_b64 = req.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if pil_img.width * pil_img.height > 16_777_216:
            pil_img.thumbnail((2048, 2048))
        frame_rgb = np.array(pil_img)
    except HTTPException:
        raise
    except Exception as dec_err:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {dec_err}")

    # 1. Out-of-Distribution Guard Evaluation
    should_guard = (req.run_ood_guard is not False) and (not req.bypass_ood_guard)
    if should_guard and vision_guard is not None:
        guard_res = vision_guard.validate_frame(frame_rgb)
        if not guard_res["is_aerial"]:
            return {
                "status": "rejected",
                "is_aerial": False,
                "rejection_reason": guard_res["rejection_reason"],
                "slai_class": "INVALID_AERIAL_SURFACE",
                "landing_decision": "ABORT_OOD_NON_AERIAL",
                "confidence": 0.0,
                "optimal_lz_valid": False,
                "message": guard_res.get("message", "Non-aerial subject detected; landing zone search suppressed."),
                "guard_metrics": guard_res
            }

    # 2. 3x3 Sector Grid Analysis (computed once per frame)
    h, w, _ = frame_rgb.shape
    cw = max(1, w // 3)
    ch = max(1, h // 3)
    sector_matrix = []
    best_sector = [1, 1]
    best_score = -999.0

    for r in range(3):
        row_scores = []
        for c in range(3):
            tile = frame_rgb[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
            t_r = float(np.mean(tile[:, :, 0]))
            t_g = float(np.mean(tile[:, :, 1]))
            t_b = float(np.mean(tile[:, :, 2]))
            t_denom = t_g + t_r - t_b
            t_vari = (t_g - t_r) / (t_denom if abs(t_denom) > 1e-4 else 1.0)
            if t_b > (t_r + t_g) * 0.65 and t_b > 80:
                score = -1.0
            elif t_vari > 0.08 and t_g > t_r * 1.05:
                score = 1.0 + t_vari
            elif t_vari >= -0.02 and t_g > t_r:
                score = 0.2 + t_vari
            else:
                score = -0.6
            row_scores.append(round(score, 2))
            if score > best_score:
                best_score = score
                best_sector = [r, c]
        sector_matrix.append(row_scores)

    dx = best_sector[1] - 1
    dy = -(best_sector[0] - 1)
    base_evasion_deg = int((math.atan2(dx, dy) * 180.0 / math.pi + 360.0) % 360.0) if (dx != 0 or dy != 0) else None

    # 3. Model Inference
    import torch
    from ml.train_tinyml_vision import SLAI_CLASSES
    prep64, prep224 = _get_vision_preprocessors()

    def _derive_decision(cls_name: str, conf: float):
        ev_deg = base_evasion_deg if cls_name != "SAFE_LZ" else None
        if cls_name == "SAFE_LZ" and conf >= 0.60:
            return "SAFE_TOUCHDOWN_AUTHORIZED", ev_deg
        elif cls_name == "OBSTACLE_CANOPY":
            return (f"ADVISORY_EVASION_{ev_deg}DEG" if ev_deg is not None else "ADVISORY_LATERAL_EVADE"), ev_deg
        else:
            return (f"CRITICAL_EVASION_{ev_deg}DEG" if ev_deg is not None else "CRITICAL_HAZARD_ABORT"), ev_deg

    def _eval_single_model(m_obj, tensor_in, tier_key: str):
        t_start = time.perf_counter()
        if m_obj is not None:
            with torch.inference_mode():
                logits = m_obj(tensor_in)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            prob_map = {SLAI_CLASSES[i]: round(float(probs[i]), 4) for i in range(len(SLAI_CLASSES))}
            top_i = int(np.argmax(probs))
            c_name = SLAI_CLASSES[top_i]
            conf_val = float(probs[top_i])
        else:
            r_m, g_m, b_m = float(np.mean(frame_rgb[:, :, 0])), float(np.mean(frame_rgb[:, :, 1])), float(np.mean(frame_rgb[:, :, 2]))
            denom = g_m + r_m - b_m
            vari = (g_m - r_m) / (denom if abs(denom) > 1e-4 else 1.0)
            if b_m > r_m * 1.08 and b_m > g_m:
                c_name = "WATER_HAZARD"
            elif vari > 0.06:
                c_name = "SAFE_LZ"
            elif vari >= -0.02:
                c_name = "OBSTACLE_CANOPY"
            else:
                c_name = "CRITICAL_HAZARD"
            conf_val = 0.82
            prob_map = {cls_n: (0.82 if cls_n == c_name else 0.06) for cls_n in SLAI_CLASSES}
        dt_ms = (time.perf_counter() - t_start) * 1000.0
        dec_str, ev_deg = _derive_decision(c_name, conf_val)
        return {
            "tier": tier_key,
            "slai_class": c_name,
            "confidence": round(conf_val, 3),
            "landing_decision": dec_str,
            "evasion_vector_deg": ev_deg,
            "probabilities": prob_map,
            "inference_time_ms": round(dt_ms, 2)
        }

    req_tier = (req.model_tier or "tinylandingnet").lower()

    if req_tier == "all":
        t64 = prep64(pil_img).unsqueeze(0)
        t224 = prep224(pil_img).unsqueeze(0)
        r_t1 = _eval_single_model(tinylandingnet_model, t64, "tinylandingnet")
        r_t2 = _eval_single_model(mobilenet_v3_small_model, t224, "mobilenet_v3_small")
        r_t3 = _eval_single_model(resnet18_model, t224, "resnet18")
        return {
            "status": "success",
            "is_aerial": True,
            "slai_class": r_t1["slai_class"],
            "confidence": r_t1["confidence"],
            "landing_decision": r_t1["landing_decision"],
            "optimal_lz_valid": (r_t1["slai_class"] == "SAFE_LZ" or best_score > 0.5),
            "probabilities": r_t1["probabilities"],
            "grid_analysis": {
                "sector_matrix": sector_matrix,
                "best_sector": best_sector,
                "evasion_vector_deg": r_t1["evasion_vector_deg"]
            },
            "model_info": {
                "tier": "tinylandingnet",
                "inference_time_ms": r_t1["inference_time_ms"],
                "device": "cpu"
            },
            "all_tiers": {
                "tinylandingnet": r_t1,
                "mobilenet_v3_small": r_t2,
                "resnet18": r_t3
            }
        }

    if req_tier in ("mobilenet_v3_small", "mobilenet") and mobilenet_v3_small_model is not None:
        res = _eval_single_model(mobilenet_v3_small_model, prep224(pil_img).unsqueeze(0), "mobilenet_v3_small")
    elif req_tier in ("resnet18", "resnet") and resnet18_model is not None:
        res = _eval_single_model(resnet18_model, prep224(pil_img).unsqueeze(0), "resnet18")
    else:
        res = _eval_single_model(tinylandingnet_model, prep64(pil_img).unsqueeze(0), "tinylandingnet")

    return {
        "status": "success",
        "is_aerial": True,
        "slai_class": res["slai_class"],
        "confidence": res["confidence"],
        "landing_decision": res["landing_decision"],
        "optimal_lz_valid": (res["slai_class"] == "SAFE_LZ" or best_score > 0.5),
        "probabilities": res["probabilities"],
        "grid_analysis": {
            "sector_matrix": sector_matrix,
            "best_sector": best_sector,
            "evasion_vector_deg": res["evasion_vector_deg"]
        },
        "model_info": {
            "tier": res["tier"],
            "inference_time_ms": res["inference_time_ms"],
            "device": "cpu"
        }
    }


@app.get("/api/vision/models-comparison")
def get_vision_models_comparison():
    """Returns 3-tier vision model comparison and RTX 4060 GPU training benchmarks."""
    global _CACHE_VISION_COMPARISON
    if _CACHE_VISION_COMPARISON is not None:
        return _CACHE_VISION_COMPARISON
    comp_path = os.path.join(BASE_DIR, "ml", "vision_model_comparison.json")
    gpu_path = os.path.join(BASE_DIR, "ml", "gpu_training_summary.json")
    payload = {"status": "ok", "comparison": {}, "gpu_training_summary": {}}
    if os.path.exists(comp_path):
        with open(comp_path, "r", encoding="utf-8") as f:
            payload["comparison"] = json.load(f)
    if os.path.exists(gpu_path):
        with open(gpu_path, "r", encoding="utf-8") as f:
            payload["gpu_training_summary"] = json.load(f)
    _CACHE_VISION_COMPARISON = payload
    return payload


if __name__ == "__main__":
    import uvicorn
    print("[Server] Starting Cognitive CanSat FastAPI server on http://127.0.0.1:8000 ...")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)


