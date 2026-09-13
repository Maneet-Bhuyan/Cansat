# Airborne ESP32-CAM TinyML Firmware

## Target Hardware
* **Board:** AI-Thinker ESP32-CAM
* **Camera Sensor:** OV5640 (5MP) or OV3660 (3MP)
* **Power Supply:** 3.7V Li-ion battery stepped up to 5.1V via DC-DC boost converter
* **Storage:** FAT32 MicroSD card inserted into onboard slot

## Operation
1. Periodically captures downward aerial frames during flight descent.
2. Feeds downsampled $64 \times 64$ frames into the compiled `model_data.h` INT8 neural network.
3. Records high-resolution images to the SD card for post-recovery retrieval.
4. Broadcasts landing hazard predictions and preview thumbnails via 2.4 GHz ESP-NOW.
