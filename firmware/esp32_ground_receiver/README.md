# Ground Receiver ESP32 Node Firmware

## Target Hardware Specifications
* **Module:** ESP-WROOM-32U Development Board (NodeMCU 38-Pin) or ESP32-WROVER with IPEX Connector
* **Antenna:** High-gain 2.4 GHz external directional or 6dBi dipole antenna connected to IPEX/SMA
* **Radio:** 2.4 GHz ESP-NOW Promiscuous Ingestion (Channel 1)
* **Interface:** Micro-USB connected to Ground Station laptop running at **115200 baud**

---

## File Manifest
* [`esp32_ground_receiver.ino`](file:///e:/Cansat/firmware/esp32_ground_receiver/esp32_ground_receiver.ino): Main Arduino firmware sketch for the ground node.

---

## Arduino IDE Configuration
To flash the Ground Receiver:
1. Connect the ESP-WROOM-32U board to your laptop via Micro-USB.
2. Open Arduino IDE and select board: **ESP32 Dev Module** (or **DOIT ESP32 DEVKIT V1**).
3. Tools settings:
   - **Upload Speed:** `921600`
   - **CPU Frequency:** `240MHz (WiFi/BT)`
   - **Flash Frequency:** `80MHz`
   - **Flash Mode:** `QIO`
   - **Port:** Select the assigned USB COM port (e.g. `COM3` or `COM4`).
4. Click **Upload**.

---

## Streaming to Laptop
Once flashed, the ground receiver reassembles incoming ESP-NOW chunks and outputs:
```
$CAM_FRAME,<frame_id>,<size_bytes>,<airtime_ms>,<base64_jpeg_data>
```

You can view the live video stream on your laptop using either:
1. **Mission Control Web Dashboard**: Open `http://127.0.0.1:8000/` and connect via Web Serial or Python Serial Bridge. The video appears automatically in the **Live Aerial Camera Stream** tile.
2. **Standalone Python Camera Viewer**:
   ```bash
   python firmware/ground_cam_viewer.py --port COM_GROUND
   ```
   Or to test with synthetic feed without hardware:
   ```bash
   python firmware/ground_cam_viewer.py --demo
   ```
