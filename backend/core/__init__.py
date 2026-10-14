# Cognitive CanSat Backend Core Package
from .serial_manager import DualSerialManager, SerialPortConfig, list_available_ports
from .kinematics import KinematicsEngine, KinematicState, KinematicAlarms
from .atmospheric import AtmosphericEngine, AtmosphericSounding
try:
    from .telemetry_analyzer import TelemetryQualityAnalyzer, TelemetryQualityReport
except ImportError:
    TelemetryQualityAnalyzer = None  # type: ignore
    TelemetryQualityReport = None  # type: ignore

__all__ = [
    'DualSerialManager',
    'SerialPortConfig',
    'list_available_ports',
    'KinematicsEngine',
    'KinematicState',
    'KinematicAlarms',
    'AtmosphericEngine',
    'AtmosphericSounding',
    'TelemetryQualityAnalyzer',
    'TelemetryQualityReport',
]
