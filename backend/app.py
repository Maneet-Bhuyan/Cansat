"""
Cognitive CanSat FastAPI Real-Time Machine Learning Backend Server
Serves real-time inference using trained scikit-learn and PyOD models.
"""
import os
import math
import json
import time
import warnings
from typing import Dict, Any, Optional, List
from collections import deque
import numpy as np
import pandas as pd
import joblib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Suppress minor version warnings for clean telemetry logs
warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "ml", "saved_models")
METRICS_PATH = os.path.join(BASE_DIR, "ml", "model_metrics.json")

app = FastAPI(
    title="Cognitive CanSat ML Telemetry Server",
    description="Real-Time Machine Learning Inference API for Sounding Pico-Satellite Telemetry",
    version="2.0.0"
)

# Enable CORS for local file execution and browser dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    print(f"[LIVE AUDIT]: Temp={payload.temp}C, Press={payload.pressure}hPa, Alt={payload.altitude}m, Accel=({payload.ax},{payload.ay},{payload.az})g, Gyro=({payload.gx},{payload.gy},{payload.gz})deg/s, GPS=({payload.lat},{payload.lon}), Hum={payload.humidity}%, Bat={payload.batteryVoltage}V, vSpd={v_spd}m/s", flush=True)
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

@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/index.html")
def serve_index_html():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

test_cases_dir = os.path.join(BASE_DIR, "test_cases")
if os.path.exists(test_cases_dir):
    app.mount("/test_cases", StaticFiles(directory=test_cases_dir), name="test_cases")

@app.get("/api/latest_telemetry")
def get_latest_telemetry():
    return {
        "status": "success",
        "count": len(live_telemetry_history),
        "packets": list(live_telemetry_history)
    }

@app.get("/api/health")
def get_health():
    return {
        "status": "online" if models_loaded else "degraded",
        "models_loaded": models_loaded,
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

# --- REAL-TIME HARDWARE SERIAL BRIDGE (COM3 / LoRa Ground Receiver) ---
import serial
import serial.tools.list_ports
import threading
import asyncio

serial_subscribers: List[WebSocket] = []
serial_thread_running = False
serial_thread_lock = threading.Lock()

async def broadcast_serial_line(line: str):
    for ws in list(serial_subscribers):
        try:
            await ws.send_text(line)
        except Exception:
            pass

def serial_worker_loop(loop, port_name: str = "COM3", baud_rate: int = 9600):
    global serial_thread_running
    try:
        ser = serial.Serial(port_name, baud_rate, timeout=1)
        ser.dtr = True
        ser.rts = True
        print(f"[Serial Bridge] Connected to {port_name} at {baud_rate} baud.")
        while serial_thread_running:
            if ser.in_waiting:
                raw_bytes = ser.readline()
                line = raw_bytes.decode('utf-8', errors='ignore').strip()
                if line:
                    asyncio.run_coroutine_threadsafe(broadcast_serial_line(line), loop)
            else:
                time.sleep(0.02)
        ser.close()
        print("[Serial Bridge] Port closed cleanly.")
    except Exception as e:
        print(f"[Serial Bridge] Serial worker error: {e}")
        serial_thread_running = False

@app.websocket("/ws/serial")
async def websocket_serial_bridge(websocket: WebSocket):
    global serial_thread_running
    await websocket.accept()
    serial_subscribers.append(websocket)
    print(f"[WebSocket] Serial bridge client connected. (Total: {len(serial_subscribers)})")
    
    loop = asyncio.get_running_loop()
    with serial_thread_lock:
        if not serial_thread_running:
            serial_thread_running = True
            t = threading.Thread(target=serial_worker_loop, args=(loop, "COM3", 9600), daemon=True)
            t.start()
            
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in serial_subscribers:
            serial_subscribers.remove(websocket)
        print(f"[WebSocket] Serial client disconnected. (Remaining: {len(serial_subscribers)})")
        if len(serial_subscribers) == 0:
            serial_thread_running = False

