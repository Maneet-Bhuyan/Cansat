"""
Executive Pitch Deck Generator (.pptx) for Cognitive CanSat
-----------------------------------------------------------
Generates a 12-slide widescreen (16:9) PowerPoint presentation at:
  reports/Cognitive_CanSat_Pitch_Deck.pptx

Designed for IEEE/aerospace competition judges, investors, and technical reviewers:
  Slide 1:  Title & Mission Overview
  Slide 2:  The Core Problem: Three Failure Modes in Atmospheric Sounding Probes
  Slide 3:  Dual-Tier Cyber-Physical System Architecture
  Slide 4:  Pillar 1: Physical Hardware Bench Characterization (N = 362 Real Packets)
  Slide 5:  Physics-Informed Hybrid State Estimation (EKF + ExtraTrees Calibrator)
  Slide 6:  Pillar 2: 100-Flight Unbiased Monte Carlo Ablation Results (-49.2% RMSE)
  Slide 7:  Aerodynamic Descent & Quantile Touchdown Prognostics (-94.8% TTD Error)
  Slide 8:  Edge TinyML: TinyLandingNet (7.15 KB INT8) vs. Ground Backbones
  Slide 9:  Five-Stage Out-of-Distribution (OOD) AerialVisionGuard (100% Rejection)
  Slide 10: Deterministic Telemetry Quality Analyzer & Distributed Lakehouse
  Slide 11: Full-Stack Web Serial Mission Control HUD (Desktop & Mobile)
  Slide 12: Unbiased Reproducibility Audit, Production Security & Deployment Readiness
"""

from __future__ import annotations

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
FIG_DIR = os.path.join(REPORTS_DIR, "figures")
OUT_PPTX = os.path.join(REPORTS_DIR, "Cognitive_CanSat_Pitch_Deck.pptx")

# Dark Aerospace Color Palette
BG_DARK = RGBColor(10, 17, 30)       # #0A111E
PANEL_BG = RGBColor(17, 28, 48)      # #111C30
PANEL_BORDER = RGBColor(38, 62, 102) # #263E66
CYAN_ACCENT = RGBColor(6, 182, 212)  # #06B6D4
GREEN_ACCENT = RGBColor(16, 185, 129)# #10B981
AMBER_ACCENT = RGBColor(245, 158, 11)# #F59E0B
TEXT_WHITE = RGBColor(241, 245, 249) # #F1F5F9
TEXT_MUTED = RGBColor(148, 163, 184) # #94A3B8


def apply_dark_background(slide) -> None:
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BG_DARK


def add_header(slide, slide_num: int, total_slides: int, category: str, title: str, subtitle: str) -> None:
    # Top accent bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = CYAN_ACCENT
    bar.line.fill.background()

    # Category pill
    tb_cat = slide.shapes.add_textbox(Inches(0.6), Inches(0.25), Inches(8.0), Inches(0.35))
    tf_cat = tb_cat.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = f"COGNITIVE CANSAT // {category.upper()}"
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = CYAN_ACCENT
    p_cat.font.name = "Consolas"

    # Slide counter right
    tb_num = slide.shapes.add_textbox(Inches(10.5), Inches(0.25), Inches(2.2), Inches(0.35))
    tf_num = tb_num.text_frame
    p_num = tf_num.paragraphs[0]
    p_num.alignment = PP_ALIGN.RIGHT
    p_num.text = f"SLIDE {slide_num:02d} / {total_slides:02d}"
    p_num.font.size = Pt(10)
    p_num.font.bold = True
    p_num.font.color.rgb = TEXT_MUTED
    p_num.font.name = "Consolas"

    # Main Title
    tb_title = slide.shapes.add_textbox(Inches(0.6), Inches(0.55), Inches(12.1), Inches(0.55))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE
    p_title.font.name = "Calibri"

    # Subtitle
    tb_sub = slide.shapes.add_textbox(Inches(0.6), Inches(1.08), Inches(12.1), Inches(0.4))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = subtitle
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = TEXT_MUTED
    p_sub.font.name = "Calibri"


