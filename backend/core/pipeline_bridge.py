"""
Cognitive CanSat - Distributed Telemetry Pipeline Bridge
-------------------------------------------------------
Thread-safe, asynchronous outbound bridge connecting CanSat Mission Control
to the Redpanda / Kafka distributed message broker, TimescaleDB hot path,
and MinIO S3 cold path lakehouse.
"""

import os
import json
import time
import queue
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger("PipelineBridge")

try:
    from kafka import KafkaProducer
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False
    logger.warning("kafka-python-ng not installed; running in pipeline simulation mode.")


class PipelineBridge:
    """
    Non-blocking background pipeline bridge for high-throughput aerospace telemetry.
    Queues outgoing packets and events, handles auto-reconnection to Redpanda/Kafka,
    and provides real-time health telemetry to the Mission Control HUD.
    """

    def __init__(
        self,
        broker: Optional[str] = None,
        telemetry_topic: str = "cansat.telemetry.raw",
        events_topic: str = "cansat.telemetry.events",
        queue_size: int = 5000,
        enabled: bool = True
    ):
        self.broker = broker or os.environ.get("CANSAT_KAFKA_BROKER", "localhost:19092")
        self.telemetry_topic = telemetry_topic
        self.events_topic = events_topic
        self.enabled = enabled

        self._queue = queue.Queue(maxsize=queue_size)
        self._producer: Optional[Any] = None
        self._running = False
        self._connected = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Telemetry metrics
        self.packets_queued = 0
        self.packets_sent = 0
        self.packets_dropped = 0
        self.events_sent = 0
        self.errors = 0
        self.last_error: Optional[str] = None
        self.last_sent_timestamp: Optional[float] = None
        self.current_packet_id = 0

    def start(self) -> None:
        """Start the background producer dispatcher thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._dispatch_loop,
                name="PipelineBridge-Worker",
                daemon=True
            )
            self._worker_thread.start()
            logger.info(f"[PipelineBridge] Worker started. Target broker: {self.broker}")

    def stop(self) -> None:
        """Gracefully stop the background worker thread."""
        with self._lock:
            self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.5)
        self._close_producer()
        logger.info("[PipelineBridge] Worker stopped.")

    def _close_producer(self) -> None:
        with self._lock:
            if self._producer:
                try:
                    self._producer.flush(timeout=1.0)
                    self._producer.close(timeout=1.0)
                except Exception:
                    pass
                self._producer = None
            self._connected = False

    def _get_or_create_producer(self) -> bool:
        if not HAS_KAFKA or not self.enabled:
            return False

        if self._producer is not None:
            return True

        try:
            self._producer = KafkaProducer(
                bootstrap_servers=[self.broker],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks=1,
                request_timeout_ms=1500,
                max_block_ms=1500
            )
            self._connected = True
            logger.info(f"[PipelineBridge] [+] Connected to Redpanda/Kafka broker at {self.broker}")
            return True
        except Exception as e:
            self._connected = False
            self.last_error = f"Connection failed: {str(e)}"
            return False

    def publish_telemetry(self, data: Dict[str, Any], mission_id: str = "MISSION_ALPHA_01") -> bool:
        """
        Non-blocking enqueue of a CanSat telemetry packet.
        Maps CanSat internal sensor & ML fields into the pipeline TelemetryPacket schema.
        """
        if not self.enabled:
            return False

        self.current_packet_id += 1
        pkt_id = data.get("packet_id", self.current_packet_id)

        # Standardized schema transformation
        ts_ms = data.get("timestamp_ms")
        if ts_ms is None:
            raw_ts = data.get("timestamp") or data.get("time")
            if isinstance(raw_ts, (int, float)):
                ts_ms = int(raw_ts * 1000) if raw_ts < 1e11 else int(raw_ts)
            else:
                ts_ms = int(time.time() * 1000)

        alt = float(data.get("altitude_m") if data.get("altitude_m") is not None else data.get("altitude", 0.0))
        press = float(data.get("pressure_hpa") if data.get("pressure_hpa") is not None else data.get("pressure", 1013.25))
        temp = float(data.get("temperature_c") if data.get("temperature_c") is not None else data.get("temp", 25.0))
        
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

        bat = data.get("battery_v")
        if bat is None:
            bat = data.get("batteryVoltage") if data.get("batteryVoltage") is not None else data.get("battery_voltage", 4.20)
        bat = float(bat)

        stage = data.get("flight_stage") or data.get("flight_phase") or data.get("flightPhase") or "PAD_IDLE"
        anom_score = float(data.get("anomaly_score") or data.get("anomalyScore") or 0.0)
        is_anom = bool(data.get("is_anomaly") or data.get("isAnomaly") or False)
        status = data.get("status") or (data.get("anomaly_type") if is_anom else "OK") or "OK"

        packet = {
            "mission_id": data.get("mission_id", mission_id),
            "packet_id": int(pkt_id),
            "timestamp_ms": int(ts_ms),
            "altitude_m": round(alt, 2),
            "pressure_hpa": round(press, 2),
            "velocity_mps": round(vel, 2),
            "accel_x_g": round(ax, 3),
            "accel_y_g": round(ay, 3),
            "accel_z_g": round(az, 3),
            "gyro_x_dps": round(gx, 2),
            "gyro_y_dps": round(gy, 2),
            "gyro_z_dps": round(gz, 2),
            "battery_v": round(bat, 2),
            "temperature_c": round(temp, 2),
            "flight_stage": stage,
            "status": status,
            # Enriched fields
            "humidity_pct": float(data.get("humidity", data.get("humidity_pct", 50.0))),
            "lat": float(data.get("lat", 22.5727)),
            "lon": float(data.get("lon", 88.3655)),
            "pitch_deg": float(data.get("pitch", data.get("pitch_deg", 0.0))),
            "roll_deg": float(data.get("roll", data.get("roll_deg", 0.0))),
            "accel_mag_g": float(data.get("accel_mag", (ax**2 + ay**2 + az**2)**0.5)),
            "anomaly_score": anom_score,
            "is_anomaly": is_anom,
            "dew_point_c": data.get("dew_point", data.get("dew_point_c")),
            "air_density_kg_m3": data.get("air_density", data.get("air_density_kg_m3")),
            "lapse_rate_c_100m": data.get("lapse_rate", data.get("lapse_rate_c_100m")),
            "calibrated_altitude_m": data.get("calibrated_altitude", alt)
        }

        return self._enqueue_item({"type": "telemetry", "topic": self.telemetry_topic, "payload": packet})

    def publish_event(
        self,
        event_type: str,
        severity: str = "INFO",
        description: str = "",
        metric_value: float = 0.0,
        mission_id: str = "MISSION_ALPHA_01"
    ) -> bool:
        """Enqueue an aerospace operational event or ML anomaly alert."""
        if not self.enabled:
            return False

        event = {
            "mission_id": mission_id,
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "metric_value": metric_value,
            "timestamp_ms": int(time.time() * 1000)
        }
        return self._enqueue_item({"type": "event", "topic": self.events_topic, "payload": event})

    def _enqueue_item(self, item: Dict[str, Any]) -> bool:
        try:
            self._queue.put_nowait(item)
            self.packets_queued += 1
            return True
        except queue.Full:
            # Drop oldest item to prevent memory bloat and keep real-time latency
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(item)
                self.packets_dropped += 1
            except Exception:
                pass
            return False

    def _dispatch_loop(self) -> None:
        """Background loop continuously sending items from queue to Redpanda broker."""
        last_reconnect_attempt = 0.0
        reconnect_interval = 3.0

        while self._running:
            # Check or establish connection
            now = time.time()
            if not self._connected:
                if now - last_reconnect_attempt >= reconnect_interval:
                    last_reconnect_attempt = now
                    self._get_or_create_producer()

            try:
                # Wait for items with short timeout
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self._connected or self._producer is None:
                # If broker is offline, discard item if queue is large
                self._queue.task_done()
                continue

            try:
                topic = item["topic"]
                payload = item["payload"]
                key = str(payload.get("packet_id", int(time.time() * 1000))).encode("utf-8")
                
                self._producer.send(topic, key=key, value=payload)
                self.packets_sent += 1
                self.last_sent_timestamp = time.time()
                self._queue.task_done()
            except Exception as send_err:
                self.errors += 1
                self.last_error = str(send_err)
                self._connected = False
                self._close_producer()
                self._queue.task_done()

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic health status for the Mission Control API & HUD."""
        return {
            "enabled": self.enabled,
            "connected": self._connected,
            "broker": self.broker,
            "telemetry_topic": self.telemetry_topic,
            "events_topic": self.events_topic,
            "queue_size": self._queue.qsize(),
            "packets_queued": self.packets_queued,
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "errors": self.errors,
            "last_error": self.last_error,
            "last_sent_timestamp": self.last_sent_timestamp,
            "kafka_available": HAS_KAFKA
        }

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self._close_producer()

    def reconfigure(self, broker: Optional[str] = None, enabled: Optional[bool] = None) -> None:
        with self._lock:
            if broker and broker != self.broker:
                self.broker = broker
                self._close_producer()
            if enabled is not None:
                self.enabled = enabled


# Global singleton instance
_pipeline_bridge_instance: Optional[PipelineBridge] = None

def get_pipeline_bridge() -> PipelineBridge:
    global _pipeline_bridge_instance
    if _pipeline_bridge_instance is None:
        _pipeline_bridge_instance = PipelineBridge()
        _pipeline_bridge_instance.start()
    return _pipeline_bridge_instance
