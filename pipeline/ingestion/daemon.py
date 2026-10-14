"""
CanSat Ingestion Daemon
Reads from hardware serial (pyserial), synthetic flight simulator, CanSat scenario CSV replay,
or CanSat FastAPI WebSocket bridge, validates frames, and produces to Redpanda / Kafka topic 'cansat.telemetry.raw'.
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

from kafka import KafkaProducer

# Ensure project root is in sys.path so 'simulator' and 'packet_parser' are found
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from simulator.flight_simulator import CanSatFlightSimulator
from packet_parser import TelemetryPacket

# Path to CanSat test cases directory
CANSAT_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "Cansat"))
TEST_CASES_DIR = os.path.join(CANSAT_DIR, "test_cases")


def create_kafka_producer(broker: str = "localhost:19092") -> KafkaProducer:
    print(f"[*] Connecting to Redpanda broker at {broker}...")
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[broker],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks=1
            )
            print("[+] Successfully connected to Redpanda broker!")
            return producer
        except Exception as e:
            print(f"[-] Broker not ready ({e}). Retrying in 2s...")
            time.sleep(2)


def run_simulator_mode(producer: KafkaProducer, topic: str = "cansat.telemetry.raw", rate_hz: float = 10.0, mission_id: str = "MISSION_ALPHA_01"):
    sim = CanSatFlightSimulator(frequency_hz=rate_hz, mission_id=mission_id)
    print(f"[*] Starting Flight Ingestion Daemon in SIMULATION mode @ {rate_hz} Hz...")
    
    for packet in sim.run_stream(total_duration_s=80.0):
        try:
            validated = TelemetryPacket(**packet)
            payload = validated.model_dump()
            producer.send(topic, key=str(payload["packet_id"]).encode("utf-8"), value=payload)
            print(f"[->] Sim Packet #{payload['packet_id']} | Alt: {payload['altitude_m']:.1f}m | Vel: {payload['velocity_mps']:.1f}m/s | Stage: {payload['flight_stage']}")
        except Exception as e:
            print(f"[!] Validation / Publish Error: {e}")


def run_replay_mode(producer: KafkaProducer, scenario_name: str, topic: str = "cansat.telemetry.raw", rate_hz: float = 10.0, mission_id: Optional[str] = None):
    clean_name = scenario_name.replace(".csv", "")
    csv_file = os.path.join(TEST_CASES_DIR, f"{clean_name}.csv")
    if not os.path.exists(csv_file):
        # Fallback check in current dir
        if os.path.exists(clean_name + ".csv"):
            csv_file = clean_name + ".csv"
        else:
            print(f"[!] Error: Scenario CSV file not found: {csv_file}")
            print(f"    Available scenarios in {TEST_CASES_DIR}:")
            if os.path.exists(TEST_CASES_DIR):
                for f in os.listdir(TEST_CASES_DIR):
                    if f.endswith(".csv"):
                        print(f"      - {f}")
            return

    actual_mission_id = mission_id or clean_name.upper()
    print(f"[*] Starting Flight Ingestion Daemon in REPLAY mode...")
    print(f"    Scenario   : {clean_name}")
    print(f"    Mission ID : {actual_mission_id}")
    print(f"    Rate       : {rate_hz} Hz (interval: {1.0/rate_hz:.3f}s)")

    import pandas as pd
    df = pd.read_csv(csv_file)
    interval = 1.0 / rate_hz

    packet_id = 0
    t_start = time.time()

    for idx, row in df.iterrows():
        packet_id += 1
        row_dict = row.to_dict()
        row_dict["mission_id"] = actual_mission_id
        row_dict["packet_id"] = packet_id
        row_dict["timestamp_ms"] = int((time.time() - t_start) * 1000)

        try:
            packet = TelemetryPacket.from_cansat_dict(row_dict, mission_id=actual_mission_id, packet_id=packet_id)
            payload = packet.model_dump()
            producer.send(topic, key=str(packet_id).encode("utf-8"), value=payload)
            print(f"[->] Replay #{packet_id:04d} | Alt: {payload['altitude_m']:6.1f}m | Vel: {payload['velocity_mps']:5.1f}m/s | Stage: {payload['flight_stage']:<18} | Bat: {payload['battery_v']:.2f}V")
        except Exception as e:
            print(f"[!] Replay parse error on row {idx}: {e}")

        time.sleep(interval)

    print(f"[+] Replay of {clean_name} finished! Total packets: {packet_id}")


def run_serial_mode(producer: KafkaProducer, port: str = "COM4", baud: int = 9600, topic: str = "cansat.telemetry.raw", mission_id: str = "MISSION_HARDWARE_01"):
    try:
        import serial
    except ImportError:
        print("[!] pyserial is not installed. Install with 'pip install pyserial'")
        return

    print(f"[*] Starting Flight Ingestion Daemon in HARDWARE SERIAL mode...")
    print(f"    Port       : {port}")
    print(f"    Baud Rate  : {baud}")
    print(f"    Mission ID : {mission_id}")

    packet_id = 0
    while True:
        try:
            ser = serial.Serial(port, baud, timeout=1.0)
            print(f"[+] Connected to serial port {port} @ {baud} baud. Listening...")
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line or line.startswith("#") or line.startswith("$"):
                    continue

                packet_id += 1
                try:
                    # Check if JSON
                    if line.startswith("{") and line.endswith("}"):
                        data = json.loads(line)
                        packet = TelemetryPacket.from_cansat_dict(data, mission_id=mission_id, packet_id=packet_id)
                    else:
                        packet = TelemetryPacket.from_csv_line(line, mission_id=mission_id, packet_id=packet_id)

                    payload = packet.model_dump()
                    producer.send(topic, key=str(packet_id).encode("utf-8"), value=payload)
                    print(f"[->] Serial Packet #{packet_id} | Alt: {payload['altitude_m']}m | Stage: {payload['flight_stage']}")
                except Exception as parse_err:
                    print(f"[!] Serial line parsing warning: {parse_err}")

        except Exception as e:
            print(f"[-] Serial port error on {port}: {e}. Retrying in 2s...")
            time.sleep(2)


def run_bridge_mode(producer: KafkaProducer, ws_url: str = "ws://127.0.0.1:8000/ws/serial", topic: str = "cansat.telemetry.raw", mission_id: str = "MISSION_BRIDGE_01"):
    try:
        import websocket
    except ImportError:
        print("[!] websocket-client not installed. Install with 'pip install websocket-client'")
        return

    print(f"[*] Starting Flight Ingestion Daemon in WEBSOCKET BRIDGE mode...")
    print(f"    Target WS  : {ws_url}")
    print(f"    Mission ID : {mission_id}")

    packet_id = 0

    def on_message(ws, message):
        nonlocal packet_id
        line = message.strip()
        if not line or line.startswith("#") or line.startswith("$"):
            return

        packet_id += 1
        try:
            if line.startswith("{") and line.endswith("}"):
                data = json.loads(line)
                packet = TelemetryPacket.from_cansat_dict(data, mission_id=mission_id, packet_id=packet_id)
            else:
                packet = TelemetryPacket.from_csv_line(line, mission_id=mission_id, packet_id=packet_id)

            payload = packet.model_dump()
            producer.send(topic, key=str(packet_id).encode("utf-8"), value=payload)
            print(f"[->] Bridge Packet #{packet_id} | Alt: {payload['altitude_m']}m | Bat: {payload['battery_v']}V")
        except Exception as e:
            print(f"[!] Bridge message parsing warning: {e}")

    def on_error(ws, error):
        print(f"[-] WebSocket bridge error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print("[i] WebSocket bridge closed. Reconnecting in 3s...")
        time.sleep(3)

    while True:
        try:
            ws_app = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws_app.run_forever()
        except Exception as e:
            print(f"[-] WebSocket connection error: {e}. Retrying in 3s...")
            time.sleep(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integrated CanSat Telemetry Ingestion Daemon")
    parser.add_argument("--mode", choices=["sim", "serial", "replay", "bridge"], default="sim",
                        help="Ingestion mode: sim (simulator), serial (hardware), replay (test CSV), bridge (CanSat WS)")
    parser.add_argument("--broker", default="localhost:19092", help="Redpanda / Kafka broker address")
    parser.add_argument("--topic", default="cansat.telemetry.raw", help="Kafka topic name")
    parser.add_argument("--rate", type=float, default=10.0, help="Publish frequency (Hz)")
    parser.add_argument("--scenario", default="01_nominal_sounding_flight",
                        help="Flight scenario name to replay (used in --mode replay)")
    parser.add_argument("--port", default="COM4", help="Serial port for hardware mode")
    parser.add_argument("--baud", type=int, default=9600, help="Serial baud rate")
    parser.add_argument("--ws", default="ws://127.0.0.1:8000/ws/serial", help="WebSocket URL for bridge mode")
    parser.add_argument("--mission-id", default=None, help="Custom mission ID")
    args = parser.parse_args()

    producer = create_kafka_producer(args.broker)

    if args.mode == "sim":
        run_simulator_mode(producer, topic=args.topic, rate_hz=args.rate,
                           mission_id=args.mission_id or "MISSION_SIM_01")
    elif args.mode == "replay":
        run_replay_mode(producer, scenario_name=args.scenario, topic=args.topic,
                        rate_hz=args.rate, mission_id=args.mission_id)
    elif args.mode == "serial":
        run_serial_mode(producer, port=args.port, baud=args.baud, topic=args.topic,
                        mission_id=args.mission_id or "MISSION_HARDWARE_01")
    elif args.mode == "bridge":
        run_bridge_mode(producer, ws_url=args.ws, topic=args.topic,
                        mission_id=args.mission_id or "MISSION_BRIDGE_01")