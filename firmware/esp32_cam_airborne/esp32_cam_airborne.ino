// ============================================================================
//  COGNITIVE CANSAT - AIRBORNE ESP32-CAM VIDEO TRANSMITTER
//  Target Hardware: AI-Thinker ESP32-CAM (ESP32-S + OV3660 / OV2640)
//  Protocol: 2.4 GHz ESP-NOW Action Frame Broadcast (Channel 1)
//  Mode: Low-Latency Video Transmission to Ground Receiver
// ============================================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "camera_pins.h"

// ----------------------------------------------------------------------------
// CONFIGURATION PARAMETERS
// ----------------------------------------------------------------------------
// Resolution Options:
//   FRAMESIZE_QQVGA : 160x120 (~1.2 - 2.5 KB) -> Ultra high frame rate (5-10 FPS)
//   FRAMESIZE_QVGA  : 320x240 (~3.5 - 6.5 KB) -> Recommended (Crisp visual quality)
//   FRAMESIZE_VGA   : 640x480 (~12 - 20 KB)   -> High resolution
#define CAMERA_FRAME_SIZE    FRAMESIZE_QVGA
#define CAMERA_JPEG_QUALITY  12   // 10-63 (Lower = Higher Quality, 12 is optimal)
#define TARGET_FPS           3    // Target descent capture rate (1-5 FPS)
#define CHUNK_MAX_SIZE       200  // Bytes per ESP-NOW packet (Hard limit: 250)
#define WIFI_CHANNEL         1    // Must match Ground Receiver channel

// Broadcast MAC address (receivable by any ESP32 listening on Channel 1)
static uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ----------------------------------------------------------------------------
// PROTOCOL DEFINITIONS
// ----------------------------------------------------------------------------
#define SYNC_WORD            0xAA55
#define PKT_FRAME_START      0x01
#define PKT_FRAME_DATA       0x02

#pragma pack(push, 1)
typedef struct {
    uint16_t sync;          // 0xAA55
    uint8_t  pkt_type;      // PKT_FRAME_START (0x01)
    uint16_t frame_id;      // Monotonically increasing sequence number
    uint32_t total_bytes;   // Total JPEG length
    uint16_t total_chunks;  // Total number of chunks in this frame
    uint16_t width;         // Image width in pixels
    uint16_t height;        // Image height in pixels
    uint8_t  quality;       // JPEG quality factor
} FrameHeaderPacket;

typedef struct {
    uint16_t sync;          // 0xAA55
    uint8_t  pkt_type;      // PKT_FRAME_DATA (0x02)
    uint16_t frame_id;      // Matching frame sequence number
    uint16_t chunk_index;   // 0-indexed chunk counter
    uint16_t total_chunks;  // Total chunk count
    uint8_t  chunk_len;     // Number of valid payload bytes in this chunk
    uint8_t  payload[CHUNK_MAX_SIZE]; // Raw JPEG slice
} FrameChunkPacket;
#pragma pack(pop)

// ----------------------------------------------------------------------------
// GLOBAL STATE
// ----------------------------------------------------------------------------
static uint16_t g_frame_counter = 0;
static unsigned long g_last_capture_time = 0;
static const unsigned long g_frame_interval_ms = 1000 / TARGET_FPS;
static bool g_esp_now_ready = false;

// ----------------------------------------------------------------------------
// CAMERA HARDWARE INITIALIZATION
// ----------------------------------------------------------------------------
bool init_camera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000; // 20 MHz
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size   = CAMERA_FRAME_SIZE;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;

    // Check for external PSRAM
    if (psramFound()) {
        config.fb_count = 2;
        config.grab_mode = CAMERA_GRAB_LATEST;
        config.fb_location = CAMERA_FB_IN_PSRAM;
        Serial.println(F("[CAM] PSRAM detected (4MB). Double frame buffering enabled."));
    } else {
        config.fb_count = 1;
        config.fb_location = CAMERA_FB_IN_DRAM;
        Serial.println(F("[CAM] WARNING: No PSRAM detected. Single buffer mode in DRAM."));
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM ERROR] Camera init failed with error: 0x%x\n", err);
        return false;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (s != NULL) {
        // Sensor calibration for OV3660 / OV2640 downward sounding view
        s->set_brightness(s, 1);    // Slightly boost brightness for aerial ground contrast
        s->set_contrast(s, 1);      // Boost contrast
        s->set_saturation(s, 0);    // Normal saturation
        s->set_whitebal(s, 1);      // Enable Auto White Balance
        s->set_awb_gain(s, 1);      // Enable AWB gain
        s->set_exposure_ctrl(s, 1); // Auto Exposure Control
        s->set_gain_ctrl(s, 1);     // Auto Gain Control
        s->set_vflip(s, 1);         // Flip vertically for downward mounting orientation
        s->set_hmirror(s, 0);       // No mirror
        Serial.printf("[CAM] Sensor detected. PID: 0x%02X\n", s->id.PID);
    }
    return true;
}