def add_card(slide, left: float, top: float, width: float, height: float, title: str, bullets: list[str], accent_color=CYAN_ACCENT) -> None:
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = PANEL_BG
    card.line.color.rgb = PANEL_BORDER
    card.line.width = Pt(1.2)

    # Left accent stripe
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top + 0.12), Inches(0.07), Inches(height - 0.24))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = accent_color
    stripe.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(left + 0.22), Inches(top + 0.14), Inches(width - 0.36), Inches(height - 0.28))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = accent_color
    p0.font.name = "Calibri"
    p0.space_after = Pt(8)

    for b in bullets:
        p = tf.add_paragraph()
        p.text = f"- {b}"
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_WHITE
        p.font.name = "Calibri"
        p.space_after = Pt(6)


def add_metric_box(slide, left: float, top: float, width: float, height: float, value: str, label: str, detail: str, color=GREEN_ACCENT) -> None:
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    box.fill.solid()
    box.fill.fore_color.rgb = PANEL_BG
    box.line.color.rgb = color
    box.line.width = Pt(1.5)

    tb = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.12), Inches(width - 0.3), Inches(height - 0.24))
    tf = tb.text_frame
    tf.word_wrap = True

    p_val = tf.paragraphs[0]
    p_val.text = value
    p_val.font.size = Pt(26)
    p_val.font.bold = True
    p_val.font.color.rgb = color
    p_val.font.name = "Consolas"

    p_lbl = tf.add_paragraph()
    p_lbl.text = label
    p_lbl.font.size = Pt(12)
    p_lbl.font.bold = True
    p_lbl.font.color.rgb = TEXT_WHITE
    p_lbl.font.name = "Calibri"
    p_lbl.space_before = Pt(3)

    p_det = tf.add_paragraph()
    p_det.text = detail
    p_det.font.size = Pt(10.5)
    p_det.font.color.rgb = TEXT_MUTED
    p_det.font.name = "Calibri"
    p_det.space_before = Pt(2)


def add_notes(slide, notes_text: str) -> None:
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = notes_text


