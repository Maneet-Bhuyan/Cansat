"""
Cognitive CanSat - Atmospheric Thermodynamics Sounding Engine
--------------------------------------------------------------
Implements:
  - Hypsometric barometric altimetry (relative to ground reference pressure).
  - Environmental Lapse Rate (ELR, deg C / 100m) with inversion layer detection.
  - Magnus-Tetens formula for Dew Point (T_dew) from Temp and Relative Humidity.
  - Ideal Gas Law dry air density (rho) in kg/m^3.
  - Standard Atmosphere (ISA) comparison.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class AtmosphericSounding:
    pressure_hpa: float
    temperature_c: float
    relative_humidity_pct: float
    dew_point_c: float
    air_density_kg_m3: float
    barometric_altitude_m: float
    environmental_lapse_rate: float  # deg C / 100m
    is_thermal_inversion: bool
    isa_temp_deviation_c: float


class AtmosphericEngine:
    """
    Sounding physics processor computing thermodynamics, lapse rates, and moisture indices.
    """

    # Thermodynamic constants
    R_SPECIFIC_DRY_AIR = 287.058    # J / (kg * K)
    STANDARD_SEA_LEVEL_P = 1013.25  # hPa
    STANDARD_SEA_LEVEL_T = 15.0     # deg C
    STANDARD_LAPSE_RATE = 0.65      # deg C per 100 m (ISA troposphere standard)

    # Magnus-Tetens coefficients for water vapor (0 deg C to +60 deg C)
    MAGNUS_A = 17.27
    MAGNUS_B = 237.7

    def __init__(self, ground_reference_pressure: float = 1013.25, ground_reference_temp: float = 20.0):
        self.p0 = ground_reference_pressure
        self.t0 = ground_reference_temp

        # History for numerical differentiation of lapse rate
        self._history: List[Tuple[float, float]] = []  # (altitude_m, temperature_c)

    def set_ground_reference(self, pad_pressure_hpa: float, pad_temp_c: Optional[float] = None) -> None:
        """Calibrate barometric ground reference before launch."""
        self.p0 = float(pad_pressure_hpa)
        if pad_temp_c is not None:
            self.t0 = float(pad_temp_c)

    def compute_dew_point(self, temp_c: float, humidity_pct: float) -> float:
        """
        Magnus-Tetens formula for dew point calculation.
        Valid for -45 deg C <= T <= 60 deg C and 1% <= RH <= 100%.
        """
        rh = max(0.01, min(humidity_pct, 100.0))
        alpha = ((self.MAGNUS_A * temp_c) / (self.MAGNUS_B + temp_c)) + math.log(rh / 100.0)
        t_dew = (self.MAGNUS_B * alpha) / (self.MAGNUS_A - alpha)
        return round(t_dew, 2)

    def compute_air_density(self, pressure_hpa: float, temp_c: float, humidity_pct: Optional[float] = None) -> float:
        """
        Computes air density in kg/m^3.
        If humidity_pct is provided, applies virtual temperature correction for moist air:
        rho = P / (R_spec * T_virtual).
        Otherwise uses dry air Ideal Gas Law.
        """
        t_kelvin = temp_c + 273.15
        if t_kelvin <= 0:
            t_kelvin = 288.15
        pressure_pa = pressure_hpa * 100.0

        if humidity_pct is not None and humidity_pct > 0:
            # Saturation vapor pressure (Tetens formula in hPa)
            e_sat = 6.1078 * (10.0 ** ((7.5 * temp_c) / (237.3 + temp_c)))
            # Actual vapor pressure in hPa
            e_actual = (min(100.0, max(0.0, humidity_pct)) / 100.0) * e_sat
            # Virtual temperature: Tv = T * (1 + 0.378 * (e / P))
            p_safe = max(10.0, pressure_hpa)
            t_virtual = t_kelvin * (1.0 + 0.378 * (e_actual / p_safe))
            rho = pressure_pa / (self.R_SPECIFIC_DRY_AIR * t_virtual)
        else:
            rho = pressure_pa / (self.R_SPECIFIC_DRY_AIR * t_kelvin)

        return round(rho, 4)

    def compute_barometric_altitude(self, pressure_hpa: float) -> float:
        """
        Barometric formula: computes altitude (m) relative to calibrated pad reference p0.
        """
        if pressure_hpa <= 0 or self.p0 <= 0:
            return 0.0
        # US Standard Atmosphere 1976 barometric formula
        ratio = pressure_hpa / self.p0
        alt = 44330.0 * (1.0 - math.pow(ratio, 0.190284))
        return round(alt, 2)

    def compute_lapse_rate(self, current_alt_m: float, current_temp_c: float) -> Tuple[float, bool]:
        """
        Calculate Environmental Lapse Rate (ELR, deg C / 100m).
        Returns: (ELR, is_thermal_inversion)
        """
        self._history.append((current_alt_m, current_temp_c))
        if len(self._history) > 50:
            self._history.pop(0)

        if len(self._history) < 3:
            return 0.65, False

        # Compute delta over a 30-meter altitude baseline
        h_start, t_start = self._history[0]
        h_end, t_end = self._history[-1]
        delta_h = h_end - h_start

        if abs(delta_h) < 15.0:
            return 0.65, False

        # ELR = -dT / dz * 100
        elr = -((t_end - t_start) / delta_h) * 100.0
        # A thermal inversion occurs if temperature increases with altitude (negative ELR)
        is_inversion = (elr < -0.1)
        return round(elr, 2), is_inversion

    def process_sounding(self, pressure_hpa: float, temp_c: float, humidity_pct: float, altitude_override: Optional[float] = None) -> AtmosphericSounding:
        """
        Process a full atmospheric observation.
        """
        alt = altitude_override if altitude_override is not None else self.compute_barometric_altitude(pressure_hpa)
        dew_pt = self.compute_dew_point(temp_c, humidity_pct)
        density = self.compute_air_density(pressure_hpa, temp_c, humidity_pct)
        elr, is_inv = self.compute_lapse_rate(alt, temp_c)

        # Compare with International Standard Atmosphere (ISA) temperature at this altitude
        isa_temp_at_alt = self.STANDARD_SEA_LEVEL_T - (self.STANDARD_LAPSE_RATE * (alt / 100.0))
        isa_dev = temp_c - isa_temp_at_alt

        return AtmosphericSounding(
            pressure_hpa=pressure_hpa,
            temperature_c=temp_c,
            relative_humidity_pct=humidity_pct,
            dew_point_c=dew_pt,
            air_density_kg_m3=density,
            barometric_altitude_m=alt,
            environmental_lapse_rate=elr,
            is_thermal_inversion=is_inv,
            isa_temp_deviation_c=round(isa_dev, 2),
        )
