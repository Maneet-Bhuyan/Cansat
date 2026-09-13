// ============================================================================
//  COGNITIVE CANSAT AIRBORNE CAMERA PIN DEFINITIONS
//  Hardware: AI-Thinker ESP32-CAM Development Board
//  Supported Sensors: OV3660 (3MP), OV2640 (2MP), OV5640 (5MP)
// ============================================================================

#ifndef CAMERA_PINS_H
#define CAMERA_PINS_H

// Camera Sensor Interface Pinout (AI-Thinker Model)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Board Auxiliary Peripherals
#define FLASH_LED_PIN      4   // High-power white spotlight LED
#define ONBOARD_LED_PIN   33   // Small red indicator LED (Active LOW)

#endif // CAMERA_PINS_H
