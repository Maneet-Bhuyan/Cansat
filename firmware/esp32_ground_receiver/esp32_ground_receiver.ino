// ============================================================================
//  COGNITIVE CANSAT - GROUND RECEIVER NODE (ESP-WROOM-32U / WROVER)
//  Target Hardware: ESP-WROOM-32U Development Board with External IPEX Antenna
//  Protocol: 2.4 GHz ESP-NOW Promiscuous Ingestion (Channel 1)
//  Output: USB Serial Bridge at 115200 Baud ($CAM_FRAME,<id>,<len>,<base64>)
// ============================================================================

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ----------------------------------------------------------------------------
// CONFIGURATION & BUFFER LIMITS
// ----------------------------------------------------------------------------
#define SERIAL_BAUD_RATE     115200  // High-speed USB UART
#define WIFI_CHANNEL         1       // Must match Airborne transmitter channel
#define MAX_FRAME_BYTES      32768   // 32 KB frame buffer (ample for QVGA/QQVGA)
#define CHUNK_MAX_SIZE       200     // Matches airborne chunk slice size
#define FRAME_TIMEOUT_MS     600     // Drop incomplete frame if chunks stall

// Protocol Sync & Identifiers
#define SYNC_WORD            0xAA55
#define PKT_FRAME_START      0x01
#define PKT_FRAME_DATA       0x02

#pragma pack(push, 1)
typedef struct {
    uint16_t sync;
    uint8_t  pkt_type;
    uint16_t frame_id;
    uint32_t total_bytes;
    uint16_t total_chunks;
    uint16_t width;
    uint16_t height;
    uint8_t  quality;
} FrameHeaderPacket;

typedef struct {
    uint16_t sync;
    uint8_t  pkt_type;
    uint16_t frame_id;
    uint16_t chunk_index;
    uint16_t total_chunks;
    uint8_t  chunk_len;
    uint8_t  payload[CHUNK_MAX_SIZE];
} FrameChunkPacket;
#pragma pack(pop)

// ----------------------------------------------------------------------------
// REASSEMBLY STATE
// ----------------------------------------------------------------------------
static uint8_t  s_frame_buffer[MAX_FRAME_BYTES];
static uint16_t s_current_frame_id = 0;
static uint32_t s_expected_bytes = 0;
static uint16_t s_expected_chunks = 0;
static uint16_t s_received_chunks = 0;
static unsigned long s_frame_start_time = 0;
static bool     s_frame_in_progress = false;

// Statistics
static uint32_t s_total_frames_completed = 0;
static uint32_t s_total_frames_dropped = 0;
static unsigned long s_last_fps_calc = 0;
static uint32_t s_frames_in_last_sec = 0;