// ----------------------------------------------------------------------------
// ESP-NOW RADIO INITIALIZATION
// ----------------------------------------------------------------------------
bool init_esp_now() {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true);

    // Lock to Channel 1 for deterministic peer-to-peer radio matching
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);

    if (esp_now_init() != ESP_OK) {
        Serial.println(F("[RADIO ERROR] ESP-NOW initialization failed."));
        return false;
    }

    // Register broadcast peer
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = WIFI_CHANNEL;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println(F("[RADIO ERROR] Failed to add broadcast peer."));
        return false;
    }

    Serial.printf("[RADIO] ESP-NOW ready. Broadcasting on 2.4 GHz Channel %d.\n", WIFI_CHANNEL);
    return true;
}

// ----------------------------------------------------------------------------
// VIDEO FRAME CAPTURE & CHUNK TRANSMITTER
// ----------------------------------------------------------------------------
void capture_and_transmit() {
    digitalWrite(ONBOARD_LED_PIN, LOW); // LED ON (Active Low indicator)

    unsigned long t_start = millis();
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println(F("[CAM ERROR] Frame capture failed."));
        digitalWrite(ONBOARD_LED_PIN, HIGH);
        return;
    }

    g_frame_counter++;
    uint32_t frame_bytes = fb->len;
    uint16_t total_chunks = (frame_bytes + CHUNK_MAX_SIZE - 1) / CHUNK_MAX_SIZE;

    // 1. Transmit Frame Start Header
    FrameHeaderPacket header;
    header.sync         = SYNC_WORD;
    header.pkt_type     = PKT_FRAME_START;
    header.frame_id     = g_frame_counter;
    header.total_bytes  = frame_bytes;
    header.total_chunks = total_chunks;
    header.width        = fb->width;
    header.height       = fb->height;
    header.quality      = CAMERA_JPEG_QUALITY;

    esp_now_send(broadcastAddress, (uint8_t *)&header, sizeof(header));
    delayMicroseconds(600); // Allow MAC queue clearance

    // 2. Transmit Consecutive Slices
    FrameChunkPacket chunk;
    chunk.sync         = SYNC_WORD;
    chunk.pkt_type     = PKT_FRAME_DATA;
    chunk.frame_id     = g_frame_counter;
    chunk.total_chunks = total_chunks;

    for (uint16_t i = 0; i < total_chunks; i++) {
        uint32_t offset = i * CHUNK_MAX_SIZE;
        uint32_t remaining = frame_bytes - offset;
        uint8_t  len = (remaining < CHUNK_MAX_SIZE) ? remaining : CHUNK_MAX_SIZE;

        chunk.chunk_index = i;
        chunk.chunk_len   = len;
        memcpy(chunk.payload, fb->buf + offset, len);

        esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&chunk, sizeof(chunk) - (CHUNK_MAX_SIZE - len));
        if (result != ESP_OK) {
            // Transient backoff if queue was busy
            delayMicroseconds(200);
        }
        delayMicroseconds(450); // Inter-packet spacing prevents ground FIFO overflow
    }

    unsigned long t_duration = millis() - t_start;
    float current_fps = (t_duration > 0) ? (1000.0f / t_duration) : 0.0f;

    Serial.printf("[TX #%04d] Size: %u B | Chunks: %d | Time: %lu ms (~%.1f FPS)\n",
                  g_frame_counter, frame_bytes, total_chunks, t_duration, current_fps);

    // Release camera memory back to driver pool
    esp_camera_fb_return(fb);
    digitalWrite(ONBOARD_LED_PIN, HIGH); // LED OFF
}

// ----------------------------------------------------------------------------
// ARDUINO SETUP
// ----------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println(F("======================================================"));
    Serial.println(F("  COGNITIVE CANSAT - AIRBORNE VIDEO NODE (ESP32-CAM)  "));
    Serial.println(F("======================================================"));

    pinMode(ONBOARD_LED_PIN, OUTPUT);
    digitalWrite(ONBOARD_LED_PIN, HIGH); // Off initially

    // Initialize Camera
    if (!init_camera()) {
        Serial.println(F("[FATAL] Camera hardware halt. Halting setup."));
        while (true) {
            digitalWrite(ONBOARD_LED_PIN, !digitalRead(ONBOARD_LED_PIN));
            delay(150);
        }
    }

    // Initialize ESP-NOW Radio
    if (!init_esp_now()) {
        Serial.println(F("[FATAL] Radio hardware halt. Halting setup."));
        while (true) {
            digitalWrite(ONBOARD_LED_PIN, !digitalRead(ONBOARD_LED_PIN));
            delay(500);
        }
    }

    Serial.println(F("[INIT COMPLETE] Commencing aerial video transmission..."));
}

// ----------------------------------------------------------------------------
// ARDUINO MAIN LOOP (Non-blocking FPS control)
// ----------------------------------------------------------------------------
void loop() {
    unsigned long now = millis();
    if (now - g_last_capture_time >= g_frame_interval_ms) {
        g_last_capture_time = now;
        capture_and_transmit();
    }
}
