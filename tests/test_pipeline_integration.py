"""
Automated Test Suite for CanSat & Telemetry Pipeline Integration
Validates schema translation, pipeline bridge queuing, FastAPI endpoints,
and offline fault-tolerance.
"""

import os
import sys
import time
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Also add telemetry pipeline to sys.path
PIPELINE_ROOT = PROJECT_ROOT.parent / "cansat-telemetry-pipeline"
if PIPELINE_ROOT.exists():
    sys.path.insert(0, str(PIPELINE_ROOT))

from backend.core.pipeline_bridge import PipelineBridge
from fastapi.testclient import TestClient
from backend.app import app


class TestPipelineBridge:
    """Tests the non-blocking PipelineBridge component."""

    def test_bridge_initialization_and_status(self):
        bridge = PipelineBridge(broker="localhost:19092", queue_size=100)
        bridge.start()
        try:
            status = bridge.get_status()
            assert status["enabled"] is True
            assert status["broker"] == "localhost:19092"
            assert status["telemetry_topic"] == "cansat.telemetry.raw"
            assert status["events_topic"] == "cansat.telemetry.events"
            assert status["queue_size"] == 0
            assert status["packets_queued"] == 0
            assert status["kafka_available"] is True
        finally:
            bridge.stop()

    def test_publish_telemetry_schema_normalization(self):
        bridge = PipelineBridge(broker="localhost:19092", queue_size=100)
        bridge.start()
        try:
            sample_data = {
                "temp": 24.8,
                "pressure": 1012.4,
                "altitude": 154.2,
                "ax": 0.05,
                "ay": -0.02,
                "az": 0.98,
                "gx": 1.2,
                "gy": -0.8,
                "gz": 0.4,
                "lat": 22.5727,
                "lon": 88.3655,
                "humidity": 58.2,
                "batteryVoltage": 3.92,
                "vSpd": -4.8,
                "flight_phase": "PARACHUTE_DESCENT",
                "anomaly_score": 0.12,
                "is_anomaly": False,
                "pitch": 2.5,
                "roll": -1.2,
                "dew_point": 16.4,
                "air_density": 1.21
            }
            enqueued = bridge.publish_telemetry(sample_data, mission_id="TEST_MISSION_01")
            assert enqueued is True
            assert bridge.packets_queued == 1
            assert bridge._queue.qsize() == 1

            # Inspect queued item
            item = bridge._queue.get_nowait()
            assert item["type"] == "telemetry"
            assert item["topic"] == "cansat.telemetry.raw"
            p = item["payload"]
            assert p["mission_id"] == "TEST_MISSION_01"
            assert p["altitude_m"] == 154.2
            assert p["temperature_c"] == 24.8
            assert p["pressure_hpa"] == 1012.4
            assert p["velocity_mps"] == -4.8
            assert p["battery_v"] == 3.92
            assert p["flight_stage"] == "PARACHUTE_DESCENT"
            assert p["humidity_pct"] == 58.2
            assert p["pitch_deg"] == 2.5
            assert p["roll_deg"] == -1.2
            assert p["dew_point_c"] == 16.4
            assert p["air_density_kg_m3"] == 1.21
        finally:
            bridge.stop()

    def test_publish_event_formatting(self):
        bridge = PipelineBridge(broker="localhost:19092", queue_size=100)
        bridge.start()
        try:
            bridge.publish_event(
                event_type="AI_ANOMALY_HIGH_G_SHOCK",
                severity="WARNING",
                description="Peak transient G-shock exceeded 4.5g during deployment",
                metric_value=4.82,
                mission_id="TEST_MISSION_02"
            )
            assert bridge.packets_queued == 1
            item = bridge._queue.get_nowait()
            assert item["type"] == "event"
            assert item["topic"] == "cansat.telemetry.events"
            assert item["payload"]["event_type"] == "AI_ANOMALY_HIGH_G_SHOCK"
            assert item["payload"]["severity"] == "WARNING"
            assert item["payload"]["metric_value"] == 4.82
        finally:
            bridge.stop()

    def test_bounded_queue_drop_policy(self):
        # Verify queue does not grow infinitely if broker is disconnected
        bridge = PipelineBridge(broker="localhost:19092", queue_size=5)
        # Note: Do not start worker thread so items accumulate
        for i in range(10):
            bridge.publish_telemetry({"altitude": i, "temp": 20.0})

        assert bridge._queue.qsize() <= 5
        assert bridge.packets_dropped > 0


class TestPipelineFastAPIEndpoints:
    """Tests the FastAPI REST API endpoints for the telemetry pipeline."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_pipeline_status(self, client):
        resp = client.get("/api/pipeline/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        p = data["pipeline"]
        assert "enabled" in p
        assert "connected" in p
        assert "broker" in p
        assert "timescaledb_online" in p
        assert data["pipeline"]["grafana_url"] == "http://localhost:3000"
        assert data["pipeline"]["minio_console_url"] == "http://localhost:9001"

    def test_update_pipeline_config(self, client):
        resp = client.post("/api/pipeline/config", json={"enabled": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["pipeline"]["enabled"] is True

    def test_get_timescale_summary_offline_graceful(self, client):
        resp = client.get("/api/pipeline/timescale-summary?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        # Either online if DB is running, or offline with clear message
        assert data["status"] in ("online", "offline")
        assert isinstance(data.get("telemetry"), list)

    def test_stream_scenario_to_pipeline(self, client):
        resp = client.post("/api/pipeline/stream-scenario", json={
            "scenario": "01_nominal_sounding_flight",
            "rate_hz": 50.0,
            "mission_id": "TEST_INTEG_FLIGHT"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["scenario"] == "01_nominal_sounding_flight"
        assert data["mission_id"] == "TEST_INTEG_FLIGHT"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
