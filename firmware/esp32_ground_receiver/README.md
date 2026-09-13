# Ground Receiver ESP32 Node Firmware

## Target Hardware
* **Board:** ESP-WROOM-32U Development Board (NodeMCU 38-Pin)
* **Antenna:** High-gain 2.4 GHz directional or 6dBi dipole antenna via IPEX/SMA connector
* **Interface:** Micro-USB connected to Ground Station laptop at 115200 baud

## Operation
1. Initializes ESP-NOW radio on channel 1.
2. Listens for airborne packet broadcasts.
3. Reassembles image frame chunks and safety matrix bytes.
4. Forwards the stream via serial UART to the Python backend on port `COM_GROUND`.
