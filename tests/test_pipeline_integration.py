"""
Automated Test Suite for CanSat & Telemetry Pipeline Integration,
Production Security Hardening, and Artifact Endpoints.
Validates schema translation, pipeline bridge queuing, FastAPI endpoints,
security path-traversal guards, and offline fault-tolerance.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Also add telemetry pipeline to sys.path
PIPELINE_ROOT = PROJECT_ROOT.parent / "cansat-telemetry-pipeline"
if PIPELINE_ROOT.exists():
    sys.path.insert(0, str(PIPELINE_ROOT))

from fastapi import HTTPException
from backend.core.pipeline_bridge import PipelineBridge
import backend.app as app_module


class TestPipelineBridge(unittest.TestCase):
    """Tests the non-blocking PipelineBridge component."""

    def test_bridge_initialization_and_status(self):
        bridge = PipelineBridge(broker="localhost:19092", queue_size=100)
        bridge.start()
        try:
            status = bridge.get_status()
            self.assertTrue(status["enabled"])
            self.assertEqual(status["broker"], "localhost:19092")
            self.assertEqual(status["telemetry_topic"], "cansat.telemetry.raw")
            self.assertEqual(status["events_topic"], "cansat.telemetry.events")
            self.assertEqual(status["queue_size"], 0)
            self.assertEqual(status["packets_queued"], 0)
            self.assertIn("kafka_available", status)
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
                "air_density": 1.21,
            }
            enqueued = bridge.publish_telemetry(sample_data, mission_id="TEST_MISSION_01")
            self.assertTrue(enqueued)
            self.assertEqual(bridge.packets_queued, 1)
            self.assertEqual(bridge._queue.qsize(), 1)

            item = bridge._queue.get_nowait()
            self.assertEqual(item["type"], "telemetry")
            self.assertEqual(item["topic"], "cansat.telemetry.raw")
            p = item["payload"]
            self.assertEqual(p["mission_id"], "TEST_MISSION_01")
            self.assertEqual(p["altitude_m"], 154.2)
            self.assertEqual(p["temperature_c"], 24.8)
            self.assertEqual(p["pressure_hpa"], 1012.4)
            self.assertEqual(p["velocity_mps"], -4.8)
            self.assertEqual(p["battery_v"], 3.92)
            self.assertEqual(p["flight_stage"], "PARACHUTE_DESCENT")
            self.assertEqual(p["humidity_pct"], 58.2)
            self.assertEqual(p["pitch_deg"], 2.5)
            self.assertEqual(p["roll_deg"], -1.2)
            self.assertEqual(p["dew_point_c"], 16.4)
            self.assertEqual(p["air_density_kg_m3"], 1.21)
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
                mission_id="TEST_MISSION_02",
            )
            self.assertEqual(bridge.packets_queued, 1)
            item = bridge._queue.get_nowait()
            self.assertEqual(item["type"], "event")
            self.assertEqual(item["topic"], "cansat.telemetry.events")
            self.assertEqual(item["payload"]["event_type"], "AI_ANOMALY_HIGH_G_SHOCK")
            self.assertEqual(item["payload"]["severity"], "WARNING")
            self.assertEqual(item["payload"]["metric_value"], 4.82)
        finally:
            bridge.stop()

    def test_bounded_queue_drop_policy(self):
        bridge = PipelineBridge(broker="localhost:19092", queue_size=5)
        for i in range(10):
            bridge.publish_telemetry({"altitude": i, "temp": 20.0})

        self.assertLessEqual(bridge._queue.qsize(), 5)
        self.assertGreater(bridge.packets_dropped, 0)


class TestFastAPIEndpointsAndSecurity(unittest.TestCase):
    """Tests FastAPI endpoints, path traversal protection, and research artifacts."""

    def test_get_pipeline_status(self):
        data = app_module.get_pipeline_status()
        self.assertEqual(data["status"], "success")
        p = data["pipeline"]
        self.assertIn("enabled", p)
        self.assertIn("connected", p)
        self.assertIn("broker", p)
        self.assertIn("timescaledb_online", p)
        self.assertEqual(p["grafana_url"], "http://localhost:3000")
        self.assertEqual(p["minio_console_url"], "http://localhost:9001")

    def test_update_pipeline_config(self):
        req = app_module.PipelineConfigRequest(enabled=True)
        data = app_module.update_pipeline_config(req)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["pipeline"]["enabled"])

    def test_get_timescale_summary_offline_graceful(self):
        data = app_module.get_timescale_summary(limit=5)
        self.assertIn(data["status"], ("online", "offline"))
        self.assertIsInstance(data.get("telemetry"), list)

    def test_stream_scenario_to_pipeline(self):
        req = app_module.ScenarioStreamRequest(
            scenario="01_nominal_sounding_flight",
            rate_hz=50.0,
            mission_id="TEST_INTEG_FLIGHT",
        )
        data = app_module.trigger_scenario_pipeline_stream(req)
        self.assertEqual(data["status"], "started")
        self.assertEqual(data["scenario"], "01_nominal_sounding_flight")
        self.assertEqual(data["mission_id"], "TEST_INTEG_FLIGHT")

    def test_security_path_traversal_guard(self):
        with self.assertRaises(HTTPException) as ctx:
            app_module._resolve_safe_scenario_csv("../../backend/app")
        self.assertIn(ctx.exception.status_code, (400, 404))

        with self.assertRaises(HTTPException) as ctx2:
            app_module._resolve_safe_scenario_csv("..\\..\\secret$file")
        self.assertIn(ctx2.exception.status_code, (400, 404))

        clean_name, valid_path = app_module._resolve_safe_scenario_csv("01_nominal_sounding_flight")
        self.assertEqual(clean_name, "01_nominal_sounding_flight")
        self.assertTrue(os.path.isfile(valid_path))

    def test_health_and_research_artifact_endpoints(self):
        health = app_module.get_health()
        self.assertEqual(health["status"], "online")
        self.assertTrue(health["models_loaded"])
        self.assertTrue(health["security_headers_enabled"])

        pitch_page = app_module.serve_pitch_html()
        self.assertTrue(os.path.isfile(pitch_page.path))

        pptx_resp = app_module.download_pitch_deck_pptx()
        self.assertTrue(os.path.isfile(pptx_resp.path))
        self.assertGreater(os.path.getsize(pptx_resp.path), 100_000)

        tex_resp = app_module.download_ieee_paper_tex()
        self.assertTrue(os.path.isfile(tex_resp.path))
        self.assertGreater(os.path.getsize(tex_resp.path), 40_000)


if __name__ == "__main__":
    unittest.main()
