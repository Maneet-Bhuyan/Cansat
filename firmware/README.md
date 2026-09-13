# Microcontroller Firmware Suite

This directory contains the firmware source code for the Cognitive CanSat auxiliary vision and telemetry system.

## Subdirectories

* **`esp32_cam_airborne/`**: Arduino / ESP-IDF C++ sketch for the airborne AI-Thinker ESP32-CAM module.
  * Captures downward aerial images (OV5640 5MP / OV3660 3MP).
  * Runs onboard INT8 TinyML inference (`model_data.h`) for the Safe Landing Area Index (SLAI).
  * Saves full-resolution images to the onboard MicroSD card.
  * Broadcasts downsampled preview frames and $3 \times 3$ hazard matrices over 2.4 GHz ESP-NOW.

* **`esp32_ground_receiver/`**: Arduino sketch for the ground ESP-WROOM-32U node.
  * Connects to high-gain external antenna.
  * Listens for 2.4 GHz ESP-NOW packets transmitted from the descending CanSat.
  * Bridges frames and telemetry over USB Serial (460800 baud) into the ground station laptop.

* **`captures/`**: Wireless aerial frame captures and test snapshot image artifacts.

* **`ground_cam_viewer.py`**: Standalone OpenCV desktop HUD viewer for headless or diagnostic video reception.
