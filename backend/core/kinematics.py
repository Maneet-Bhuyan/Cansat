"""
Cognitive CanSat - Kinematics & Attitude Estimation Engine
----------------------------------------------------------
Features:
  - 1D Extended Kalman Filter (EKF) tracking Altitude and Vertical Speed (v_z).
  - 6-DOF IMU Sensor Fusion: Accelerometer gravity pitch/roll + gyroscope integration.
  - Resultant G-Force calculations and peak shock load detection (> 4.5G).
  - Gyro tumble anomaly detection (> 150 deg/s) and freefall tracking.
  - Parachute descent envelope compliance audit (4.0 - 6.5 m/s).
"""

import math
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple


@dataclass
class KinematicState:
    raw_altitude: float
    filtered_altitude: float
    vertical_speed: float       # m/s (positive ascent, negative descent)
    accel_magnitude_g: float     # Total G force
    pitch_deg: float            # -180 to +180 deg
    roll_deg: float             # -90 to +90 deg
    gyro_magnitude_dps: float    # deg/s total rotational rate
    is_freefall: bool
    is_tumble: bool
    is_high_g_shock: bool
    descent_compliant: bool     # True if descending at safe parachute speed
    timestamp: float


@dataclass
class KinematicAlarms:
    shock_threshold_g: float = 4.5
    tumble_threshold_dps: float = 150.0
    freefall_threshold_g: float = 0.20
    safe_descent_min_mps: float = 4.0
    safe_descent_max_mps: float = 6.5


class AltitudeKalmanFilter:
    """
    Linear 1D Kalman filter estimating true altitude and vertical velocity
    from noisy barometric altitude readings and vertical acceleration (a_z).
    State vector: x = [z (m), v_z (m/s)]^T
    """

    def __init__(self, initial_altitude: float = 0.0, process_var: float = 0.5, measure_var: float = 2.0):
        # State: [altitude, vertical_velocity]
        self.z = float(initial_altitude)
        self.vz = 0.0

        # Covariance matrix P
        self.p00 = 10.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 10.0

        # Process and measurement noise
        self.q = process_var   # Process noise (system dynamics variance)
        self.r = measure_var   # Measurement noise (barometer sensor variance)

        self.last_update_time: Optional[float] = None

    def update(self, measured_altitude: float, a_z_g: float = 1.0, current_time: Optional[float] = None) -> Tuple[float, float]:
        """
        Step Kalman filter with barometric measurement and vertical acceleration.
        Returns: (filtered_altitude_m, vertical_velocity_mps)
        """
        now = current_time if current_time is not None else time.time()
        if self.last_update_time is None:
            self.last_update_time = now
            self.z = float(measured_altitude)
            return self.z, self.vz

        dt = now - self.last_update_time
        self.last_update_time = now

        # Clamp dt to prevent numerical divergence if packets stall
        dt = max(0.01, min(dt, 2.0))

        # Acceleration in m/s^2 (remove 1G gravity bias from vertical axis)
        a_vertical = (a_z_g - 1.0) * 9.80665

        # 1. State Prediction:
        # z = z + vz * dt + 0.5 * a * dt^2
        # vz = vz + a * dt
        self.z += self.vz * dt + 0.5 * a_vertical * (dt ** 2)
        self.vz += a_vertical * dt

        # 2. Covariance Prediction: P = F * P * F^T + Q
        dt2 = dt * dt
        p00 = self.p00 + dt * (self.p10 + self.p01) + dt2 * self.p11 + 0.25 * (dt2 ** 2) * self.q
        p01 = self.p01 + dt * self.p11 + 0.5 * (dt ** 3) * self.q
        p10 = self.p10 + dt * self.p11 + 0.5 * (dt ** 3) * self.q
        p11 = self.p11 + dt2 * self.q

        # 3. Measurement Update:
        # Innovation y = measured - predicted
        y = measured_altitude - self.z
        s = p00 + self.r  # Innovation covariance

        if s > 1e-9:
            k0 = p00 / s  # Kalman gain for altitude
            k1 = p10 / s  # Kalman gain for velocity

            self.z += k0 * y
            self.vz += k1 * y

            self.p00 = p00 - k0 * p00
            self.p01 = p01 - k0 * p01
            self.p10 = p10 - k1 * p00
            self.p11 = p11 - k1 * p01
        else:
            self.p00, self.p01, self.p10, self.p11 = p00, p01, p10, p11

        return self.z, self.vz


