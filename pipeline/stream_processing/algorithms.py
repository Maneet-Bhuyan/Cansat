from collections import deque
from typing import Tuple, Optional

class FlightStateEstimator:
    """Computes rolling descent rate Δh/Δt, apogee, and parachute detection."""
    def __init__(self, window_size: int = 5):
        self.history = deque(maxlen=window_size)
        self.apogee_detected = False
        self.parachute_detected = False
        self.max_altitude = 0.0

    def process_frame(self, t_sec: float, alt: float, accel_z: float) -> Tuple[float, str, Optional[str]]:
        self.history.append((t_sec, alt))
        self.max_altitude = max(self.max_altitude, alt)
        
        # Calculate instantaneous vertical velocity Δh / Δt
        if len(self.history) >= 2:
            t_old, h_old = self.history[0]
            t_new, h_new = self.history[-1]
            dt = t_new - t_old
            velocity = (h_new - h_old) / dt if dt > 0 else 0.0
        else:
            velocity = 0.0

        event = None
        # Apogee detection: velocity crosses from positive to negative at high altitude
        if not self.apogee_detected and alt > 200.0 and velocity < -0.5:
            self.apogee_detected = True
            event = "APOGEE_DETECTED"

        # Parachute deployment detection: shock acceleration followed by terminal descent
        if self.apogee_detected and not self.parachute_detected:
            if accel_z > 3.0 or (-8.0 <= velocity <= -4.0 and alt < (self.max_altitude - 20.0)):
                self.parachute_detected = True
                event = "PARACHUTE_DEPLOYED"

        # Classify flight stage
        if alt <= 16.0 and len(self.history) > 10 and abs(velocity) < 0.3 and self.apogee_detected:
            stage = "LANDED"
        elif self.parachute_detected:
            stage = "PARACHUTE_DESCENT"
        elif self.apogee_detected:
            stage = "APOGEE"
        elif velocity > 20.0:
            stage = "BOOST"
        elif velocity > 0.0:
            stage = "COAST"
        else:
            stage = "LAUNCH_PAD"

        return round(velocity, 2), stage, event