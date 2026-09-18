# Cognitive CanSat Backend Core Package
from .serial_manager import DualSerialManager, SerialPortConfig, list_available_ports
from .kinematics import KinematicsEngine, KinematicState, KinematicAlarms
from .atmospheric import AtmosphericEngine, AtmosphericSounding

__all__ = [
    'DualSerialManager',
    'SerialPortConfig',
    'list_available_ports',
    'KinematicsEngine',
    'KinematicState',
    'KinematicAlarms',
    'AtmosphericEngine',
    'AtmosphericSounding',
]