class KinematicsEngine:
    """
    Comprehensive flight kinematics processor integrating Kalman state estimation,
    IMU attitude complementary fusion, and safety threshold alarms.
    """

    def __init__(self, alarms: Optional[KinematicAlarms] = None, complementary_alpha: float = 0.95):
        self.alarms = alarms or KinematicAlarms()
        self.alpha = complementary_alpha

        self.kalman = AltitudeKalmanFilter()
        self.pitch: float = 0.0
        self.roll: float = 0.0
        self.last_imu_time: Optional[float] = None
        self.peak_shock_g: float = 0.0

    def process_packet(
        self,
        altitude: float,
        ax: float, ay: float, az: float,
        gx: float, gy: float, gz: float,
        timestamp: Optional[float] = None
    ) -> KinematicState:
        """
        Process a single 6-DOF IMU + barometric packet.
        ax, ay, az in Gs.
        gx, gy, gz in deg/s.
        """
        now = timestamp if timestamp is not None else time.time()

        # 1. Accelerometer Force & Gyro Rates
        accel_mag = math.sqrt(ax * ax + ay * ay + az * az)
        gyro_mag = math.sqrt(gx * gx + gy * gy + gz * gz)
        if accel_mag > self.peak_shock_g:
            self.peak_shock_g = accel_mag

        # 2. Accelerometer-based Static Attitude
        acc_pitch = math.atan2(ay, az) * (180.0 / math.pi)
        acc_roll = math.atan2(-ax, math.sqrt(ay * ay + az * az)) * (180.0 / math.pi)

        # 3. Complementary Attitude Fusion with Gyro
        if self.last_imu_time is None:
            self.pitch = acc_pitch
            self.roll = acc_roll
            dt_imu = 0.02
        else:
            dt_imu = max(0.001, min(now - self.last_imu_time, 1.0))
            # Gyro integration + Accel correction
            self.pitch = self.alpha * (self.pitch + gx * dt_imu) + (1.0 - self.alpha) * acc_pitch
            self.roll = self.alpha * (self.roll + gy * dt_imu) + (1.0 - self.alpha) * acc_roll

        self.last_imu_time = now

        # 4. Kalman Filter Altitude & Velocity
        filt_alt, v_spd = self.kalman.update(altitude, a_z_g=az, current_time=now)

        # 5. Alarm Conditions
        is_shock = accel_mag >= self.alarms.shock_threshold_g
        is_tumble = gyro_mag >= self.alarms.tumble_threshold_dps
        is_freefall = accel_mag <= self.alarms.freefall_threshold_g

        # Parachute descent check (negative velocity during descent)
        descent_speed = -v_spd if v_spd < 0 else 0.0
        descent_ok = (self.alarms.safe_descent_min_mps <= descent_speed <= self.alarms.safe_descent_max_mps)

        return KinematicState(
            raw_altitude=altitude,
            filtered_altitude=round(filt_alt, 2),
            vertical_speed=round(v_spd, 2),
            accel_magnitude_g=round(accel_mag, 3),
            pitch_deg=round(self.pitch, 2),
            roll_deg=round(self.roll, 2),
            gyro_magnitude_dps=round(gyro_mag, 2),
            is_freefall=is_freefall,
            is_tumble=is_tumble,
            is_high_g_shock=is_shock,
            descent_compliant=descent_ok,
            timestamp=now,
        )