def build_pitch_deck() -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    total = 12

    # =========================================================================
    # SLIDE 1: TITLE & EXECUTIVE OVERVIEW
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s1)
    add_header(
        s1, 1, total, "Executive Pitch & IEEE System Overview",
        "Cognitive CanSat: Physics-Informed Telemetry & OOD-Guarded Edge TinyML",
        "Autonomous Atmospheric Sounding Pico-Satellite Platform | Authors: Maneet Bhuyan, Gurbashish Sena Nayak, Shubham Sharma, and Ganesh Vallabh M",
    )
    add_metric_box(s1, 0.6, 1.75, 2.85, 1.55, "-49.2%", "Altitude RMSE Reduction", "0.903 m Hybrid EKF+ExtraTrees vs. 1.776 m Raw Baro (N=100 Flights)", GREEN_ACCENT)
    add_metric_box(s1, 3.68, 1.75, 2.85, 1.55, "-94.8%", "Touchdown Countdown Error", "2.33 s Quantile GBR RMSE vs. 44.46 s Naive Ballistic Division", CYAN_ACCENT)
    add_metric_box(s1, 6.76, 1.75, 2.85, 1.55, "7.15 KB", "TinyLandingNet INT8 ROM", "93.04% EuroSAT Accuracy in 7,320 INT8 Params on ESP32-CAM", AMBER_ACCENT)
    add_metric_box(s1, 9.84, 1.75, 2.89, 1.55, "100.0%", "OOD Non-Aerial Rejection", "5-Stage AerialVisionGuard Blocks Faces, Occlusions & Blur (<1.8 ms)", GREEN_ACCENT)

    add_card(
        s1, 0.6, 3.55, 6.0, 3.4,
        "What Problem Does Cognitive CanSat Solve?",
        [
            "Pico-satellites (250-350 g) operate under strict 520 KB SRAM, 320 mW power, and 9600 bps RF telemetry limits.",
            "Venturi static-port suction corrupts barometric altitude during rapid freefall and canopy descent.",
            "Parachute pendulum oscillations (+/-18 deg) cause naive h/|vz| countdown timers to diverge by >40 seconds.",
            "Closed-set edge CNNs misclassify bench-handling human faces or camera occlusions as safe landing zones.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s1, 6.8, 3.55, 5.93, 3.4,
        "Key Innovations & Unbiased Validation",
        [
            "Physics-Informed EKF + Scale-Invariant ExtraTrees Calibrator trained on strictly disjoint flight ensembles.",
            "Quantile Gradient Boosting Touchdown Prognostics delivering calibrated [P10, P90] uncertainty intervals.",
            "3-Tier Vision Hierarchy: TinyLandingNet (7.15 KB edge) benchmarked against MobileNetV3-Small & ResNet-18.",
            "Zero-Leakage Scientific Audit: 100% of paper claims verified programmatically via ml/validate_paper_claims.py.",
        ],
        GREEN_ACCENT,
    )
    add_notes(s1, "Welcome judges and reviewers. Cognitive CanSat transforms a passive 350-gram sounding probe into an autonomous cyber-physical platform combining physics-informed state estimation, calibrated touchdown prognostics, and OOD-guarded TinyML terrain classification.")

    # =========================================================================
    # SLIDE 2: THE THREE CORE FAILURE MODES
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s2)
    add_header(
        s2, 2, total, "Problem Formulation",
        "Three Core Failure Modes in Atmospheric Sounding Pico-Satellites",
        "Why standard linear filters, ballistic formulas, and unguarded CNNs fail in turbulent descent",
    )
    add_card(
        s2, 0.6, 1.7, 3.9, 5.2,
        "1. Barometric Venturi Depression",
        [
            "High-velocity airflow across chassis static vents induces Bernoulli dynamic pressure depression: dP_q = -0.5 * c_p * rho * vz^2.",
            "Causes systematic positive altitude bias dh_q = +c_p * vz^2 / (2g) * (1 + 0.15 sin^2(psi)).",
            "Causal Savitzky-Golay smoothing (1.778 m RMSE) smooths white noise right around the biased curve without removing the offset.",
            "1.25 Hz packet jitter amplifies finite-difference velocity noise.",
        ],
        AMBER_ACCENT,
    )
    add_card(
        s2, 4.7, 1.7, 3.9, 5.2,
        "2. Parachute Pendulum Countdown Divergence",
        [
            "After pyrotechnic separation (>5G shock), the canopy enters coupled pendulum oscillation (+/-18 deg pitch/roll).",
            "Vertical descent rate vz fluctuates rapidly during wind gusts and thermal updrafts.",
            "Naive ballistic countdown tau = h / |vz| yields 44.46 s RMSE and negative R^2 (-2.01).",
            "Payload cameras and recovery beacons cannot trigger reliably without calibrated uncertainty bounds.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s2, 8.8, 1.7, 3.93, 5.2,
        "3. Closed-Set Softmax Overconfidence",
        [
            "ESP32-CAM provides only 520 KB internal SRAM (no PSRAM required for our 7.15 KB model).",
            "A 4-class softmax layer must sum to 1.0 even when viewing non-aerial Out-of-Distribution (OOD) inputs.",
            "Bench-top human faces, indoor lab walls, and lens caps trigger false >85% SAFE_LZ clearances on unguarded CNNs.",
            "Requires pre-neural and post-neural statistical/spectral gating.",
        ],
        GREEN_ACCENT,
    )
    add_notes(s2, "This slide details the three mathematical failure modes addressed in our IEEE paper: aerodynamic Venturi suction on the barometer, pendulum-induced countdown instability, and closed-set neural overconfidence on non-aerial camera inputs.")

    # =========================================================================
    # SLIDE 3: DUAL-TIER CYBER-PHYSICAL SYSTEM ARCHITECTURE
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s3)
    add_header(
        s3, 3, total, "System Architecture",
        "Dual-Tier Airborne Edge & Ground Lakehouse Architecture",
        "Split-compute pipeline bridging 433 MHz LoRa + 2.4 GHz ESP-NOW with FastAPI, SQLite WAL, and Redpanda/Kafka",
    )
    add_card(
        s3, 0.6, 1.7, 5.9, 2.5,
        "Tier 1: Airborne Avionics & Edge Vision (350g, 66x115mm)",
        [
            "Primary Flight MCU: Polls BMP280 (Pressure/Temp), DHT11/SHT31 (Humidity), MPU6050 6-DOF IMU (+/-16G, +/-2000 deg/s), u-blox NEO-6M GNSS, and 1S LiPo ADC at 1.25 Hz (dt = 0.8 s).",
            "Edge Vision Node (AI-Thinker ESP32-CAM, 240 MHz Xtensa LX6): Captures 320x240 QVGA frames, runs 7.15 KB INT8 TinyLandingNet across a 3x3 grid (16.3 ms/tile), and computes Escape Heading.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s3, 0.6, 4.4, 5.9, 2.5,
        "Dual-Link RF Downlink & Web Serial Ingestion",
        [
            "Sub-GHz LoRa (433/868/915 MHz @ 9600 bps): Transmits 13-channel CSV telemetry over 1.5 km slant range.",
            "2.4 GHz ESP-NOW (@ 460,800 baud UART bridge): Streams compressed QVGA MJPEG frames + 3x3 SLAI hazard telemetry.",
            "Direct Chromium Web Serial API (COM4 + COM5) or WebSocket streaming.",
        ],
        AMBER_ACCENT,
    )
    add_card(
        s3, 6.8, 1.7, 5.93, 5.2,
        "Tier 2: Ground Station Analytics & Telemetry Lakehouse",
        [
            "TelemetryQualityAnalyzer: Deterministic verification of packet completeness, clock jitter, GNSS (0,0) lock losses, and sensor step anomalies.",
            "Kinematics & Atmospheric Engines: Hypsometric altitude, Magnus-Tetens dew point, humid air density, 1D EKF, and complementary attitude filter.",
            "5-Model Tabular ML Suite: Random Forest Phase Classifier (97.96%), PyOD Isolation Forest (0.8407 ROC-AUC), Apogee GBR, ExtraTrees Calibrator, and Quantile TTD Prognostics.",
            "3-Tier Vision & OOD Guard: 5-Stage AerialVisionGuard + TinyLandingNet / MobileNetV3-Small / ResNet-18 comparison.",
            "Persistence: SQLite WAL (data/cansat_missions.db, 3,898 rows) + Redpanda/Kafka + TimescaleDB + MinIO S3.",
        ],
        GREEN_ACCENT,
    )
    add_notes(s3, "Our architecture separates hard real-time airborne sensing on the dual-MCU payload from heavyweight ground analytics and lakehouse persistence.")

    # =========================================================================
    # SLIDE 4: PILLAR 1 - PHYSICAL HARDWARE BENCH CHARACTERIZATION
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s4)
    add_header(
        s4, 4, total, "Validation Pillar 1: Real Hardware Telemetry",
        "Physical CanSat Hardware Bench-Top Characterization (N = 362 Real Packets)",
        "Empirical sensor noise covariances recorded from assembled avionics at ~868 m MSL in data/cansat_missions.db",
    )
    fig1_path = os.path.join(FIG_DIR, "paper_fig1_hardware_bench_characterization.png")
    if os.path.exists(fig1_path):
        s4.shapes.add_picture(fig1_path, Inches(0.6), Inches(1.65), width=Inches(7.7))

    add_card(
        s4, 8.5, 1.65, 4.23, 5.25,
        "Measured Hardware Noise Floor",
        [
            "3 Logged Hardware Missions (362 packets) stored in SQLite WAL database alongside 3,536 scenario frames (3,898 total rows).",
            "Stationary Runs (A2F9, 106 pkts; 2DD8, 135 pkts): Extracted 1-sigma white noise floor at 868.7 m MSL.",
            "Barometric Noise: sigma_h = 0.423 m, sigma_P = 0.143 hPa.",
            "Thermal/Humidity Noise: sigma_T = 0.165 C, sigma_RH = 1.515%.",
            "6-DOF MEMS IMU Noise: sigma_a = 0.022 G, sigma_g = 2.02 deg/s.",
            "Dynamic Session (74EE, 121 pkts): Verified +/-42 deg tilt and [-114.7, +98.9] deg/s angular tracking without I2C lockup.",
        ],
        CYAN_ACCENT,
    )
    add_notes(s4, "Pillar 1 grounds our entire study in real physical hardware measurements. We recorded 362 packets across 3 sessions on the assembled CanSat hardware at 868 meters MSL to extract exact sensor noise covariances.")

    # =========================================================================
    # SLIDE 5: PHYSICS-INFORMED HYBRID STATE ESTIMATION
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s5)
    add_header(
        s5, 5, total, "Methodology: State Estimation",
        "Physics-Informed Hybrid EKF + Scale-Invariant ExtraTrees Calibrator",
        "Eliminating aerodynamic Venturi pressure depression without train-test leakage or extrapolation clipping",
    )
    add_card(
        s5, 0.6, 1.7, 6.0, 5.2,
        "Stage 1: Adaptive 1D Constant-Velocity EKF",
        [
            "State Vector x_k = [h_k, vz_k]^T driven by vertical inertial acceleration u_k = (az_k - 1.0) * g0.",
            "Non-uniform dt_k transition matrices F_k and Q_k handle LoRa UART timing jitter (8 ms to 199 ms).",
            "High-G Shock Gate: When |a_k| > 2.5G (pyrotechnic apogee burst), process noise variance sigma_q^2 scales 10x to prevent filter lag.",
            "Provides smooth kinematic prior x_{k|k} and vertical velocity estimate vz_k.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s5, 6.8, 1.7, 5.93, 5.2,
        "Stage 2: Disjoint ExtraTrees Venturi Compensator",
        [
            "Direct altitude tree regressors fail when test apogees (up to 1,250 m) exceed training altitudes.",
            "Our residual_pipeline predicts the scale-invariant aerodynamic bias b_hat_k = f_ET(u_k) from 13 aerodynamic features (dynamic pressure proxy, tilt sin^2(psi), |a|, |omega|).",
            "Trained on 80 independent calibration flights (seed=1001, 35,342 samples) with unknown Venturi coefficients c_p in [0.38, 0.62].",
            "Convex Fusion: h_hat_k = 0.25 * h_{k|k}^EKF + 0.75 * (h_raw,k - b_hat_k).",
        ],
        GREEN_ACCENT,
    )
    add_notes(s5, "Instead of predicting absolute altitude—which clips outside the training elevation range—our ExtraTrees regressor learns the scale-invariant aerodynamic Venturi residual on a strictly disjoint seed=1001 calibration set.")

    # =========================================================================
    # SLIDE 6: PILLAR 2 - 100-FLIGHT MONTE CARLO ABLATION
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s6)
    add_header(
        s6, 6, total, "Validation Pillar 2: Unbiased 100-Flight Ablation",
        "5-Method State Estimation Ablation Across 100 Held-Out Flights (44,555 Frames)",
        "Evaluated on strictly disjoint seed=20260921 with zero analytical formula subtraction in the test loop",
    )
    fig2_path = os.path.join(FIG_DIR, "paper_fig2_monte_carlo_state_estimation.png")
    if os.path.exists(fig2_path):
        s6.shapes.add_picture(fig2_path, Inches(0.6), Inches(1.65), width=Inches(7.8))

    add_card(
        s6, 8.55, 1.65, 4.18, 5.25,
        "Unbiased Ablation Findings",
        [
            "1. Raw Barometric Altimetry: 1.776 +/- 0.258 m RMSE (Baseline).",
            "2. Causal Savitzky-Golay (N=11, p=2): 1.778 +/- 0.256 m RMSE (cannot remove Venturi offset).",
            "3. Standalone 1D EKF (No ML): 1.281 +/- 0.145 m RMSE (-27.9% reduction via IMU fusion).",
            "4. Standalone ExtraTrees (No EKF): 0.982 +/- 0.146 m RMSE (-44.7% reduction).",
            "5. Proposed Hybrid EKF + ExtraTrees: 0.903 +/- 0.130 m RMSE (-49.2% reduction, 95% CI [0.877, 0.928] m).",
        ],
        GREEN_ACCENT,
    )
    add_notes(s6, "Across 100 held-out flights totaling 44,555 frames, the hybrid EKF + ExtraTrees architecture achieves 0.903 m altitude RMSE, outperforming both standalone EKF (1.281 m) and standalone ExtraTrees (0.982 m).")

    # =========================================================================
    # SLIDE 7: DESCENT AERODYNAMICS & TOUCHDOWN PROGNOSTICS
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s7)
    add_header(
        s7, 7, total, "Prognostics & Trajectory Envelope",
        "Quantile Touchdown Prognostics & 10-Scenario Atmospheric Envelope",
        "94.8% countdown error reduction with unpadded [P10, P90] prediction intervals across turbulent descent regimes",
    )
    fig3_path = os.path.join(FIG_DIR, "paper_fig3_10scenario_kinematics_envelope.png")
    if os.path.exists(fig3_path):
        s7.shapes.add_picture(fig3_path, Inches(0.6), Inches(1.65), width=Inches(7.8))

    add_card(
        s7, 8.55, 1.65, 4.18, 5.25,
        "Touchdown & Phase Metrics",
        [
            "Quantile Gradient Boosting (alpha = 0.10, 0.50, 0.90) ingests 21 aerodynamic features (air density, dynamic pressure q, pendulum energy).",
            "Holdout TTD RMSE: 2.33 s vs. 44.46 s Naive Ballistic (-94.8% error, R^2 = 0.9963).",
            "Unpadded [P10, P90] Coverage (PICP): 81.27% on holdout (target 80.0%) and 74.8% across 100 Monte Carlo flights.",
            "Descent Regime Classifier: 99.75% holdout / 96.8% MC accuracy.",
            "Flight Phase Classifier: 97.96% holdout / 94.37% MC accuracy.",
        ],
        CYAN_ACCENT,
    )
    add_notes(s7, "By training Quantile Gradient Boosting models on 21 thermodynamic and pendulum-energy features, we cut countdown RMSE from 44.46 seconds down to 2.33 seconds.")

    # =========================================================================
    # SLIDE 8: EDGE TINYML VISION HIERARCHY
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s8)
    add_header(
        s8, 8, total, "Validation Pillar 3: Three-Tier Computer Vision",
        "TinyLandingNet (7.15 KB INT8) vs. MobileNetV3-Small & ResNet-18",
        "Benchmarking microcontroller depthwise-separable CNNs against CUDA-trained ground-station backbones on 27,000 EuroSAT patches",
    )
    fig4_path = os.path.join(FIG_DIR, "paper_fig4_vision_hierarchy_and_ood_guard.png")
    if os.path.exists(fig4_path):
        s8.shapes.add_picture(fig4_path, Inches(0.6), Inches(1.65), width=Inches(7.8))

    add_card(
        s8, 8.55, 1.65, 4.18, 5.25,
        "3-Tier Tradeoff Analysis",
        [
            "Tier 1 TinyLandingNet (Edge ESP32-CAM): 6,996 FP32 / 7,320 INT8 params, 7.15 KB Flash ROM, 0.783 MMACs, 93.04% Test Acc, 0.055 ms ONNX / 16.3 ms MCU.",
            "Tier 2 MobileNetV3-Small (Ground Fast): 1.52M params, 1,486 KB INT8, 99.68% Acc, 25.09 ms CPU.",
            "Tier 3 ResNet-18 (Ground Heavy): 11.18M params, 10,917 KB INT8, 99.73% Acc, 31.86 ms CPU.",
            "ResNet-18 requires 1,597x more parameters and exceeds the 520 KB ESP32 SRAM limit by >80x for a +6.69% accuracy gain.",
        ],
        AMBER_ACCENT,
    )
    add_notes(s8, "Tier 1 TinyLandingNet occupies just 7.15 KB of Flash ROM and achieves 93.04% accuracy on the 4,050-image EuroSAT test split, fitting effortlessly inside the 520 KB ESP32-CAM internal SRAM.")

    # =========================================================================
    # SLIDE 9: FIVE-STAGE OOD AERIAL VISION GUARD
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s9)
    add_header(
        s9, 9, total, "Open-Set Vision Safety",
        "Five-Stage Out-of-Distribution (OOD) AerialVisionGuard",
        "100% rejection of non-aerial inputs (human faces, indoor walls, lens caps, blur) in <1.8 ms overhead",
    )
    add_card(
        s9, 0.6, 1.7, 6.0, 5.2,
        "Pre-Neural Statistical & Spectral Gates (Stages 1-3)",
        [
            "Stage 1 (Luminance & Saturation Gate): Rejects lens-cap darkness (mu_Y < 18), overexposure (mu_Y > 245), or flat occlusion (sigma_Y < 6.0).",
            "Stage 2 (YCbCr Skin-Tone & VARI Portrait Gate): Rejects close-up human faces when central YCbCr skin ratio > 0.22, R > G + 12, and vegetation index VARI < -0.04.",
            "Stage 3 (Laplacian Micro-Texture Gate): Rejects smooth indoor walls and motion blur when Var(laplacian(Y)) < 14.0.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s9, 6.8, 1.7, 5.93, 5.2,
        "Post-Neural Energy & Physical Cross-Checks (Stages 4-5)",
        [
            "Stage 4 (Helmholtz Free Energy & Shannon Entropy): Computes E(x;T) = -T ln sum exp(z_c/T) and normalized entropy H(p). Flags H(p) > 0.78 or max_c p_c < 0.48 as uncertain.",
            "Stage 5 (VARI Spectral-Neural Cross-Check): Overrides false >70% SAFE_LZ or OBSTACLE_CANOPY predictions when physical vegetation index VARI < -0.06.",
            "Result: 100% OOD rejection across all 4 non-aerial hazard categories across all 3 CNN backbones while passing 100% of real drone descent videos.",
        ],
        GREEN_ACCENT,
    )
    add_notes(s9, "All closed-set CNNs fail when shown a human face or indoor wall during bench testing. Our 5-stage AerialVisionGuard blocks 100% of non-aerial frames in under 1.8 milliseconds.")

    # =========================================================================
    # SLIDE 10: DETERMINISTIC TELEMETRY QUALITY & LAKEHOUSE
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s10)
    add_header(
        s10, 10, total, "Data Engineering & Reliability",
        "Deterministic Telemetry Quality Analyzer & Distributed Lakehouse",
        "Objective, non-heuristic link verification (backend/core/telemetry_analyzer.py) before ML ingestion",
    )
    add_card(
        s10, 0.6, 1.7, 6.0, 5.2,
        "Objective Telemetry Integrity Metrics",
        [
            "Packet Completeness: Exact ratio N_valid / N_total plus malformed line indices and NaN/null cell coordinates.",
            "Temporal Regularity: Inter-packet dt distribution (mean, median, SD, jitter) and dropout intervals where dt >= 2.0 s.",
            "GNSS Lock & Step-Anomaly Detection: Identifies indoor/blackout (0.0, 0.0) lock losses and unphysical single-step jumps (|dT| > 5C, |dh| > 50m).",
            "Verified across all 10 scenarios (95.47% completeness in high-dropout Scenario 04; 31 blackout rows in Scenario 08).",
        ],
        AMBER_ACCENT,
    )
    add_card(
        s10, 6.8, 1.7, 5.93, 5.2,
        "Dual-Tier Persistence & Cloud Lakehouse",
        [
            "Local Zero-Config Persistence: SQLite Write-Ahead Logging (WAL) database (data/cansat_missions.db) with automatic session recovery.",
            "Event Streaming: Asynchronous Redpanda / Apache Kafka producer (cansat.telemetry.raw and cansat.vision.frames topics).",
            "Time-Series & Object Storage: TimescaleDB hypertables for SQL analytics + MinIO S3 bucket for raw QVGA frame archives.",
            "Automated Post-Flight Review (PFR): Generates 300-DPI PDF & Markdown executive mission reports in one click.",
        ],
        CYAN_ACCENT,
    )
    add_notes(s10, "Before any telemetry frame reaches our ML models, the TelemetryQualityAnalyzer verifies packet completeness, clock jitter, and GNSS lock integrity.")

    # =========================================================================
    # SLIDE 11: FULL-STACK MISSION CONTROL UI (DESKTOP & MOBILE)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s11)
    add_header(
        s11, 11, total, "Human-Machine Interface",
        "Responsive Web Serial Mission Control HUD (Desktop & Mobile Views)",
        "60 FPS GPU-accelerated telemetry dashboard with 3D WebGL attitude cylinder, Leaflet GNSS recovery, and live replay",
    )
    add_card(
        s11, 0.6, 1.7, 4.0, 5.2,
        "Real-Time 12-Tile Telemetry HUD",
        [
            "Chart.js time-series with decimated ring buffers (`animation: false`) for zero-GC-stutter 60 FPS rendering.",
            "Three.js WebGL 3D CanSat attitude model with one-click TARE UPRIGHT stationary calibration.",
            "Leaflet dark-matter GNSS ground track with Haversine distance and Google Maps field recovery deep-links.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s11, 4.75, 1.7, 3.9, 5.2,
        "Interactive Simulation & Vision Lab",
        [
            "Live 10-Scenario Selector (#demo-scenario-select) + 0.5x-10x frame scrubber for judge inspection.",
            "TinyML Vision Lab (tinyml.html): Live webcam OOD stress-testing, 3x3 SLAI hazard overlay, and 3-model comparison.",
            "Research Hub (results.html & pitch.html): Interactive figures, paper downloads, and slide deck.",
        ],
        GREEN_ACCENT,
    )
    add_card(
        s11, 8.8, 1.7, 3.93, 5.2,
        "Mobile & Field Recovery Ready",
        [
            "Dedicated Mobile Layout (css/mobile.css): Slide-out navigation drawer, touch-friendly controls (>=44px tap targets).",
            "Responsive breakpoints at 1280px, 1024px, 768px, and 480px.",
            "Field crew can open the dashboard on smartphones during parachute chase to track live GPS landing coordinates.",
        ],
        AMBER_ACCENT,
    )
    add_notes(s11, "The frontend is engineered for both Mission Control multi-monitor desktops and mobile field-recovery smartphones.")

    # =========================================================================
    # SLIDE 12: UNBIASED REPRODUCIBILITY, SECURITY & DEPLOYMENT
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s12)
    add_header(
        s12, 12, total, "Production Readiness & Verification",
        "Zero-Bias Scientific Verification, API Security & Cloud Deployment",
        "Full-stack compliance audit ensuring every paper claim and production endpoint is battle-tested",
    )
    add_metric_box(s12, 0.6, 1.75, 2.85, 1.5, "100%", "Claims Verified", "ml/validate_paper_claims.py Passes All 4 Pillars + LaTeX Rules", GREEN_ACCENT)
    add_metric_box(s12, 3.68, 1.75, 2.85, 1.5, "0", "Train-Test Leakage", "Disjoint Seeds (1001 Train vs 20260921 Test, 44,555 Frames)", CYAN_ACCENT)
    add_metric_box(s12, 6.76, 1.75, 2.85, 1.5, "11 / 11", "Automated Test Suites", "Python Unit Tests + Node.js Self-Tests + API Security Checks", AMBER_ACCENT)
    add_metric_box(s12, 9.84, 1.75, 2.89, 1.5, "READY", "Cloud & GitHub Release", "Docker + HuggingFace Spaces + Hostinger Split-Deploy Ready", GREEN_ACCENT)

    add_card(
        s12, 0.6, 3.5, 6.0, 3.45,
        "Unbiased Data & Scientific Integrity Guarantees",
        [
            "Zero Analytical Bias Subtraction in Test Loop: Test evaluation uses only learned models and causal filters.",
            "Strictly Causal Real-Time Filtering: Causal FIR Savitzky-Golay (pos=10) uses zero future lookahead.",
            "Unpadded Prediction Intervals: [P10, P90] coverage evaluated directly on raw quantile outputs.",
            "Transparent Limitations Section: Explicitly distinguishes N=362 bench hardware packets from 100-flight simulations.",
        ],
        CYAN_ACCENT,
    )
    add_card(
        s12, 6.8, 3.5, 5.93, 3.45,
        "Production Security & Deployment Hardening",
        [
            "HTTP Security Headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, X-XSS-Protection, Permissions-Policy.",
            "Input & Path Hardening: Path-traversal sanitization on scenario routes, 15 MB image / 16 MP bomb guards, 10 MB CSV upload limits.",
            "Complete Documentation: README.md, DEPLOYMENT_GUIDE.md, .env.example, IEEE LaTeX paper, and downloadable PPTX pitch deck.",
        ],
        GREEN_ACCENT,
    )
    add_notes(s12, "Thank you! Every claim in our IEEE paper is reproducibly verified by ml/validate_paper_claims.py, and the entire application is hardened and ready for deployment.")

    prs.save(OUT_PPTX)
    return OUT_PPTX


if __name__ == "__main__":
    out = build_pitch_deck()
    print(f"[+] Generated 12-slide executive pitch deck: {out} ({os.path.getsize(out):,} bytes)")
