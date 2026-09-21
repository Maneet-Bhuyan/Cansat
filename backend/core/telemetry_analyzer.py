"""
Telemetry Data Quality & Flight Reliability Analyzer
Cognitive CanSat Mission Control - Ground Station Analytics Engine

Provides objective, mathematically rigorous evaluation of sounding pico-satellite
telemetry and flight CSV datasets before downstream machine learning inference
and aerodynamic post-flight reconstruction.
"""

from __future__ import annotations

import io
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


PRIMARY_TELEMETRY_FIELDS = [
    "temp", "pressure", "altitude",
    "gx", "gy", "gz",
    "ax", "ay", "az",
    "lat", "lon", "humidity", "batteryVoltage"
]

DERIVED_TELEMETRY_FIELDS = [
    "pitch", "roll", "accelMag"
]

# Standard hardware / operational envelope boundaries based on CanSat onboard sensors:
# BMP180 / BMP280, DHT11 / SHT31, MPU6050 6-DOF IMU, u-blox NEO-6M GNSS, 1S LiPo
DEFAULT_PHYSICAL_BOUNDS: Dict[str, Tuple[float, float]] = {
    "temp": (-50.0, 85.0),           # °C (operational range for BMP/DHT)
    "pressure": (10.0, 1150.0),       # hPa (low vacuum sounding to sea-level high pressure)
    "altitude": (-100.0, 45000.0),    # m (pad elevation to stratospheric sounding ceiling)
    "gx": (-2000.0, 2000.0),          # °/s (MPU6050 full-scale gyro range)
    "gy": (-2000.0, 2000.0),          # °/s
    "gz": (-2000.0, 2000.0),          # °/s
    "ax": (-16.0, 16.0),              # G (MPU6050 full-scale accel range)
    "ay": (-16.0, 16.0),              # G
    "az": (-16.0, 16.0),              # G
    "lat": (-90.0, 90.0),             # WGS84 latitude degrees
    "lon": (-180.0, 180.0),           # WGS84 longitude degrees
    "humidity": (0.0, 100.0),         # Relative humidity %
    "batteryVoltage": (3.00, 4.35),   # Volts (1S LiPo operational envelope)
}


@dataclass
class PacketIntegrityReport:
    total_rows: int = 0
    valid_packets: int = 0
    corrupted_rows: int = 0
    duplicate_packets: int = 0
    missing_packets_estimate: int = 0
    packet_completeness_pct: float = 0.0


@dataclass
class TemporalGap:
    start_index: int
    end_index: int
    start_timestamp: str
    end_timestamp: str
    interval_sec: float
    missing_packets_estimate: int


@dataclass
class TemporalIntegrityReport:
    timestamp_count: int = 0
    nominal_interval_sec: float = 0.8
    mean_interval_sec: Optional[float] = None
    median_interval_sec: Optional[float] = None
    min_interval_sec: Optional[float] = None
    max_interval_sec: Optional[float] = None
    std_interval_sec: Optional[float] = None
    timestamp_gaps: List[Dict[str, Any]] = field(default_factory=list)
    gap_count: int = 0
    irregular_intervals_count: int = 0


@dataclass
class FieldCompleteness:
    field_name: str
    total_samples: int = 0
    non_null_count: int = 0
    missing_count: int = 0
    availability_pct: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    out_of_range_count: int = 0
    non_numeric_count: int = 0


@dataclass
class NumericValidityReport:
    nan_count: int = 0
    inf_count: int = 0
    non_numeric_count: int = 0
    malformed_rows_count: int = 0


@dataclass
class FlightDurationReport:
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    duration_sec: float = 0.0


@dataclass
class SensorDropoutEvent:
    sensor: str
    dropout_type: str
    start_index: int
    end_index: int
    start_timestamp: Optional[str]
    end_timestamp: Optional[str]
    duration_sec: float
    packet_count: int
    description: str


