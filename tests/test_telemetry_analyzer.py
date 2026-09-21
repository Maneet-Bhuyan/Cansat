"""
Deterministic Unit Test Suite for Telemetry Data Quality & Flight Reliability Analyzer
Validates the 10 mandatory edge cases with exact metric assertions.
"""

import unittest
import math
from backend.core.telemetry_analyzer import TelemetryQualityAnalyzer, TelemetryQualityReport


CSV_HEADER = "timestamp,temp,pressure,altitude,gx,gy,gz,ax,ay,az,lat,lon,humidity,batteryVoltage,pitch,roll,accelMag"


class TestTelemetryQualityAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = TelemetryQualityAnalyzer(nominal_interval_sec=0.8, gap_threshold_sec=2.0)

    # -------------------------------------------------------------------------
    # 1. Perfect Telemetry
    # -------------------------------------------------------------------------
    def test_01_perfect_telemetry(self):
        """Test dataset with 100% valid packets, no gaps, no missing sensors."""
        rows = [CSV_HEADER]
        times = [
            "2026-08-30T10:00:00.000Z",
            "2026-08-30T10:00:00.800Z",
            "2026-08-30T10:00:01.600Z",
            "2026-08-30T10:00:02.400Z",
            "2026-08-30T10:00:03.200Z"
        ]
        for t in times:
            rows.append(f"{t},25.00,1013.25,10.0,0.1,0.2,0.3,0.01,0.02,0.98,22.5727,88.3655,55.0,4.15,1.17,0.58,0.98")

        csv_str = "\n".join(rows)
        report = self.analyzer.analyze_csv_string(csv_str)

        self.assertEqual(report.status, "success")
        self.assertEqual(report.packet_integrity.total_rows, 5)
        self.assertEqual(report.packet_integrity.valid_packets, 5)
        self.assertEqual(report.packet_integrity.corrupted_rows, 0)
        self.assertEqual(report.packet_integrity.duplicate_packets, 0)
        self.assertEqual(report.packet_integrity.missing_packets_estimate, 0)
        self.assertEqual(report.packet_integrity.packet_completeness_pct, 100.0)

        # Temporal integrity
        self.assertEqual(report.temporal_integrity.timestamp_count, 5)
        self.assertAlmostEqual(report.temporal_integrity.mean_interval_sec, 0.8, places=3)
        self.assertAlmostEqual(report.temporal_integrity.median_interval_sec, 0.8, places=3)
        self.assertAlmostEqual(report.temporal_integrity.min_interval_sec, 0.8, places=3)
        self.assertAlmostEqual(report.temporal_integrity.max_interval_sec, 0.8, places=3)
        self.assertEqual(report.temporal_integrity.gap_count, 0)
        self.assertEqual(report.temporal_integrity.irregular_intervals_count, 0)

        # Sensor completeness
        for col in ["temp", "pressure", "altitude", "batteryVoltage"]:
            fc = report.sensor_completeness[col]
            self.assertEqual(fc.non_null_count, 5)
            self.assertEqual(fc.missing_count, 0)
            self.assertEqual(fc.availability_pct, 100.0)
            self.assertEqual(fc.out_of_range_count, 0)

        self.assertAlmostEqual(report.flight_duration.duration_sec, 3.2, places=2)
        self.assertEqual(len(report.sensor_dropouts), 0)

    # -------------------------------------------------------------------------
    # 2. Missing Packet
    # -------------------------------------------------------------------------
    def test_02_missing_packet(self):
        """Test detection of sequence jump: 1 packet dropped (interval 1.6s vs 0.8s)."""
        # Nominal is 0.8s. A jump from 0.8s to 2.4s (gap of 1.6s) means 1 missing packet.
        # With gap threshold = 1.5s:
        analyzer = TelemetryQualityAnalyzer(nominal_interval_sec=0.8, gap_threshold_sec=1.5)
        rows = [
            CSV_HEADER,
            "2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:00.800Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            # Dropped: 01.600Z
            "2026-08-30T10:00:02.400Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = analyzer.analyze_csv_string("\n".join(rows))

        self.assertEqual(report.packet_integrity.total_rows, 3)
        self.assertEqual(report.packet_integrity.valid_packets, 3)
        self.assertEqual(report.temporal_integrity.gap_count, 1)
        self.assertEqual(report.packet_integrity.missing_packets_estimate, 1)
        # Expected total was 4 packets, valid is 3 -> 75%
        self.assertAlmostEqual(report.packet_integrity.packet_completeness_pct, 75.0, places=1)
        gap = report.temporal_integrity.timestamp_gaps[0]
        self.assertAlmostEqual(gap["interval_sec"], 1.6, places=2)
        self.assertEqual(gap["missing_packets_estimate"], 1)

    # -------------------------------------------------------------------------
    # 3. Duplicate Packet
    # -------------------------------------------------------------------------
    def test_03_duplicate_packet(self):
        """Test detection of exact duplicate packet and repeated timestamps."""
        rows = [
            CSV_HEADER,
            "2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:00.800Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            # Duplicate of the previous packet
            "2026-08-30T10:00:00.800Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:01.600Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = self.analyzer.analyze_csv_string("\n".join(rows))

        self.assertEqual(report.packet_integrity.total_rows, 4)
        self.assertEqual(report.packet_integrity.duplicate_packets, 1)
        self.assertIn("1 duplicate telemetry packets detected.", report.issues_log[0])

    # -------------------------------------------------------------------------
    # 4. Timestamp Gap
    # -------------------------------------------------------------------------
    def test_04_timestamp_gap(self):
        """Test large timestamp outage exceeding gap threshold (> 2.0s)."""
        rows = [
            CSV_HEADER,
            "2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:00.800Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            # Gap of 4.0 seconds (dropped: 1.6, 2.4, 3.2, 4.0 -> 4 packets missing)
            "2026-08-30T10:00:04.800Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = self.analyzer.analyze_csv_string("\n".join(rows))

        self.assertEqual(report.temporal_integrity.gap_count, 1)
        self.assertAlmostEqual(report.temporal_integrity.max_interval_sec, 4.0, places=2)
        gap = report.temporal_integrity.timestamp_gaps[0]
        self.assertAlmostEqual(gap["interval_sec"], 4.0, places=2)
        self.assertEqual(gap["missing_packets_estimate"], 4)
        self.assertEqual(report.packet_integrity.missing_packets_estimate, 4)

    # -------------------------------------------------------------------------
    # 5. Missing Sensor Value
    # -------------------------------------------------------------------------
    def test_05_missing_sensor_value(self):
        """Test single missing field (empty value or NaN in temp)."""
        rows = [
            CSV_HEADER,
            "2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            # Empty temperature value
            "2026-08-30T10:00:00.800Z,,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:01.600Z,24.8,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:02.400Z,24.7,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = self.analyzer.analyze_csv_string("\n".join(rows))

        temp_fc = report.sensor_completeness["temp"]
        self.assertEqual(temp_fc.total_samples, 4)
        self.assertEqual(temp_fc.non_null_count, 3)
        self.assertEqual(temp_fc.missing_count, 1)
        self.assertAlmostEqual(temp_fc.availability_pct, 75.0, places=1)
        self.assertEqual(report.numeric_validity.nan_count, 1)
        # Pressure should still be 100%
        self.assertEqual(report.sensor_completeness["pressure"].availability_pct, 100.0)

    # -------------------------------------------------------------------------
    # 6. Multiple Missing Sensor Values
    # -------------------------------------------------------------------------
    def test_06_multiple_missing_sensor_values(self):
        """Test multiple missing sensor fields across multiple rows."""
        rows = [
            CSV_HEADER,
            # Row 0: missing altitude
            "2026-08-30T10:00:00.000Z,25.0,1013.2,,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            # Row 1: missing gx, gy
            "2026-08-30T10:00:00.800Z,25.0,1013.2,10.0,,,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            # Row 2: missing humidity, batteryVoltage
            "2026-08-30T10:00:01.600Z,24.8,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,,,0,0,1",
            # Row 3: fully populated
            "2026-08-30T10:00:02.400Z,24.7,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = self.analyzer.analyze_csv_string("\n".join(rows))

        self.assertEqual(report.sensor_completeness["altitude"].missing_count, 1)
        self.assertEqual(report.sensor_completeness["gx"].missing_count, 1)
        self.assertEqual(report.sensor_completeness["gy"].missing_count, 1)
        self.assertEqual(report.sensor_completeness["humidity"].missing_count, 1)
        self.assertEqual(report.sensor_completeness["batteryVoltage"].missing_count, 1)
        self.assertEqual(report.numeric_validity.nan_count, 5)
        # Total valid rows without corruption = 1 (only Row 3 had no NaNs)
        self.assertEqual(report.packet_integrity.valid_packets, 1)

    # -------------------------------------------------------------------------
    # 7. Invalid Numeric Value
    # -------------------------------------------------------------------------
    def test_07_invalid_numeric_value(self):
        """Test non-numeric string tokens like 'CORRUPT' and 'ERR' in numeric columns."""
        rows = [
            CSV_HEADER,
            "2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:00.800Z,CORRUPT,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "2026-08-30T10:00:01.600Z,25.0,ERR,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = self.analyzer.analyze_csv_string("\n".join(rows))

        self.assertEqual(report.numeric_validity.non_numeric_count, 2)
        self.assertEqual(report.sensor_completeness["temp"].non_numeric_count, 1)
        self.assertEqual(report.sensor_completeness["pressure"].non_numeric_count, 1)
        self.assertEqual(report.packet_integrity.valid_packets, 1)

    # -------------------------------------------------------------------------
    # 8. Empty Dataset
    # -------------------------------------------------------------------------
    def test_08_empty_dataset(self):
        """Test empty string and header-only CSVs."""
        report_empty_str = self.analyzer.analyze_csv_string("")
        self.assertEqual(report_empty_str.status, "empty")
        self.assertEqual(report_empty_str.packet_integrity.total_rows, 0)

        report_header_only = self.analyzer.analyze_csv_string(CSV_HEADER)
        self.assertEqual(report_header_only.status, "empty")
        self.assertEqual(report_header_only.packet_integrity.total_rows, 0)

    # -------------------------------------------------------------------------
    # 9. Malformed CSV
    # -------------------------------------------------------------------------
    def test_09_malformed_csv(self):
        """Test malformed CSV containing rows with irregular column counts or delimiters."""
        rows = [
            CSV_HEADER,
            "2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
            "malformed;semicolon;row;with;too;few;tokens",
            "2026-08-30T10:00:01.600Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1,EXTRA,TOKENS,HERE",
            "2026-08-30T10:00:02.400Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1",
        ]
        report = self.analyzer.analyze_csv_string("\n".join(rows))

        self.assertGreater(report.numeric_validity.malformed_rows_count, 0)
        self.assertGreater(report.packet_integrity.corrupted_rows, 0)
        # At least the 2 clean rows parsed
        self.assertGreaterEqual(report.packet_integrity.valid_packets, 1)

    # -------------------------------------------------------------------------
    # 10. Single-Row Dataset
    # -------------------------------------------------------------------------
    def test_10_single_row_dataset(self):
        """Test single-row dataset: verifies zero-division protection on delta-t and duration."""
        single_row = f"{CSV_HEADER}\n2026-08-30T10:00:00.000Z,25.0,1013.2,10.0,0,0,0,0,0,1,22.5,88.3,50,4.1,0,0,1"
        report = self.analyzer.analyze_csv_string(single_row)

        self.assertEqual(report.status, "success")
        self.assertEqual(report.packet_integrity.total_rows, 1)
        self.assertEqual(report.packet_integrity.valid_packets, 1)
        self.assertEqual(report.temporal_integrity.timestamp_count, 1)
        # Intervals cannot be calculated on N=1, should be None without raising ZeroDivisionError
        self.assertIsNone(report.temporal_integrity.mean_interval_sec)
        self.assertIsNone(report.temporal_integrity.median_interval_sec)
        self.assertEqual(report.temporal_integrity.gap_count, 0)
        self.assertEqual(report.flight_duration.duration_sec, 0.0)

    # -------------------------------------------------------------------------
    # Additional: GNSS Lock Loss & Battery Sag Dropouts
    # -------------------------------------------------------------------------
    def test_sensor_dropouts_detection(self):
        """Test GNSS lock loss ((0,0) coordinates) and LiPo voltage sag (< 3.4V)."""
        rows = [CSV_HEADER]
        for i in range(10):
            t_sec = i * 0.8
            # GNSS drops out at index 4, 5, 6
            lat = 0.0 if 4 <= i <= 6 else 22.5727
            lon = 0.0 if 4 <= i <= 6 else 88.3655
            # Voltage sags at index 7, 8, 9
            v_bat = 3.30 if i >= 7 else 4.10
            rows.append(f"2026-08-30T10:00:0{t_sec:.1f}Z,25.0,1013.2,10.0,0,0,0,0,0,1,{lat},{lon},50,{v_bat},0,0,1")

        report = self.analyzer.analyze_csv_string("\n".join(rows))

        dropout_types = [d["dropout_type"] for d in report.sensor_dropouts]
        self.assertIn("GNSS_FIX_LOSS", dropout_types)
        self.assertIn("BATTERY_VOLTAGE_SAG", dropout_types)

        gps_dropout = next(d for d in report.sensor_dropouts if d["dropout_type"] == "GNSS_FIX_LOSS")
        self.assertEqual(gps_dropout["packet_count"], 3)
        self.assertEqual(gps_dropout["start_index"], 4)
        self.assertEqual(gps_dropout["end_index"], 6)

        sag_dropout = next(d for d in report.sensor_dropouts if d["dropout_type"] == "BATTERY_VOLTAGE_SAG")
        self.assertEqual(sag_dropout["packet_count"], 3)


if __name__ == "__main__":
    unittest.main()
