"""
Stream Processing Worker - Integrated CanSat Aerospace Telemetry Engine
Consumes from Redpanda topic 'cansat.telemetry.raw', computes or validates rolling kinematics,
writes Hot Path to TimescaleDB, detects ML anomalies, and buffers Cold Path to MinIO S3 in Snappy Parquet.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

import pandas as pd
import psycopg
from kafka import KafkaConsumer
from minio import Minio

# Ensure modules in stream_processing can find algorithms
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from algorithms import FlightStateEstimator

# DB Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "telemetry_db")
DB_USER = os.getenv("DB_USER", "cansat_admin")
DB_PASS = os.getenv("DB_PASS", "cansat_password")

# MinIO Config
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER = os.getenv("MINIO_USER", "minioadmin")
MINIO_PASS = os.getenv("MINIO_PASS", "minioadminpassword")
BUCKET_NAME = os.getenv("MINIO_BUCKET", "cansat-telemetry-lake")

# Kafka / Redpanda Config
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:19092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "cansat.telemetry.raw")


def init_minio() -> Optional[Minio]:
    try:
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            print(f"[+] Created MinIO cold storage bucket: {BUCKET_NAME}")
        else:
            print(f"[+] Connected to MinIO bucket: {BUCKET_NAME}")
        return client
    except Exception as e:
        print(f"[-] MinIO cold storage connection failed ({e}). Proceeding in hot-path only mode.")
        return None


def init_db():
    while True:
        try:
            conn = psycopg.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
            )
            print(f"[+] Connected to TimescaleDB Hot Path at {DB_HOST}:{DB_PORT}/{DB_NAME}!")
            return conn
        except Exception as e:
            print(f"[-] TimescaleDB not ready ({e}). Retrying in 2s...")
            time.sleep(2)


def run_stream_pipeline():
    print("=" * 70)
    print("      CANSAT DISTRIBUTED STREAM PROCESSING & ML FUSION ENGINE")
    print("=" * 70)
    
    # Initialize MinIO S3 client
    minio_client = init_minio()
    
    # Connect to TimescaleDB
    db_conn = init_db()
    db_cursor = db_conn.cursor()

    # Connect to Redpanda / Kafka
    print(f"[*] Subscribing to Redpanda broker at {KAFKA_BROKER} (topic: {KAFKA_TOPIC})...")
    consumer = None
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=[KAFKA_BROKER],
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                group_id="cansat-stream-worker-group"
            )
            print(f"[+] Subscribed to topic: {KAFKA_TOPIC}")
        except Exception as e:
            print(f"[-] Redpanda not ready ({e}). Retrying in 2s...")
            time.sleep(2)

    estimator = FlightStateEstimator()
    cold_buffer = []
    last_flush_time = time.time()
    seen_anomalies = set()

    print("[*] Stream worker active. Waiting for telemetry packets...\n")

    for msg in consumer:
        try:
            packet = msg.value
            t_sec = packet.get("timestamp_ms", int(time.time() * 1000)) / 1000.0
            alt = float(packet.get("altitude_m", 0.0))
            accel_z = float(packet.get("accel_z_g", 1.0))

            # Run stream analytics algorithm
            calc_velocity, calc_stage, event = estimator.process_frame(t_sec, alt, accel_z)
            
            # Use CanSat ML phase / Kalman velocity if present; otherwise fall back to estimator
            velocity = packet.get("velocity_mps")
            if velocity is None or abs(velocity) < 1e-5:
                velocity = calc_velocity
                packet["velocity_mps"] = velocity

            stage = packet.get("flight_stage")
            if not stage or stage in ("LAUNCH_PAD", "UNKNOWN"):
                stage = calc_stage
                packet["flight_stage"] = stage

            mission_id = packet.get("mission_id", "MISSION_ALPHA_01")
            packet_id = packet.get("packet_id", 0)

            # Hot Path: Insert into TimescaleDB
            now_iso = datetime.now(timezone.utc).isoformat()
            
            # Check for ML Anomaly
            is_anom = packet.get("is_anomaly", False)
            anom_score = float(packet.get("anomaly_score", 0.0))
            anom_type = packet.get("status", "OK")

            try:
                db_cursor.execute("""
                    INSERT INTO raw_telemetry (
                        time, mission_id, packet_id, altitude_m, pressure_hpa, velocity_mps,
                        accel_x_g, accel_y_g, accel_z_g, gyro_x_dps, gyro_y_dps, gyro_z_dps,
                        battery_v, temperature_c, flight_stage, status,
                        humidity_pct, lat, lon, pitch_deg, roll_deg, accel_mag_g,
                        anomaly_score, is_anomaly, dew_point_c, air_density_kg_m3, calibrated_altitude_m
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                """, (
                    now_iso, mission_id, packet_id, alt,
                    packet.get("pressure_hpa", 1013.25), velocity,
                    packet.get("accel_x_g", 0.0), packet.get("accel_y_g", 0.0), accel_z,
                    packet.get("gyro_x_dps", 0.0), packet.get("gyro_y_dps", 0.0), packet.get("gyro_z_dps", 0.0),
                    packet.get("battery_v", 4.2), packet.get("temperature_c", 25.0),
                    stage, anom_type,
                    packet.get("humidity_pct", 50.0), packet.get("lat", 22.5727), packet.get("lon", 88.3655),
                    packet.get("pitch_deg", 0.0), packet.get("roll_deg", 0.0),
                    packet.get("accel_mag_g", 1.0), anom_score, is_anom,
                    packet.get("dew_point_c"), packet.get("air_density_kg_m3"), packet.get("calibrated_altitude_m", alt)
                ))

                # Handle Trajectory Events
                if event:
                    db_cursor.execute("""
                        INSERT INTO flight_events (time, mission_id, event_type, severity, description, metric_value)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (now_iso, mission_id, event, "CRITICAL", f"Algorithm trigger: {event}", alt))
                    print(f"[🔥 TRAJECTORY EVENT] {event} at Altitude: {alt}m | Velocity: {velocity} m/s")

                # Handle Cognitive AI ML Anomaly
                if (is_anom or anom_score > 0.65) and anom_type != "OK":
                    event_key = f"{mission_id}:{anom_type}:{int(t_sec / 2)}"
                    if event_key not in seen_anomalies:
                        seen_anomalies.add(event_key)
                        db_cursor.execute("""
                            INSERT INTO flight_events (time, mission_id, event_type, severity, description, metric_value)
                            VALUES (%s, %s, %s, %s, %s, %s);
                        """, (now_iso, mission_id, f"AI_ANOMALY_{anom_type}", "WARNING", f"Cognitive AI Alert: {anom_type} (Score: {anom_score:.2f})", anom_score))
                        print(f"[⚠️ AI ANOMALY] {anom_type} detected (score: {anom_score:.2f}) at alt {alt}m")

                db_conn.commit()
            except (psycopg.OperationalError, psycopg.DatabaseError) as dbe:
                print(f"[!] TimescaleDB write error: {dbe}. Reconnecting...")
                try:
                    db_conn = init_db()
                    db_cursor = db_conn.cursor()
                except Exception:
                    pass

            # Buffer for Cold Path (Parquet Lakehouse)
            packet["time"] = now_iso
            cold_buffer.append(packet)

            # Flush to MinIO S3 every 5 seconds or 50 packets
            if minio_client and (len(cold_buffer) >= 50 or (time.time() - last_flush_time > 5.0 and cold_buffer)):
                try:
                    df = pd.DataFrame(cold_buffer)
                    parquet_buffer = BytesIO()
                    df.to_parquet(parquet_buffer, engine="pyarrow", compression="snappy", index=False)
                    parquet_buffer.seek(0)
                    
                    object_name = f"raw_events/mission={mission_id}/chunk_{int(time.time())}.parquet"
                    minio_client.put_object(
                        BUCKET_NAME, object_name, parquet_buffer,
                        length=len(parquet_buffer.getvalue()),
                        content_type="application/octet-stream"
                    )
                    print(f"[❄️ COLD PATH] Flushed {len(cold_buffer)} records to S3: {object_name}")
                except Exception as s3_err:
                    print(f"[!] MinIO flush warning: {s3_err}")
                finally:
                    cold_buffer.clear()
                    last_flush_time = time.time()

        except Exception as loop_err:
            print(f"[!] Error in stream processing loop: {loop_err}")
            time.sleep(0.01)


if __name__ == "__main__":
    run_stream_pipeline()