from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import time

class TelemetryPacket(BaseModel):
    """
    Standard & Enriched Aerospace Telemetry Packet for CanSat Missions.
    Fully compatible with the original CanSat sensor suite, EKF kinematics,
    and distributed streaming pipeline (Redpanda / TimescaleDB / MinIO).
    """
    mission_id: str = "MISSION_ALPHA_01"
    packet_id: int = 1
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    altitude_m: float = 0.0
    pressure_hpa: float = 1013.25
    velocity_mps: Optional[float] = 0.0
    accel_x_g: float = 0.0
    accel_y_g: float = 0.0
    accel_z_g: float = 1.0
    gyro_x_dps: float = 0.0
    gyro_y_dps: float = 0.0
    gyro_z_dps: float = 0.0
    battery_v: float = 4.20
    temperature_c: float = 25.0
    flight_stage: Optional[str] = "LAUNCH_PAD"
    status: Optional[str] = "OK"

    # Enriched CanSat Aerospace Fields
    humidity_pct: Optional[float] = 50.0
    lat: Optional[float] = 22.5727
    lon: Optional[float] = 88.3655
    pitch_deg: Optional[float] = 0.0
    roll_deg: Optional[float] = 0.0
    accel_mag_g: Optional[float] = 1.0
    anomaly_score: Optional[float] = 0.0
    is_anomaly: Optional[bool] = False
    dew_point_c: Optional[float] = None
    air_density_kg_m3: Optional[float] = None
    lapse_rate_c_100m: Optional[float] = None
    calibrated_altitude_m: Optional[float] = None
    calibrated_vspd_mps: Optional[float] = None

    @classmethod
    def from_cansat_dict(cls, data: Dict[str, Any], mission_id: str = "MISSION_ALPHA_01", packet_id: Optional[int] = None) -> "TelemetryPacket":
        """
        Converts CanSat dictionary (from FastAPI, WebSocket, SQLite, or CSV)
        into a validated TelemetryPacket with robust schema mapping.
        """
        # Map timestamp
        ts_ms = data.get("timestamp_ms")
        if ts_ms is None:
            raw_ts = data.get("timestamp") or data.get("time")
            if isinstance(raw_ts, (int, float)):
                ts_ms = int(raw_ts * 1000) if raw_ts < 1e11 else int(raw_ts)
            else:
                ts_ms = int(time.time() * 1000)

        # Map altitude
        alt = float(data.get("altitude_m") if data.get("altitude_m") is not None else data.get("altitude", 0.0))
        cal_alt = float(data.get("calibrated_altitude", alt))

        # Map pressure & temperature
        press = float(data.get("pressure_hpa") if data.get("pressure_hpa") is not None else data.get("pressure", 1013.25))
        temp = float(data.get("temperature_c") if data.get("temperature_c") is not None else data.get("temp", 25.0))

        # Map kinematics
        vel = data.get("velocity_mps")
        if vel is None:
            vel = data.get("v_spd") if data.get("v_spd") is not None else data.get("vSpd", 0.0)
        vel = float(vel) if vel is not None else 0.0

        ax = float(data.get("accel_x_g") if data.get("accel_x_g") is not None else data.get("ax", 0.0))
        ay = float(data.get("accel_y_g") if data.get("accel_y_g") is not None else data.get("ay", 0.0))
        az = float(data.get("accel_z_g") if data.get("accel_z_g") is not None else data.get("az", 1.0))

        gx = float(data.get("gyro_x_dps") if data.get("gyro_x_dps") is not None else data.get("gx", 0.0))
        gy = float(data.get("gyro_y_dps") if data.get("gyro_y_dps") is not None else data.get("gy", 0.0))
        gz = float(data.get("gyro_z_dps") if data.get("gyro_z_dps") is not None else data.get("gz", 0.0))

        # Battery
        bat = data.get("battery_v")
        if bat is None:
            bat = data.get("batteryVoltage") if data.get("batteryVoltage") is not None else data.get("battery_voltage", 4.2)
        bat = float(bat)

        # Stage & Anomaly
        stage = data.get("flight_stage") or data.get("flight_phase") or data.get("flightPhase") or "LAUNCH_PAD"
        anom_score = float(data.get("anomaly_score") or data.get("anomalyScore") or 0.0)
        is_anom = bool(data.get("is_anomaly") or data.get("isAnomaly") or False)
        status = data.get("status")
        if not status:
            if is_anom:
                status = data.get("anomaly_type", "ANOMALY")
            else:
                status = "OK"

        return cls(
            mission_id=data.get("mission_id", mission_id),
            packet_id=int(data.get("packet_id", packet_id or 1)),
            timestamp_ms=int(ts_ms),
            altitude_m=alt,
            pressure_hpa=press,
            velocity_mps=vel,
            accel_x_g=ax,
            accel_y_g=ay,
            accel_z_g=az,
            gyro_x_dps=gx,
            gyro_y_dps=gy,
            gyro_z_dps=gz,
            battery_v=bat,
            temperature_c=temp,
            flight_stage=stage,
            status=status,
            humidity_pct=float(data.get("humidity", data.get("humidity_pct", 50.0))),
            lat=float(data.get("lat", 22.5727)),
            lon=float(data.get("lon", 88.3655)),
            pitch_deg=float(data.get("pitch", data.get("pitch_deg", 0.0))),
            roll_deg=float(data.get("roll", data.get("roll_deg", 0.0))),
            accel_mag_g=float(data.get("accel_mag", data.get("accelMag", (ax**2 + ay**2 + az**2)**0.5))),
            anomaly_score=anom_score,
            is_anomaly=is_anom,
            dew_point_c=float(data.get("dew_point", data.get("dew_point_c", 15.0))) if data.get("dew_point") is not None or data.get("dew_point_c") is not None else None,
            air_density_kg_m3=float(data.get("air_density", data.get("air_density_kg_m3", 1.225))) if data.get("air_density") is not None or data.get("air_density_kg_m3") is not None else None,
            lapse_rate_c_100m=float(data.get("lapse_rate", data.get("lapse_rate_c_100m", 0.65))) if data.get("lapse_rate") is not None or data.get("lapse_rate_c_100m") is not None else None,
            calibrated_altitude_m=cal_alt,
            calibrated_vspd_mps=float(data.get("calibrated_vspd", vel))
        )

    @classmethod
    def from_csv_line(cls, line: str, mission_id: str = "MISSION_ALPHA_01", packet_id: int = 1) -> "TelemetryPacket":
        """
        Parses CanSat raw 13-item CSV:
        temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, volt
        """
        parts = [float(x.strip()) for x in line.split(",") if x.strip()]
        if len(parts) >= 13:
            temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, volt = parts[:13]
            return cls(
                mission_id=mission_id,
                packet_id=packet_id,
                timestamp_ms=int(time.time() * 1000),
                altitude_m=alt,
                pressure_hpa=press,
                accel_x_g=ax,
                accel_y_g=ay,
                accel_z_g=az,
                gyro_x_dps=gx,
                gyro_y_dps=gy,
                gyro_z_dps=gz,
                battery_v=volt,
                temperature_c=temp,
                humidity_pct=hum,
                lat=lat,
                lon=lon,
                flight_stage="LAUNCH_PAD",
                status="OK"
            )
        raise ValueError(f"Expected at least 13 CSV items, got {len(parts)}: {line}")


def calculate_crc16(data: bytes) -> int:
    """CRC-16-CCITT implementation for RF packet verification"""
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc