"""
Post-Flight Analytics Engine (Cold Path Data Lakehouse)
Executes ultra-fast analytical OLAP queries directly over MinIO S3 Snappy Parquet files
(or local parquet archives) using DuckDB.
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, Optional
import duckdb

S3_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
S3_ACCESS_KEY = os.getenv("MINIO_USER", "minioadmin")
S3_SECRET_KEY = os.getenv("MINIO_PASS", "minioadminpassword")
BUCKET_NAME = os.getenv("MINIO_BUCKET", "cansat-telemetry-lake")


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_endpoint='{S3_ENDPOINT}';")
        con.execute(f"SET s3_access_key_id='{S3_ACCESS_KEY}';")
        con.execute(f"SET s3_secret_access_key='{S3_SECRET_KEY}';")
        con.execute("SET s3_use_ssl=false;")
        con.execute("SET s3_url_style='path';")
    except Exception as e:
        print(f"[!] DuckDB httpfs configuration warning: {e}")
    return con


def run_mission_analytics(mission_id: Optional[str] = None, parquet_path: Optional[str] = None) -> Dict[str, Any]:
    con = get_duckdb_connection()
    target_path = parquet_path or f"s3://{BUCKET_NAME}/raw_events/*/*.parquet"
    if mission_id and not parquet_path:
        target_path = f"s3://{BUCKET_NAME}/raw_events/mission={mission_id}/*.parquet"

    try:
        summary_query = f"""
            SELECT 
                COUNT(packet_id) AS total_packets_logged,
                COALESCE(MAX(altitude_m), 0.0) AS max_apogee_meters,
                COALESCE(MIN(altitude_m), 0.0) AS launch_pad_altitude_meters,
                COALESCE(MIN(time), '') AS mission_start,
                COALESCE(MAX(time), '') AS mission_end,
                COALESCE(ROUND(AVG(velocity_mps), 2), 0.0) AS average_velocity,
                COALESCE(ROUND(MIN(battery_v), 2), 0.0) AS min_battery_level,
                COALESCE(ROUND(MAX(anomaly_score), 3), 0.0) AS max_anomaly_score
            FROM read_parquet('{target_path}');
        """
        summary_df = con.execute(summary_query).df()
        summary_dict = summary_df.to_dict(orient="records")[0] if not summary_df.empty else {}

        stages_query = f"""
            SELECT 
                flight_stage,
                COUNT(*) AS packet_count,
                ROUND(AVG(altitude_m), 1) AS avg_altitude,
                ROUND(AVG(velocity_mps), 1) AS avg_velocity,
                ROUND(MAX(accel_mag_g), 2) AS max_accel_g
            FROM read_parquet('{target_path}')
            GROUP BY flight_stage
            ORDER BY packet_count DESC;
        """
        stages_df = con.execute(stages_query).df()
        stages_list = stages_df.to_dict(orient="records")

        anomalies_query = f"""
            SELECT 
                status,
                COUNT(*) AS count,
                ROUND(AVG(anomaly_score), 3) AS avg_score,
                ROUND(MAX(altitude_m), 1) AS peak_alt
            FROM read_parquet('{target_path}')
            WHERE status != 'OK' OR is_anomaly = TRUE
            GROUP BY status
            ORDER BY count DESC;
        """
        anomalies_df = con.execute(anomalies_query).df()
        anomalies_list = anomalies_df.to_dict(orient="records")

        return {
            "status": "success",
            "mission_id": mission_id or "ALL_MISSIONS",
            "target_path": target_path,
            "summary": summary_dict,
            "stages": stages_list,
            "anomalies": anomalies_list
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "target_path": target_path
        }


def analyze_mission(mission_id: Optional[str] = None):
    print("=" * 70)
    print("      CANSAT COLD-PATH LAKEHOUSE ANALYTICS (DUCKDB + S3)")
    print("=" * 70)
    print("[*] Querying MinIO S3 Snappy Parquet flight archives...")
    
    results = run_mission_analytics(mission_id=mission_id)
    if results.get("status") == "error":
        print(f"\n[-] Query note: {results.get('message')}")
        print("    (Ensure MinIO is running and packets have been flushed to S3)")
        return

    print("\n--- Mission Summary Report ---")
    for k, v in results.get("summary", {}).items():
        print(f"  {k:<30}: {v}")

    print("\n--- Flight Stage Distribution ---")
    for st in results.get("stages", []):
        print(f"  Stage: {st.get('flight_stage', 'N/A'):<20} | Packets: {st.get('packet_count', 0):<6} | Avg Alt: {st.get('avg_altitude', 0):<6}m | Avg Vel: {st.get('avg_velocity', 0)} m/s")

    anoms = results.get("anomalies", [])
    if anoms:
        print("\n--- Detected Anomaly Events ---")
        for a in anoms:
            print(f"  Category: {a.get('status')} | Count: {a.get('count')} | Avg Score: {a.get('avg_score')}")
    else:
        print("\n[+] No flight anomalies recorded in this dataset (Nominal Profile).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DuckDB CanSat Cold Path Analytics")
    parser.add_argument("--mission-id", default=None, help="Filter analytics by mission ID")
    parser.add_argument("--parquet", default=None, help="Direct path to parquet file or pattern")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    args = parser.parse_args()

    if args.json:
        res = run_mission_analytics(mission_id=args.mission_id, parquet_path=args.parquet)
        print(json.dumps(res, indent=2))
    else:
        analyze_mission(mission_id=args.mission_id)