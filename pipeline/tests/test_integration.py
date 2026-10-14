"""
Unit and Integration Test Suite for CanSat Telemetry Pipeline
Tests packet parser, aerospace schema transformation, CRC16,
and flight state estimation on CanSat flight profiles.
"""

import os
import sys
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from ingestion.packet_parser import TelemetryPacket, calculate_crc16
from stream_processing.algorithms import FlightStateEstimator
from analytics.post_flight_analytics import run_mission_analytics


class TestTelemetryPacketParser:
    def test_standard_packet_validation(self):
        pkt = TelemetryPacket(
            mission_id="ALPHA_01",
            packet_id=42,
            timestamp_ms=1000,
            altitude_m=350.2,
            pressure_hpa=980.5,
            velocity_mps=15.2,
            accel_x_g=0.1,
            accel_y_g=-0.05,
            accel_z_g=2.1,
            gyro_x_dps=1.5,
            gyro_y_dps=-2.0,
            gyro_z_dps=0.5,
            battery_v=3.95,
            temperature_c=21.4,
            flight_stage="BOOST",
            status="OK"
        )
        assert pkt.mission_id == "ALPHA_01"
        assert pkt.altitude_m == 350.2
        assert pkt.flight_stage == "BOOST"

    def test_from_cansat_dict_mapping(self):
        cansat_record = {
            "temp": 26.2,
            "pressure": 1011.8,
            "altitude": 85.4,
            "calibrated_altitude": 85.1,
            "ax": 0.02,
            "ay": -0.01,
            "az": 1.05,
            "gx": 0.5,
            "gy": -0.2,
            "gz": 0.1,
            "lat": 22.5727,
            "lon": 88.3655,
            "humidity": 52.0,
            "batteryVoltage": 4.12,
            "vSpd": 12.5,
            "flight_phase": "BALLOON_ASCENT",
            "anomaly_score": 0.05,
            "is_anomaly": False,
            "pitch": 1.2,
            "roll": -0.5,
            "dew_point": 15.8,
            "air_density": 1.22
        }
        pkt = TelemetryPacket.from_cansat_dict(cansat_record, mission_id="SOUNDING_01", packet_id=10)
        assert pkt.mission_id == "SOUNDING_01"
        assert pkt.packet_id == 10
        assert pkt.temperature_c == 26.2
        assert pkt.pressure_hpa == 1011.8
        assert pkt.altitude_m == 85.4
        assert pkt.calibrated_altitude_m == 85.1
        assert pkt.velocity_mps == 12.5
        assert pkt.battery_v == 4.12
        assert pkt.flight_stage == "BALLOON_ASCENT"
        assert pkt.humidity_pct == 52.0
        assert pkt.lat == 22.5727
        assert pkt.lon == 88.3655
        assert pkt.pitch_deg == 1.2
        assert pkt.roll_deg == -0.5
        assert pkt.dew_point_c == 15.8
        assert pkt.air_density_kg_m3 == 1.22

    def test_from_csv_line(self):
        line = "24.5, 1013.0, 10.2, 0.1, -0.2, 0.3, 0.01, -0.02, 0.99, 22.57, 88.36, 45.0, 4.18"
        pkt = TelemetryPacket.from_csv_line(line, mission_id="CSV_TEST", packet_id=1)
        assert pkt.mission_id == "CSV_TEST"
        assert pkt.temperature_c == 24.5
        assert pkt.pressure_hpa == 1013.0
        assert pkt.altitude_m == 10.2
        assert pkt.humidity_pct == 45.0
        assert pkt.battery_v == 4.18

    def test_crc16(self):
        data = b"CANSAT_TELEMETRY_PACKET"
        crc1 = calculate_crc16(data)
        crc2 = calculate_crc16(data)
        assert crc1 == crc2
        assert isinstance(crc1, int)
        assert crc1 != calculate_crc16(b"CORRUPTED_PACKET")


class TestFlightStateEstimator:
    def test_apogee_and_parachute_detection(self):
        estimator = FlightStateEstimator(window_size=5)

        # Pad stage
        v, stage, ev = estimator.process_frame(0.0, 15.0, 1.0)
        assert stage == "LAUNCH_PAD"

        # Ascent stage
        estimator.process_frame(1.0, 100.0, 2.5)
        estimator.process_frame(2.0, 250.0, 2.5)
        estimator.process_frame(3.0, 400.0, 1.0)
        estimator.process_frame(4.0, 500.0, 0.5)
        v, stage, ev = estimator.process_frame(5.0, 550.0, 0.2)
        assert v > 0.0

        # Apogee transition across 5-sample rolling window
        estimator.process_frame(6.0, 548.0, 0.0)
        estimator.process_frame(7.0, 540.0, 0.0)
        estimator.process_frame(8.0, 530.0, 0.0)
        estimator.process_frame(9.0, 520.0, 0.0)
        v, stage, ev = estimator.process_frame(10.0, 510.0, 0.0)
        # Parachute transition and terminal descent
        assert estimator.apogee_detected is True
        assert estimator.parachute_detected is True
        assert stage == "PARACHUTE_DESCENT"
        assert v < 0.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
