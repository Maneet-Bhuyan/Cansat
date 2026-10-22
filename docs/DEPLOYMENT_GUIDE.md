# Cognitive CanSat Mission Control — Production Deployment & Security Guide

This document provides step-by-step deployment, security hardening, and verification instructions for launching the **Cognitive CanSat Mission Control & AI Ground Station** across local hardware workstations, Docker containers, Hugging Face Spaces, and Hostinger cloud/VPS hosting.

---

## 1. Pre-Launch Engineering & Security Checklist

Every production deployment of the Cognitive CanSat platform enforces the following engineering controls:

1. **HTTP Security Headers Middleware (`backend/app.py`)**:
   - `X-Content-Type-Options: nosniff` (prevents MIME-sniffing attacks)
   - `X-Frame-Options: SAMEORIGIN` (prevents clickjacking embeds)
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `X-XSS-Protection: 1; mode=block`
   - `Permissions-Policy: geolocation=(), microphone=()`
2. **Input Sanitization & Path Traversal Prevention**:
   - All scenario identifiers (`/api/analysis/scenario/{scenario_name}`, `/api/analysis/quality/{scenario_name}`, `/api/pipeline/stream-scenario`) are validated via strict regex `^[A-Za-z0-9_\-]+$` and canonical `os.path.realpath` containment inside `test_cases/`.
   - Export filenames in `Content-Disposition` headers are sanitized via `_sanitize_filename_token`.
3. **Payload Size & Memory Guardrails**:
   - `/api/vision/classify-frame` enforces a `15 MB` Base64 payload cap and automatically downscales frames exceeding `16 MP` (`4096x4096`) prior to tensor allocation.
   - `/api/analysis/quality/analyze-csv` enforces a `10 MB` CSV string cap.
4. **Zero-Leakage Scientific Reproducibility**:
   - Run `python ml/validate_paper_claims.py` prior to release to verify all 4 validation pillars (Hardware Bench, 10-Scenario Suite, 100-Flight Monte Carlo Ensemble, and 3-Tier Vision + 5-Stage OOD Guard).

---

## 2. Local Hardware Ground Station Launch (Windows / Linux / macOS)

```bash
# 1. Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 2. Install locked dependencies
pip install -r requirements.txt

# 3. Copy environment template and configure COM ports if using physical LoRa/ESP32-CAM receivers
cp .env.example .env

# 4. Run automated pre-flight verification
python ml/validate_paper_claims.py
node tests/selftest.js

# 5. Start the FastAPI Ground Control Server
python launch.py
```

Access the application surfaces at:
- **3D Mission Control HUD**: `http://127.0.0.1:8000/index.html`
- **TinyML Optical Hazard Lab**: `http://127.0.0.1:8000/tinyml.html`
- **Telemetry Analytics & Ablation Studio**: `http://127.0.0.1:8000/analysis.html`
- **ML Architecture & Model Zoo**: `http://127.0.0.1:8000/models.html`
- **Scientific Validation & Artifact Hub**: `http://127.0.0.1:8000/results.html`
- **Interactive Executive Pitch Deck**: `http://127.0.0.1:8000/pitch.html`
- **Health & Readiness Probe**: `http://127.0.0.1:8000/api/health`

---

## 3. Hugging Face Spaces Deployment (Docker SDK)

The repository root includes a root-less, production-hardened [`Dockerfile`](file:///e:/Cansat/Dockerfile) running under `UID 1000` compatible with Hugging Face Spaces Docker containers.

1. Create a new Space on Hugging Face (`https://huggingface.co/new-space`) and select **Docker** as the Space SDK.
2. In your Space settings or `README.md` YAML frontmatter, set `app_port: 8000` (or pass `PORT=7860` in Space Variables; the `Dockerfile` dynamically binds `--port ${PORT}`).
3. Push the repository to your Hugging Face Space remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<your-space-name>
   git push space main
   ```
4. Verify the deployment via `https://<your-space>.hf.space/api/health`.

---

## 4. Hostinger VPS / Custom Domain Deployment

The [`deploy/`](file:///e:/Cansat/deploy) directory contains turnkey production configs for Ubuntu/Debian VPS instances on Hostinger:

- [`deploy/setup_hostinger.sh`](file:///e:/Cansat/deploy/setup_hostinger.sh): Automated provisioning script (UFW firewall, Nginx reverse proxy, systemd daemon, Let's Encrypt TLS).
- [`deploy/cansat.service`](file:///e:/Cansat/deploy/cansat.service): Systemd unit running Uvicorn with automatic restart on failure.
- [`deploy/cansat.nginx.conf`](file:///e:/Cansat/deploy/cansat.nginx.conf): Nginx reverse proxy supporting HTTP/1.1 WebSocket upgrades (`/ws/telemetry`, `/ws/serial`) and static asset caching.
- [`deploy/docker-compose.prod.yml`](file:///e:/Cansat/deploy/docker-compose.prod.yml): Production Docker Compose stack.
