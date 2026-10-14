"""
CanSat Flight Simulator
Realistic 6-stage trajectory physics engine with barometric atmosphere and sensor noise.
"""

import time
import math
import random
from typing import Iterator, Dict, Any

class CanSatFlightSimulator:
    def __init__(self, frequency_hz: float = 10.0, mission_id: str = "MISSION_ALPHA_01"):
        self.frequency_hz = frequency_hz
        self.interval = 1.0 / frequency_hz
        self.mission_id = mission_id
        self.packet_id = 0
        self.launch_alt = 15.0  # Launch site altitude (m)
        self.apogee_alt = 550.0  # Peak altitude target (m)
        self.parachute_terminal_velocity = -6.5  # m/s descent
        
    def _barometric_pressure(self, altitude_m: float) -> float:
        # Standard barometric formula: P = P0 * (1 - (L*h)/T0) ^ (g*M / (R0*L))
        p0 = 1013.25
        return p0 * math.pow(max(0.01, 1.0 - (2.25577e-5 * altitude_m)), 5.25588)

    def generate_packet(self, t_elapsed: float) -> Dict[str, Any]:
        self.packet_id += 1
        
        # Stages:
        # 0.0 - 5.0s:  LAUNCH_PAD
        # 5.0 - 12.0s: BOOST (~7g acceleration)
        # 12.0 - 20.0s: COAST (Decelerating under gravity)
        # 20.0 - 22.0s: APOGEE (Peak altitude reached, ejection shock)
        # 22.0 - 65.0s: PARACHUTE_DESCENT (~ -6.5 m/s)
        # 65.0s+:      LANDED (Touchdown)
        
        if t_elapsed < 5.0:
            stage = "LAUNCH_PAD"
            alt = self.launch_alt + random.gauss(0, 0.15)
            vel = 0.0
            accel_z = 1.0 + random.gauss(0, 0.02)
            gyro_z = random.gauss(0, 0.5)

        elif t_elapsed < 12.0:
            stage = "BOOST"
            t = t_elapsed - 5.0
            burn_accel = 18.0
            vel = burn_accel * t
            alt = self.launch_alt + 0.5 * burn_accel * (t ** 2)
            accel_z = (burn_accel / 9.81 + 1.0) + random.gauss(0, 0.3)
            gyro_z = 25.0 + random.gauss(0, 5.0)

        elif t_elapsed < 20.0:
            stage = "COAST"
            t = t_elapsed - 12.0
            v0 = 18.0 * 7.0
            h0 = self.launch_alt + 0.5 * 18.0 * (7.0 ** 2)
            vel = v0 - 9.81 * t
            alt = min(h0 + v0 * t - 0.5 * 9.81 * (t ** 2), self.apogee_alt)
            accel_z = random.gauss(0, 0.08)
            gyro_z = random.gauss(0, 4.0)

        elif t_elapsed < 22.0:
            stage = "APOGEE"
            alt = self.apogee_alt + random.gauss(0, 0.2)
            vel = random.gauss(0, 0.1)
            accel_z = 4.5 + random.gauss(0, 0.4)  # Parachute deployment shock
            gyro_z = random.gauss(15.0, 6.0)

        elif t_elapsed < 65.0:
            stage = "PARACHUTE_DESCENT"
            t = t_elapsed - 22.0
            alt = max(self.launch_alt, self.apogee_alt + (self.parachute_terminal_velocity * t) + random.gauss(0, 0.3))
            vel = self.parachute_terminal_velocity + random.gauss(0, 0.2)
            accel_z = 1.0 + random.gauss(0, 0.06)
            gyro_z = random.gauss(2.0, 1.5)

        else:
            stage = "LANDED"
            alt = self.launch_alt + random.gauss(0, 0.05)
            vel = 0.0
            accel_z = 1.0 + random.gauss(0, 0.01)
            gyro_z = random.gauss(0, 0.1)

        pressure = self._barometric_pressure(alt) + random.gauss(0, 0.05)
        battery = max(3.3, 4.15 - (t_elapsed * 0.003) + random.gauss(0, 0.01))
        temp = 24.0 - (alt * 0.0065) + random.gauss(0, 0.1)

        return {
            "mission_id": self.mission_id,
            "packet_id": self.packet_id,
            "timestamp_ms": int(t_elapsed * 1000),
            "altitude_m": round(alt, 2),
            "pressure_hpa": round(pressure, 2),
            "velocity_mps": round(vel, 2),
            "accel_x_g": round(random.gauss(0, 0.05), 3),
            "accel_y_g": round(random.gauss(0, 0.05), 3),
            "accel_z_g": round(accel_z, 3),
            "gyro_x_dps": round(random.gauss(0, 1.0), 2),
            "gyro_y_dps": round(random.gauss(0, 1.0), 2),
            "gyro_z_dps": round(gyro_z, 2),
            "battery_v": round(battery, 2),
            "temperature_c": round(temp, 2),
            "flight_stage": stage,
            "status": "OK"
        }

    def run_stream(self, total_duration_s: float = 75.0) -> Iterator[Dict[str, Any]]:
        t_start = time.time()
        while True:
            t_elapsed = time.time() - t_start
            if t_elapsed > total_duration_s:
                break
            packet = self.generate_packet(t_elapsed)
            yield packet
            time.sleep(self.interval)

if __name__ == "__main__":
    sim = CanSatFlightSimulator(frequency_hz=5.0)
    print("Testing Flight Simulator stream (5 packets)...")
    for i, p in enumerate(sim.run_stream(total_duration_s=2.0)):
        print(f"[{p['flight_stage']}] ID: {p['packet_id']}, Alt: {p['altitude_m']}m, Press: {p['pressure_hpa']}hPa, AccZ: {p['accel_z_g']}g")