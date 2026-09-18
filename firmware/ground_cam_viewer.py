"""
Cognitive CanSat - Ground Video Stream Viewer
---------------------------------------------
Reads incoming serial frames from the ESP-WROOM-32U Ground Receiver node,
decodes the live base64 JPEG stream ($CAM_FRAME,...), and renders the aerial feed
in a responsive HUD viewport with real-time FPS, latency, and throughput metrics.

Usage:
  python firmware/ground_cam_viewer.py                  (auto-detects COM port)
  python firmware/ground_cam_viewer.py --port COM4      (specifies port)
  python firmware/ground_cam_viewer.py --demo           (runs synthetic test feed)
"""

import sys
import time
import base64
import argparse
import io
from collections import deque

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

# Attempt GUI imports (OpenCV preferred for performance, Pillow/Tkinter fallback)
USE_CV2 = False
try:
    import cv2
    import numpy as np
    USE_CV2 = True
except ImportError:
    try:
        from PIL import Image, ImageTk
        import tkinter as tk
    except ImportError:
        pass


def list_available_ports():
    if not serial:
        return []
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return ports


def run_opencv_viewer(port_name: str, baud_rate: int, demo_mode: bool = False):
    print("=" * 70)
    print("  COGNITIVE CANSAT - GROUND AERIAL VIDEO HUD")
    print(f"  Source: {'DEMO SYNTHETIC GENERATOR' if demo_mode else f'SERIAL {port_name} @ {baud_rate} BAUD'}")
    print("  Controls: Press 'q' or ESC in video window to exit.")
    print("=" * 70)

    window_name = "Cognitive CanSat - Airborne Camera Feed"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)

    ser = None
    if not demo_mode:
        if not serial:
            print("[ERROR] pyserial is required. Install via: pip install pyserial")
            sys.exit(1)
        try:
            ser = serial.Serial(port_name, baud_rate, timeout=1)
            ser.setDTR(True)
            ser.setRTS(True)
            print(f"[+] Serial port {port_name} opened successfully. Listening for frames...")
        except Exception as e:
            print(f"[ERROR] Failed to open {port_name}: {e}")
            print(f"Available ports: {list_available_ports()}")
            sys.exit(1)

    fps_history = deque(maxlen=15)
    last_frame_time = time.time()
    total_frames = 0
    total_bytes = 0
    show_grid = True
    prev_gray = None

    demo_color_hue = 0

    try:
        while True:
            frame_img = None
            frame_id = 0
            frame_size = 0
            rx_duration = 0

            if demo_mode:
                # Generate synthetic test pattern mimicking descent
                time.sleep(0.20)  # ~5 FPS
                demo_color_hue = (demo_color_hue + 3) % 180
                hsv = np.zeros((240, 320, 3), dtype=np.uint8)
                hsv[:, :, 0] = demo_color_hue
                hsv[:, :, 1] = 160
                hsv[:, :, 2] = 210
                frame_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                # Draw synthetic terrain patch (green safe zone on top-right, grey road on left)
                cv2.rectangle(frame_img, (0, 0), (105, 240), (80, 80, 80), -1) # Road/Hazard
                cv2.rectangle(frame_img, (215, 0), (320, 160), (35, 140, 45), -1) # Green field
                frame_id = total_frames + 1
                frame_size = 4250
                rx_duration = 24
            else:
                if ser and ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith("#"):
                        print(f"[Ground Receiver Status] {line}")
                    elif line.startswith("$CAM_FRAME,"):
                        parts = line.split(",", 4)
                        if len(parts) >= 5:
                            try:
                                frame_id = int(parts[1])
                                frame_size = int(parts[2])
                                rx_duration = int(parts[3])
                                b64_data = parts[4].strip()

                                img_bytes = base64.b64decode(b64_data)
                                np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
                                frame_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                            except Exception as decode_err:
                                print(f"[!] Decode error: {decode_err}")
                else:
                    time.sleep(0.01)

            # If no frame has arrived yet, show an active Standby HUD screen
            if frame_img is None and total_frames == 0:
                standby_screen = np.zeros((240, 320, 3), dtype=np.uint8)
                standby_screen[:] = (15, 18, 25) # Dark space blue

                # Draw blinking standby indicator
                pulse = int((time.time() * 2) % 2)
                dot_color = (0, 255, 0) if pulse else (0, 150, 0)
                cv2.circle(standby_screen, (24, 24), 6, dot_color, -1)

                cv2.putText(standby_screen, "RECEIVER ACTIVE (COM5)", (38, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1, cv2.LINE_AA)
                cv2.putText(standby_screen, "Awaiting ESP-NOW feed from ESP32-CAM...", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1, cv2.LINE_AA)
                cv2.putText(standby_screen, "1. Verify IO0 is DISCONNECTED from GND", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (120, 160, 200), 1, cv2.LINE_AA)
                cv2.putText(standby_screen, "2. Press RST button on ESP32-CAM", (20, 172), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (120, 160, 200), 1, cv2.LINE_AA)
                cv2.putText(standby_screen, "Hotkeys: 'g' Toggle 3x3 Grid | 'q' Exit", (20, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 200, 255), 1, cv2.LINE_AA)
                cv2.imshow(window_name, standby_screen)
                if cv2.waitKey(10) & 0xFF in (ord('q'), 27):
                    break
                continue

            if frame_img is not None:
                total_frames += 1
                total_bytes += frame_size

                now = time.time()
                dt = now - last_frame_time
                last_frame_time = now
                if dt > 0:
                    fps_history.append(1.0 / dt)
                avg_fps = sum(fps_history) / len(fps_history) if fps_history else 0.0

                h, w = frame_img.shape[:2]

                # Visual TTI calculation
                gray = cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY)
                tti_val = 14.5
                if prev_gray is not None and prev_gray.shape == gray.shape:
                    diff = np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32)))
                    if diff > 0.8:
                        tti_val = max(1.5, min(99.0, (255.0 / diff) * max(0.05, dt) * 2.8))
                prev_gray = gray

                # Compute Global VARI and 3x3 Spatial Grid
                arr_f = frame_img.astype(np.float32)
                b_chan, g_chan, r_chan = arr_f[:, :, 0], arr_f[:, :, 1], arr_f[:, :, 2]
                mean_b, mean_g, mean_r = np.mean(b_chan), np.mean(g_chan), np.mean(r_chan)
                denom = (mean_g + mean_r - mean_b)
                vari_score = float((mean_g - mean_r) / denom) if abs(denom) > 1e-5 else 0.0
                vari_score = max(-1.0, min(1.0, vari_score))

                # 3x3 Sector Analysis
                cell_h, cell_w = h // 3, w // 3
                best_score = -999.0
                best_cell = (1, 1)
                best_name = "SAFE_LZ"
                sector_data = []

                for r_idx in range(3):
                    for c_idx in range(3):
                        sub_b = b_chan[r_idx*cell_h:(r_idx+1)*cell_h, c_idx*cell_w:(c_idx+1)*cell_w]
                        sub_g = g_chan[r_idx*cell_h:(r_idx+1)*cell_h, c_idx*cell_w:(c_idx+1)*cell_w]
                        sub_r = r_chan[r_idx*cell_h:(r_idx+1)*cell_h, c_idx*cell_w:(c_idx+1)*cell_w]
                        sg, sr, sb = np.mean(sub_g), np.mean(sub_r), np.mean(sub_b)
                        s_denom = (sg + sr - sb)
                        s_vari = float((sg - sr) / s_denom) if abs(s_denom) > 1e-5 else 0.0

                        if s_vari > 0.12:
                            s_name = "SAFE_LZ"
                            score = 1.0 + s_vari
                            color = (0, 220, 50)
                        elif s_vari >= -0.05:
                            s_name = "CANOPY"
                            score = 0.2 + s_vari
                            color = (0, 200, 240)
                        elif sb > (sr + sg) * 0.7:
                            s_name = "WATER"
                            score = -1.0
                            color = (255, 120, 0)
                        else:
                            s_name = "HAZARD"
                            score = -0.5
                            color = (0, 50, 255)

                        sector_data.append((r_idx, c_idx, s_name, score, color))
                        if score > best_score:
                            best_score = score
                            best_cell = (r_idx, c_idx)
                            best_name = s_name

                # Escape vector calculation
                dx = best_cell[1] - 1
                dy = -(best_cell[0] - 1)
                evade_deg = (np.degrees(np.arctan2(dx, dy)) + 360.0) % 360.0 if (dx != 0 or dy != 0) else 0.0
                needs_evasion = (best_cell != (1, 1))

                # Draw 3x3 Grid Overlay if enabled
                if show_grid:
                    overlay = frame_img.copy()
                    for (r_idx, c_idx, s_name, score, color) in sector_data:
                        x1, y1 = c_idx * cell_w, r_idx * cell_h
                        x2, y2 = (c_idx + 1) * cell_w, (r_idx + 1) * cell_h
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                        # Grid border
                        cv2.rectangle(frame_img, (x1, y1), (x2, y2), (60, 80, 100), 1)

                    # Blend transparent tint
                    cv2.addWeighted(overlay, 0.18, frame_img, 0.82, 0, frame_img)

                    # Mark Best Sector
                    bx1, by1 = best_cell[1] * cell_w, best_cell[0] * cell_h
                    bx2, by2 = (best_cell[1] + 1) * cell_w, (best_cell[0] + 1) * cell_h
                    cv2.rectangle(frame_img, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
                    cv2.putText(frame_img, "OPTIMAL LZ", (bx1 + 4, by1 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 0), 1, cv2.LINE_AA)

                    # Draw Escape Vector Arrow if evasion needed
                    if needs_evasion:
                        center_pt = (w // 2, h // 2)
                        target_pt = (best_cell[1] * cell_w + cell_w // 2, best_cell[0] * cell_h + cell_h // 2)
                        cv2.arrowedLine(frame_img, center_pt, target_pt, (0, 255, 100), 2, tipLength=0.25)
                        cv2.putText(frame_img, f"EVADE {evade_deg:.0f}*", (center_pt[0] + 10, center_pt[1] - 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 100), 1, cv2.LINE_AA)

                # Center Reticle
                cx, cy = w // 2, h // 2
                cv2.drawMarker(frame_img, (cx, cy), (0, 255, 200), markerType=cv2.MARKER_CROSS, markerSize=14, thickness=1)

                # Upper HUD Strip
                cv2.rectangle(frame_img, (0, 0), (w, 22), (10, 15, 20), -1)
                text_top = f"CAN: #{frame_id:04d} | {w}x{h} | {avg_fps:.1f} FPS | VARI: {vari_score:+.2f} | TTI: {tti_val:.1f}s"
                cv2.putText(frame_img, text_top, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 200), 1, cv2.LINE_AA)

                # Lower HUD Strip
                cv2.rectangle(frame_img, (0, h - 22), (w, h), (10, 15, 20), -1)
                evade_str = f"EVADE {evade_deg:.0f}*" if needs_evasion else "ON TARGET"
                text_bot = f"SLAI: {best_name} | {evade_str} | LINK: {rx_duration}ms | 'g':GRID"
                cv2.putText(frame_img, text_bot, (6, h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 255) if needs_evasion else (0, 255, 100), 1, cv2.LINE_AA)

                cv2.imshow(window_name, frame_img)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break
            elif key == ord('g'):
                show_grid = not show_grid
                print(f"[HUD] 3x3 Spatial Grid Overlay: {'ON' if show_grid else 'OFF'}")

    except KeyboardInterrupt:
        print("\n[i] Exiting viewer.")
    finally:
        if ser:
            ser.close()
        cv2.destroyAllWindows()
        print("[i] Viewer closed cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Cognitive CanSat Ground Video Stream Viewer")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (e.g. COM3 or COM4)")
    parser.add_argument("--baud", type=int, default=460800, help="Baud rate (default: 460800)")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic test stream")
    args = parser.parse_args()

    if not USE_CV2 and not args.demo:
        print("[NOTE] OpenCV is recommended for video HUD. Install via: pip install opencv-python")

    if args.demo:
        run_opencv_viewer("DEMO", args.baud, demo_mode=True)
        return

    # Auto-detect COM port if not specified
    target_port = args.port
    if not target_port:
        available = list_available_ports()
        if not available:
            print("[!] No active serial ports found.")
            print("    Plugging in the ESP-WROOM-32U node via USB?")
            print("    You can also test the viewer with synthetic video using: python firmware/ground_cam_viewer.py --demo")
            sys.exit(1)
        target_port = available[0]
        print(f"[i] Auto-selected port: {target_port} (Available: {available})")

    run_opencv_viewer(target_port, args.baud, demo_mode=False)


if __name__ == "__main__":
    main()