// ----------------------------------------------------------------------------
// FAST EMBEDDED BASE64 ENCODER (Zero external library dependency)
// ----------------------------------------------------------------------------
static const char B64_CHARS[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

void stream_base64_to_serial(const uint8_t *data, size_t input_len) {
    size_t i = 0;
    while (i < input_len) {
        uint32_t octet_a = (i < input_len) ? data[i++] : 0;
        uint32_t octet_b = (i < input_len) ? data[i++] : 0;
        uint32_t octet_c = (i < input_len) ? data[i++] : 0;

        uint32_t triple = (octet_a << 16) | (octet_b << 8) | octet_c;

        Serial.write(B64_CHARS[(triple >> 18) & 0x3F]);
        Serial.write(B64_CHARS[(triple >> 12) & 0x3F]);
        Serial.write((i > input_len + 1) ? '=' : B64_CHARS[(triple >> 6) & 0x3F]);
        Serial.write((i > input_len)     ? '=' : B64_CHARS[triple & 0x3F]);
    }
}

// ----------------------------------------------------------------------------
// FRAME COMPLETION DISPATCHER
// ----------------------------------------------------------------------------
void dispatch_completed_frame() {
    unsigned long duration = millis() - s_frame_start_time;
    s_total_frames_completed++;
    s_frames_in_last_sec++;

    // Format: $CAM_FRAME,<frame_id>,<size_bytes>,<duration_ms>,<base64_data>\n
    Serial.print(F("$CAM_FRAME,"));
    Serial.print(s_current_frame_id);
    Serial.print(F(","));
    Serial.print(s_expected_bytes);
    Serial.print(F(","));
    Serial.print(duration);
    Serial.print(F(","));

    // Stream base64 characters directly to UART output buffer
    stream_base64_to_serial(s_frame_buffer, s_expected_bytes);
    Serial.println(); // Frame delimiter

    s_frame_in_progress = false;
}

// ----------------------------------------------------------------------------
// ESP-NOW RECEIVE CALLBACK HANDLER
// ----------------------------------------------------------------------------
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
void OnDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
#else
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
#endif
    if (len < 3) return; // Minimum sync word + type check

    uint16_t sync = incomingData[0] | (incomingData[1] << 8);
    if (sync != SYNC_WORD) return;

    uint8_t pkt_type = incomingData[2];

    // CASE 1: Start of New Frame
    if (pkt_type == PKT_FRAME_START && len >= sizeof(FrameHeaderPacket)) {
        FrameHeaderPacket *header = (FrameHeaderPacket *)incomingData;

        // If a previous frame was in progress and not finished, mark as dropped
        if (s_frame_in_progress) {
            s_total_frames_dropped++;
        }

        s_current_frame_id = header->frame_id;
        s_expected_bytes   = header->total_bytes;
        s_expected_chunks  = header->total_chunks;
        s_received_chunks  = 0;
        s_frame_start_time = millis();
        s_frame_in_progress = true;

        if (s_expected_bytes > MAX_FRAME_BYTES) {
            s_frame_in_progress = false; // Exceeds safety buffer
        }
        return;
    }

    // CASE 2: Frame Data Chunk
    if (pkt_type == PKT_FRAME_DATA && len >= 8) {
        FrameChunkPacket *chunk = (FrameChunkPacket *)incomingData;

        // Verify that this chunk matches the active frame
        if (!s_frame_in_progress || chunk->frame_id != s_current_frame_id) {
            return;
        }

        uint32_t offset = (uint32_t)chunk->chunk_index * CHUNK_MAX_SIZE;
        if (offset + chunk->chunk_len <= MAX_FRAME_BYTES) {
            memcpy(s_frame_buffer + offset, chunk->payload, chunk->chunk_len);
            s_received_chunks++;

            // Check if all chunks have arrived
            if (s_received_chunks >= s_expected_chunks) {
                dispatch_completed_frame();
            }
        }
    }
}

// ----------------------------------------------------------------------------
// ARDUINO SETUP
// ----------------------------------------------------------------------------
void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(1000);

    Serial.println();
    Serial.println(F("========================================================"));
    Serial.println(F(" COGNITIVE CANSAT - GROUND RECEIVER NODE (ESP32-WROOM)  "));
    Serial.println(F("========================================================"));

    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true);

    // Channel alignment
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);

    if (esp_now_init() != ESP_OK) {
        Serial.println(F("[ERROR] ESP-NOW init failed. Halting."));
        while (true) delay(1000);
    }

    esp_now_register_recv_cb(OnDataRecv);

    Serial.printf("[INIT COMPLETE] Receiver active on Channel %d. Awaiting airborne feed...\n", WIFI_CHANNEL);
}

// ----------------------------------------------------------------------------
// ARDUINO MAIN LOOP (Timeout & Stale Frame Watchdog)
// ----------------------------------------------------------------------------
void loop() {
    unsigned long now = millis();

    // Check for stalled/incomplete frames
    if (s_frame_in_progress && (now - s_frame_start_time > FRAME_TIMEOUT_MS)) {
        s_total_frames_dropped++;
        s_frame_in_progress = false;
    }

    // Periodic heartbeat / link quality audit every 2 seconds
    if (now - s_last_fps_calc >= 2000) {
        float fps = (float)s_frames_in_last_sec / ((now - s_last_fps_calc) / 1000.0f);
        s_frames_in_last_sec = 0;
        s_last_fps_calc = now;

        // Print telemetry diagnosis comment line (ignored by mission control parser)
        Serial.printf("# [GCS LINK AUDIT] RX: %u frames | Dropped: %u | Live Rate: %.1f FPS\n",
                      s_total_frames_completed, s_total_frames_dropped, fps);
    }
}
