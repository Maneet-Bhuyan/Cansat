# Airborne ESP32-CAM Video Transmitter Firmware

## Target Hardware Specifications
* **Module:** AI-Thinker ESP32-CAM (ESP32-S + 4MB external PSRAM + 4MB SPI Flash)
* **Camera Sensor:** OmniVision OV3660 (3MP) or OV2640 (2MP)
* **Radio:** 2.4 GHz ESP-NOW Action Frame Broadcast (Channel 1, zero association required)
* **Power Delivery:** 3.7V 1S Li-ion battery stepped up to 5.1V via dedicated DC-DC boost converter
* **Status Indicator:** Onboard Red LED on GPIO 33 (Active LOW) toggles during frame transmission

---

## File Manifest
* [`esp32_cam_airborne.ino`](file:///e:/Cansat/firmware/esp32_cam_airborne/esp32_cam_airborne.ino): Main Arduino firmware sketch.
* [`camera_pins.h`](file:///e:/Cansat/firmware/esp32_cam_airborne/camera_pins.h): Hardware pin mappings for the AI-Thinker camera interface.

---

## Arduino IDE Configuration
To flash the AI-Thinker ESP32-CAM:
1. Open Arduino IDE (version 2.x recommended).
2. Install the **ESP32 by Espressif Systems** board package (`esp32` version >= 2.0.11 or 3.x).
3. Select board: **AI Thinker ESP32-CAM**.
4. Configure Tools settings:
   - **CPU Frequency:** `240MHz (WiFi/BT)`
   - **Flash Frequency:** `80MHz`
   - **Flash Mode:** `QIO`
   - **Partition Scheme:** `Huge APP (3MB No OTA / 1MB SPIFFS)`
   - **PSRAM:** `Enabled` (**CRITICAL**: required for double frame buffering!)
5. Connect an external **USB-to-UART FTDI programmer** to the ESP32-CAM:
   - FTDI `5V`  -> ESP32-CAM `5V` (or use dedicated 5V battery power)
   - FTDI `GND` -> ESP32-CAM `GND`
   - FTDI `TX`  -> ESP32-CAM `U0R` (GPIO 3)
   - FTDI `RX`  -> ESP32-CAM `U0T` (GPIO 1)
   - **Flash Mode Strap:** Bridge **GPIO 0 to GND** before pressing the Reset button.
6. Click **Upload**. Once uploaded, remove the GPIO 0 to GND bridge and press Reset to start the video stream!