@dataclass
class TelemetryQualityReport:
    status: str
    packet_integrity: PacketIntegrityReport = field(default_factory=PacketIntegrityReport)
    temporal_integrity: TemporalIntegrityReport = field(default_factory=TemporalIntegrityReport)
    sensor_completeness: Dict[str, FieldCompleteness] = field(default_factory=dict)
    numeric_validity: NumericValidityReport = field(default_factory=NumericValidityReport)
    flight_duration: FlightDurationReport = field(default_factory=FlightDurationReport)
    sensor_dropouts: List[Dict[str, Any]] = field(default_factory=list)
    issues_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report dataclass to JSON-serializable dictionary."""
        d = asdict(self)
        if d["packet_integrity"]["packet_completeness_pct"] is not None:
            d["packet_integrity"]["packet_completeness_pct"] = round(d["packet_integrity"]["packet_completeness_pct"], 2)
        if d["temporal_integrity"]["mean_interval_sec"] is not None:
            d["temporal_integrity"]["mean_interval_sec"] = round(d["temporal_integrity"]["mean_interval_sec"], 3)
        if d["temporal_integrity"]["median_interval_sec"] is not None:
            d["temporal_integrity"]["median_interval_sec"] = round(d["temporal_integrity"]["median_interval_sec"], 3)
        if d["temporal_integrity"]["min_interval_sec"] is not None:
            d["temporal_integrity"]["min_interval_sec"] = round(d["temporal_integrity"]["min_interval_sec"], 3)
        if d["temporal_integrity"]["max_interval_sec"] is not None:
            d["temporal_integrity"]["max_interval_sec"] = round(d["temporal_integrity"]["max_interval_sec"], 3)
        if d["temporal_integrity"]["std_interval_sec"] is not None:
            d["temporal_integrity"]["std_interval_sec"] = round(d["temporal_integrity"]["std_interval_sec"], 3)
        if d["flight_duration"]["duration_sec"] is not None:
            d["flight_duration"]["duration_sec"] = round(d["flight_duration"]["duration_sec"], 2)

        for col, fc in d["sensor_completeness"].items():
            if fc["availability_pct"] is not None:
                fc["availability_pct"] = round(fc["availability_pct"], 2)
            if fc["min_value"] is not None:
                fc["min_value"] = round(fc["min_value"], 3)
            if fc["max_value"] is not None:
                fc["max_value"] = round(fc["max_value"], 3)
            if fc["mean_value"] is not None:
                fc["mean_value"] = round(fc["mean_value"], 3)
        return d


class TelemetryQualityAnalyzer:
    """
    Evaluates telemetry data quality, completeness, and temporal continuity
    without subjective heuristic scoring.
    """

    def __init__(
        self,
        nominal_interval_sec: float = 0.8,
        gap_threshold_sec: float = 2.0,
        physical_bounds: Optional[Dict[str, Tuple[float, float]]] = None
    ):
        self.nominal_dt = float(nominal_interval_sec)
        self.gap_threshold = float(gap_threshold_sec)
        self.physical_bounds = physical_bounds or DEFAULT_PHYSICAL_BOUNDS

    def analyze_file(self, csv_filepath: str) -> TelemetryQualityReport:
        """Analyze a telemetry CSV file from disk."""
        if not os.path.exists(csv_filepath):
            report = TelemetryQualityReport(status="error")
            report.issues_log.append(f"File not found: {csv_filepath}")
            return report

        try:
            with open(csv_filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return self.analyze_csv_string(content)
        except Exception as e:
            report = TelemetryQualityReport(status="error")
            report.issues_log.append(f"Failed to read file: {str(e)}")
            return report

    def analyze_csv_string(self, csv_text: str) -> TelemetryQualityReport:
        """Analyze raw CSV string content."""
        if not csv_text or not csv_text.strip():
            report = TelemetryQualityReport(status="empty")
            report.issues_log.append("Dataset is empty: 0 rows provided.")
            return report

        lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
        if not lines:
            report = TelemetryQualityReport(status="empty")
            report.issues_log.append("Dataset is empty: 0 valid lines found.")
            return report

        # Check header
        header_line = lines[0]
        header_tokens = [h.strip() for h in header_line.split(",")]
        is_header = any(col in header_tokens for col in PRIMARY_TELEMETRY_FIELDS or col == "timestamp")

        # Fallback for 13-field headerless raw telemetry lines
        if not is_header and len(header_tokens) == 13:
            csv_io = io.StringIO("timestamp," + ",".join(PRIMARY_TELEMETRY_FIELDS) + "\n" + csv_text)
        else:
            csv_io = io.StringIO(csv_text)

        malformed_count = 0
        try:
            df = pd.read_csv(csv_io, on_bad_lines="skip")
            raw_line_count = len(lines) - (1 if is_header else 0)
            parsed_count = len(df)
            malformed_count = max(0, raw_line_count - parsed_count)
        except Exception as e:
            report = TelemetryQualityReport(status="malformed")
            report.numeric_validity.malformed_rows_count = len(lines)
            report.issues_log.append(f"Malformed CSV syntax: {str(e)}")
            return report

        return self.analyze_dataframe(df, initial_malformed_count=malformed_count, raw_rows_count=len(lines) - (1 if is_header else 0))

    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        initial_malformed_count: int = 0,
        raw_rows_count: Optional[int] = None
    ) -> TelemetryQualityReport:
        """
        Evaluate telemetry quality on a pandas DataFrame.
        """
        report = TelemetryQualityReport(status="success")
        total_rows = len(df)
        if raw_rows_count is not None:
            report.packet_integrity.total_rows = raw_rows_count
        else:
            report.packet_integrity.total_rows = total_rows + initial_malformed_count

        report.numeric_validity.malformed_rows_count = initial_malformed_count
        report.packet_integrity.corrupted_rows = initial_malformed_count

        if total_rows == 0:
            report.status = "empty"
            report.issues_log.append("Dataset contains 0 rows after header parsing.")
            return report

        # Normalize column names: strip whitespace
        df.columns = [c.strip() for c in df.columns]

        # ---------------------------------------------------------------------
        # 1. Packet Integrity & Duplication
        # ---------------------------------------------------------------------
        dup_rows_mask = df.duplicated()
        duplicate_rows_count = int(dup_rows_mask.sum())

        dup_timestamps_count = 0
        if "timestamp" in df.columns:
            dup_ts_mask = df["timestamp"].duplicated()
            dup_timestamps_count = int(dup_ts_mask.sum())

        report.packet_integrity.duplicate_packets = max(duplicate_rows_count, dup_timestamps_count)
        if report.packet_integrity.duplicate_packets > 0:
            report.issues_log.append(
                f"{report.packet_integrity.duplicate_packets} duplicate telemetry packets detected."
            )

        # ---------------------------------------------------------------------
        # 2. Temporal Integrity & Flight Duration
        # ---------------------------------------------------------------------
        timestamps: List[datetime] = []
        valid_ts_indices: List[int] = []
        has_timestamps = "timestamp" in df.columns

        if has_timestamps:
            raw_ts = df["timestamp"]
            for idx, val in enumerate(raw_ts):
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                dt_obj = self._parse_iso_timestamp(val_str)
                if dt_obj is not None:
                    timestamps.append(dt_obj)
                    valid_ts_indices.append(idx)

            report.temporal_integrity.timestamp_count = len(timestamps)

            if len(timestamps) > 0:
                report.flight_duration.start_timestamp = timestamps[0].isoformat()
                report.flight_duration.end_timestamp = timestamps[-1].isoformat()
                duration = (timestamps[-1] - timestamps[0]).total_seconds()
                report.flight_duration.duration_sec = max(0.0, duration)

            if len(timestamps) >= 2:
                intervals: List[float] = []
                for i in range(1, len(timestamps)):
                    dt = (timestamps[i] - timestamps[i - 1]).total_seconds()
                    intervals.append(dt)

                intervals_arr = np.array(intervals)
                report.temporal_integrity.mean_interval_sec = float(np.mean(intervals_arr))
                report.temporal_integrity.median_interval_sec = float(np.median(intervals_arr))
                report.temporal_integrity.min_interval_sec = float(np.min(intervals_arr))
                report.temporal_integrity.max_interval_sec = float(np.max(intervals_arr))
                report.temporal_integrity.std_interval_sec = float(np.std(intervals_arr))
                report.temporal_integrity.nominal_interval_sec = self.nominal_dt

                total_lost_packets_estimate = 0
                gaps: List[Dict[str, Any]] = []

                for i, dt in enumerate(intervals):
                    if dt >= self.gap_threshold:
                        missing_est = max(1, int(round(dt / self.nominal_dt)) - 1)
                        total_lost_packets_estimate += missing_est
                        gap_entry = {
                            "start_index": valid_ts_indices[i],
                            "end_index": valid_ts_indices[i + 1],
                            "start_timestamp": timestamps[i].isoformat(),
                            "end_timestamp": timestamps[i + 1].isoformat(),
                            "interval_sec": round(dt, 3),
                            "missing_packets_estimate": missing_est,
                        }
                        gaps.append(gap_entry)

                report.temporal_integrity.timestamp_gaps = gaps
                report.temporal_integrity.gap_count = len(gaps)
                report.packet_integrity.missing_packets_estimate = total_lost_packets_estimate

                if len(gaps) > 0:
                    report.issues_log.append(
                        f"{len(gaps)} timestamp gap(s) exceeding {self.gap_threshold}s threshold detected "
                        f"(estimated {total_lost_packets_estimate} lost packet(s))."
                    )

                med_dt = report.temporal_integrity.median_interval_sec or self.nominal_dt
                irregular_count = int(np.sum((intervals_arr < med_dt * 0.8) | (intervals_arr > med_dt * 1.2)))
                report.temporal_integrity.irregular_intervals_count = irregular_count

        # ---------------------------------------------------------------------
        # 3. Numeric Validity & Sensor Completeness
        # ---------------------------------------------------------------------
        evaluated_fields = [col for col in PRIMARY_TELEMETRY_FIELDS if col in df.columns]
        for derived_col in DERIVED_TELEMETRY_FIELDS:
            if derived_col in df.columns and derived_col not in evaluated_fields:
                evaluated_fields.append(derived_col)

        total_nans = 0
        total_infs = 0
        total_non_numeric = 0
        corrupted_row_indices = set()

        for field_name in evaluated_fields:
            col_series = df[field_name]
            non_null_count = 0
            missing_count = 0
            out_of_range_count = 0
            field_non_numeric = 0
            valid_numeric_values: List[float] = []

            for row_idx, val in enumerate(col_series):
                if pd.isna(val) or val is None or str(val).strip() == "":
                    missing_count += 1
                    total_nans += 1
                    corrupted_row_indices.add(row_idx)
                    continue

                try:
                    num_val = float(val)
                    if math.isnan(num_val):
                        missing_count += 1
                        total_nans += 1
                        corrupted_row_indices.add(row_idx)
                    elif math.isinf(num_val):
                        total_infs += 1
                        corrupted_row_indices.add(row_idx)
                    else:
                        non_null_count += 1
                        valid_numeric_values.append(num_val)

                        if field_name in self.physical_bounds:
                            p_min, p_max = self.physical_bounds[field_name]
                            if num_val < p_min or num_val > p_max:
                                out_of_range_count += 1
                except (ValueError, TypeError):
                    field_non_numeric += 1
                    total_non_numeric += 1
                    corrupted_row_indices.add(row_idx)

            avail_pct = (non_null_count / total_rows * 100.0) if total_rows > 0 else 0.0

            fc = FieldCompleteness(
                field_name=field_name,
                total_samples=total_rows,
                non_null_count=non_null_count,
                missing_count=missing_count,
                availability_pct=avail_pct,
                min_value=float(np.min(valid_numeric_values)) if valid_numeric_values else None,
                max_value=float(np.max(valid_numeric_values)) if valid_numeric_values else None,
                mean_value=float(np.mean(valid_numeric_values)) if valid_numeric_values else None,
                out_of_range_count=out_of_range_count,
                non_numeric_count=field_non_numeric
            )
            report.sensor_completeness[field_name] = fc

            if missing_count > 0:
                report.issues_log.append(
                    f"Field '{field_name}': {missing_count} missing sample(s) (Availability: {round(avail_pct, 1)}%)."
                )
            if out_of_range_count > 0:
                p_min, p_max = self.physical_bounds.get(field_name, (0, 0))
                report.issues_log.append(
                    f"Field '{field_name}': {out_of_range_count} sample(s) outside physical operational envelope [{p_min}, {p_max}]."
                )

        report.numeric_validity.nan_count = total_nans
        report.numeric_validity.inf_count = total_infs
        report.numeric_validity.non_numeric_count = total_non_numeric

        valid_packets_count = total_rows - len(corrupted_row_indices)
        report.packet_integrity.valid_packets = max(0, valid_packets_count)
        report.packet_integrity.corrupted_rows += len(corrupted_row_indices)

        expected_total = (
            report.packet_integrity.valid_packets +
            report.packet_integrity.corrupted_rows +
            report.packet_integrity.missing_packets_estimate
        )
        if expected_total > 0:
            report.packet_integrity.packet_completeness_pct = (
                report.packet_integrity.valid_packets / expected_total
            ) * 100.0
        else:
            report.packet_integrity.packet_completeness_pct = 0.0

        # ---------------------------------------------------------------------
        # 4. Sensor Dropout Detection
        # ---------------------------------------------------------------------
        dropouts: List[Dict[str, Any]] = []

        if "lat" in df.columns and "lon" in df.columns:
            lats = pd.to_numeric(df["lat"], errors="coerce").fillna(0.0).values
            lons = pd.to_numeric(df["lon"], errors="coerce").fillna(0.0).values
            is_gps_loss = (np.abs(lats) < 1e-5) & (np.abs(lons) < 1e-5)

            gps_dropout_runs = self._find_consecutive_true_runs(is_gps_loss)
            for start_idx, end_idx, length in gps_dropout_runs:
                if length >= 2:
                    start_ts = timestamps[start_idx].isoformat() if start_idx < len(timestamps) else None
                    end_ts = timestamps[end_idx].isoformat() if end_idx < len(timestamps) else None
                    dur_sec = (
                        (timestamps[end_idx] - timestamps[start_idx]).total_seconds()
                        if (start_idx < len(timestamps) and end_idx < len(timestamps))
                        else (length * self.nominal_dt)
                    )
                    dropouts.append({
                        "sensor": "GPS (lat/lon)",
                        "dropout_type": "GNSS_FIX_LOSS",
                        "start_index": int(start_idx),
                        "end_index": int(end_idx),
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "duration_sec": round(dur_sec, 2),
                        "packet_count": int(length),
                        "description": f"GNSS coordinates reported (0.0, 0.0) across {length} consecutive packets (~{round(dur_sec, 1)}s)."
                    })
                    report.issues_log.append(
                        f"GNSS fix loss detected for {round(dur_sec, 1)}s ({length} packets) starting at index {start_idx}."
                    )

        for field_name in evaluated_fields:
            vals = df[field_name]
            is_missing = vals.isna() | vals.isin([float("nan"), float("inf"), float("-inf")])
            missing_runs = self._find_consecutive_true_runs(is_missing.values)
            for start_idx, end_idx, length in missing_runs:
                if length >= 3:
                    start_ts = timestamps[start_idx].isoformat() if start_idx < len(timestamps) else None
                    end_ts = timestamps[end_idx].isoformat() if end_idx < len(timestamps) else None
                    dur_sec = (
                        (timestamps[end_idx] - timestamps[start_idx]).total_seconds()
                        if (start_idx < len(timestamps) and end_idx < len(timestamps))
                        else (length * self.nominal_dt)
                    )
                    dropouts.append({
                        "sensor": field_name,
                        "dropout_type": "SENSOR_DISCONNECTED",
                        "start_index": int(start_idx),
                        "end_index": int(end_idx),
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "duration_sec": round(dur_sec, 2),
                        "packet_count": int(length),
                        "description": f"Field '{field_name}' absent for {length} consecutive packets."
                    })

        if "batteryVoltage" in df.columns:
            v_bats = pd.to_numeric(df["batteryVoltage"], errors="coerce").values
            is_sag = (v_bats < 3.40) & ~np.isnan(v_bats)
            sag_runs = self._find_consecutive_true_runs(is_sag)
            for start_idx, end_idx, length in sag_runs:
                if length >= 2:
                    min_v = float(np.min(v_bats[start_idx:end_idx + 1]))
                    start_ts = timestamps[start_idx].isoformat() if start_idx < len(timestamps) else None
                    end_ts = timestamps[end_idx].isoformat() if end_idx < len(timestamps) else None
                    dur_sec = (
                        (timestamps[end_idx] - timestamps[start_idx]).total_seconds()
                        if (start_idx < len(timestamps) and end_idx < len(timestamps))
                        else (length * self.nominal_dt)
                    )
                    dropouts.append({
                        "sensor": "batteryVoltage",
                        "dropout_type": "BATTERY_VOLTAGE_SAG",
                        "start_index": int(start_idx),
                        "end_index": int(end_idx),
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "duration_sec": round(dur_sec, 2),
                        "packet_count": int(length),
                        "description": f"Battery voltage sagged below 3.40V safety threshold (minimum observed: {round(min_v, 3)}V)."
                    })
                    report.issues_log.append(
                        f"Battery voltage sag below 3.40V observed across {length} packets (lowest: {round(min_v, 3)}V)."
                    )

        report.sensor_dropouts = dropouts
        return report

    @staticmethod
    def _parse_iso_timestamp(ts_str: str) -> Optional[datetime]:
        """Parse ISO 8601 timestamp string robustly."""
        if not ts_str:
            return None
        cleaned = ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str
        try:
            return datetime.fromisoformat(cleaned)
        except Exception:
            try:
                dt = pd.to_datetime(ts_str)
                if pd.isna(dt):
                    return None
                return dt.to_pydatetime()
            except Exception:
                try:
                    sec = float(ts_str)
                    return datetime.fromtimestamp(sec)
                except Exception:
                    return None

    @staticmethod
    def _find_consecutive_true_runs(bool_arr: np.ndarray) -> List[Tuple[int, int, int]]:
        """
        Find contiguous runs of True in a boolean array.
        Returns list of (start_idx, end_idx, length).
        """
        runs: List[Tuple[int, int, int]] = []
        if len(bool_arr) == 0:
            return runs

        in_run = False
        start_idx = 0

        for i, val in enumerate(bool_arr):
            if val and not in_run:
                in_run = True
                start_idx = i
            elif not val and in_run:
                in_run = False
                runs.append((start_idx, i - 1, i - start_idx))

        if in_run:
            runs.append((start_idx, len(bool_arr) - 1, len(bool_arr) - start_idx))

        return runs
