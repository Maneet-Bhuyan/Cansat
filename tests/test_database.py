"""
Unit test suite for Cognitive CanSat Database & Post-Flight Review Report Engine
Tests SQLite WAL initialization, batch telemetry ingestion, event logging, and PFR audit persistence.
"""

import os
import unittest
import tempfile
from pathlib import Path

from backend.core.database import (
    init_db,
    get_db_connection,
    create_mission,
    insert_telemetry_batch,
    insert_event,
    finalize_mission,
    generate_and_save_pfr_report,
    get_mission,
    list_missions,
    get_mission_report,
    get_mission_telemetry,
    get_mission_events,
    delete_mission
)


class TestCanSatDatabase(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_cansat.db")
        init_db(self.db_path)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_wal_mode_and_tables(self):
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            self.assertIn("missions", tables)
            self.assertIn("telemetry_records", tables)
            self.assertIn("mission_reports", tables)
            self.assertIn("mission_events", tables)

    def test_mission_lifecycle_and_pfr_report(self):
        # 1. Create Mission
        m = create_mission(
            name="Autonomous Sounding Test Alpha",
            callsign="CANSAT-TEST-01",
            operator="Rishi Flight Ops",
            notes="Testing EKF fusion and PFR database persistence",
            db_path=self.db_path
        )
        mission_id = m["id"]
        self.assertEqual(m["status"], "ACTIVE_FLIGHT")
        self.assertEqual(m["callsign"], "CANSAT-TEST-01")

        # 2. Log Initial Event
        evt_id = insert_event(
            mission_id=mission_id,
            timestamp_ms=0,
            event_type="MISSION_ARMED",
            severity="INFO",
            description="Ground station armed for launch pad static test",
            db_path=self.db_path
        )
        self.assertGreater(evt_id, 0)

        # 3. Simulate Flight Telemetry Sequence (Pad -> Ascent -> Apogee -> Descent -> Touchdown)
        records = []
        # Pad Idle (0 - 5s)
        for i in range(6):
            records.append({
                "timestamp_ms": i * 1000,
                "met_seconds": float(i),
                "altitude": 200.0 + (i * 0.05),
                "pressure": 990.0,
                "temp": 24.0,
                "humidity": 45.0,
                "battery_voltage": 4.18 - (i * 0.002),
                "ax": 0.01, "ay": 0.02, "az": 1.0,
                "gx": 0.1, "gy": -0.1, "gz": 0.05,
                "lat": 28.613939, "lon": 77.209021,
                "v_spd": 0.0,
                "accel_mag": 1.0,
                "air_density": 1.205,
                "dew_point": 11.5,
                "lapse_rate": 0.65,
                "flight_phase": "PAD_IDLE"
            })

        # Balloon Ascent (6 - 40s) up to 850m
        for i in range(6, 41):
            t = float(i)
            alt = 200.0 + (t - 5.0) * 18.5
            records.append({
                "timestamp_ms": i * 1000,
                "met_seconds": t,
                "altitude": alt,
                "pressure": 990.0 - ((alt - 200.0) * 0.11),
                "temp": 24.0 - ((alt - 200.0) * 0.0065),
                "humidity": 45.0 + ((alt - 200.0) * 0.02),
                "battery_voltage": 4.15 - (i * 0.003),
                "ax": 0.05, "ay": 0.08, "az": 1.35,
                "gx": 0.5, "gy": -0.4, "gz": 0.2,
                "lat": 28.613939 + (i * 0.00001),
                "lon": 77.209021 + (i * 0.00002),
                "v_spd": 18.5,
                "accel_mag": 1.38,
                "air_density": 1.15,
                "dew_point": 9.2,
                "lapse_rate": 0.65,
                "flight_phase": "BALLOON_ASCENT"
            })

        # Apogee Separation & Shock (41 - 43s) Peak 860m, 12.5G shock
        for i in range(41, 44):
            records.append({
                "timestamp_ms": i * 1000,
                "met_seconds": float(i),
                "altitude": 860.0 - (i - 41) * 2.0,
                "pressure": 915.0,
                "temp": 19.7,
                "humidity": 58.0,
                "battery_voltage": 4.02,
                "ax": 4.5, "ay": 6.2, "az": 9.8,
                "gx": 25.0, "gy": -18.0, "gz": 15.0,
                "lat": 28.6143, "lon": 77.2098,
                "v_spd": 0.5 - (i - 41) * 3.0,
                "accel_mag": 12.5,
                "air_density": 1.12,
                "dew_point": 8.5,
                "lapse_rate": 0.65,
                "flight_phase": "APOGEE_BURST"
            })

        # Parachute Descent (44 - 120s) steady 8.2 m/s descent
        for i in range(44, 121):
            t = float(i)
            alt = max(200.0, 854.0 - (t - 43.0) * 8.2)
            records.append({
                "timestamp_ms": i * 1000,
                "met_seconds": t,
                "altitude": alt,
                "pressure": 915.0 + ((860.0 - alt) * 0.11),
                "temp": 19.7 + ((860.0 - alt) * 0.0065),
                "humidity": 58.0,
                "battery_voltage": 3.95 - (i * 0.002),
                "ax": 0.05, "ay": 0.06, "az": 1.02,
                "gx": 2.1, "gy": -1.8, "gz": 0.9,
                "lat": 28.6143 + (i * 0.000015),
                "lon": 77.2098 + (i * 0.00003),
                "v_spd": -8.2,
                "accel_mag": 1.05,
                "air_density": 1.18,
                "dew_point": 10.1,
                "lapse_rate": 0.65,
                "flight_phase": "PARACHUTE_DESCENT"
            })

        # Touchdown (121 - 125s)
        for i in range(121, 126):
            records.append({
                "timestamp_ms": i * 1000,
                "met_seconds": float(i),
                "altitude": 200.0,
                "pressure": 990.0,
                "temp": 24.1,
                "humidity": 46.0,
                "battery_voltage": 3.75,
                "ax": 0.01, "ay": 0.01, "az": 1.0,
                "gx": 0.0, "gy": 0.0, "gz": 0.0,
                "lat": 28.6162, "lon": 77.2135,
                "v_spd": 0.0,
                "accel_mag": 1.0,
                "air_density": 1.205,
                "dew_point": 11.6,
                "lapse_rate": 0.65,
                "flight_phase": "TOUCHDOWN_RECOVERY"
            })

        # 4. Batch Insert
        inserted = insert_telemetry_batch(mission_id, records, db_path=self.db_path)
        self.assertEqual(inserted, len(records))

        # 5. Finalize Mission and Build Report
        report = finalize_mission(mission_id, db_path=self.db_path)

        # 6. Verify Calculated PFR Metrics
        self.assertEqual(report["mission_id"], mission_id)
        self.assertAlmostEqual(report["peak_altitude_msl"], 860.0, delta=0.5)
        self.assertAlmostEqual(report["peak_apogee_agl"], 660.0, delta=1.0)
        self.assertEqual(report["time_to_apogee_s"], 41.0)
        self.assertAlmostEqual(report["max_ejection_shock_g"], 12.5, delta=0.1)
        self.assertAlmostEqual(report["terminal_descent_rate_mps"], 8.2, delta=0.2)
        self.assertEqual(report["descent_compliance"], "COMPLIANT_NOMINAL (6-11 m/s)")
        self.assertEqual(report["total_packets"], len(records))
        self.assertGreater(report["horizontal_drift_m"], 100.0)
        self.assertIn("POST-FLIGHT REVIEW", report["report_markdown"])

        # 7. Query Mission and Report from DB
        stored_m = get_mission(mission_id, db_path=self.db_path)
        self.assertEqual(stored_m["status"], "COMPLETED")

        stored_report = get_mission_report(mission_id, db_path=self.db_path)
        self.assertIsNotNone(stored_report)
        self.assertEqual(stored_report["mission_id"], mission_id)
        self.assertEqual(stored_report["descent_compliance"], "COMPLIANT_NOMINAL (6-11 m/s)")
        self.assertIn("parsed_json", stored_report)

        # 8. Query Telemetry
        telemetry = get_mission_telemetry(mission_id, db_path=self.db_path)
        self.assertEqual(len(telemetry), len(records))
        self.assertEqual(telemetry[0]["flight_phase"], "PAD_IDLE")

        # 9. Query Events
        events = get_mission_events(mission_id, db_path=self.db_path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "MISSION_ARMED")

        # 10. Test Mission Listing
        all_missions = list_missions(db_path=self.db_path)
        self.assertEqual(len(all_missions), 1)
        self.assertEqual(all_missions[0]["packet_count"], len(records))
        self.assertAlmostEqual(all_missions[0]["max_altitude"], 860.0, delta=0.5)

        # 11. Test Delete Mission (Cascades)
        deleted = delete_mission(mission_id, db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertIsNone(get_mission(mission_id, db_path=self.db_path))
        self.assertIsNone(get_mission_report(mission_id, db_path=self.db_path))
        self.assertEqual(len(get_mission_telemetry(mission_id, db_path=self.db_path)), 0)


if __name__ == "__main__":
    unittest.main()
