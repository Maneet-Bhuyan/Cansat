# Hostinger Deployment Guide - Cognitive CanSat Platform

This guide outlines everything required to deploy the complete Cognitive CanSat platform (FastAPI backend, persistent WebSockets, PyTorch models, SQLite WAL database, and responsive frontend) on Hostinger with support for both desktop and mobile views.

---

## 1. Hostinger Hosting Plan Selection

### Recommended: Hostinger KVM VPS (KVM 2 or KVM 4)
- **Operating System**: Ubuntu 22.04 or 24.04 LTS
- **Hardware**: Minimum 2 vCPUs, 8 GB RAM (to smoothly support PyTorch CPU inference and multiple concurrent WebSocket clients).
- **Why VPS is Required**:
  The application runs a persistent Python FastAPI daemon with asynchronous WebSockets (`/ws/serial`, `/ws/telemetry`), SQLite WAL database writes, and machine learning models (`torch`, `torchvision`, `cv2`, `scikit-learn`). Standard shared hosting environments kill background processes, lack persistent WebSocket connections, and cap RAM below what PyTorch requires.

---

## 2. One-Command Automated Setup on VPS

Connect to your Hostinger VPS via SSH as root:
```bash
ssh root@YOUR_SERVER_IP
```

Clone the repository and run the automated setup script:
```bash
git clone https://github.com/Maneet-Bhuyan/Cansat.git /var/www/cansat
cd /var/www/cansat
chmod +x deploy/setup_hostinger.sh
./deploy/setup_hostinger.sh
```

The script will automatically:
1. Install system runtime packages (Python 3, Nginx, Certbot, OpenCV libraries).
2. Create the Python virtual environment and install dependencies.
3. Configure and start the systemd service (`cansat.service`).
4. Configure Nginx reverse proxy with WebSocket support on port 80.

---

## 3. Domain & Free SSL Setup (Mandatory for Web Serial & Mobile)

Modern web browsers require HTTPS for:
- Web Serial API (`navigator.serial`) on desktop.
- Secure WebSockets (`wss://`).
- Geolocation and camera sensor access.

To point your domain:
1. In your Hostinger DNS Management console, point your domain `A record` to your VPS IP address:
   - `@` -> `YOUR_VPS_IP`
   - `www` -> `YOUR_VPS_IP`
2. Run Certbot to generate and install the free SSL certificate:
   ```bash
   certbot --nginx -d your-domain.com -d www.your-domain.com
   ```
3. Certbot will automatically reconfigure Nginx for HTTPS and restart the web server.

---

## 4. Mobile and Desktop View Readiness

### Desktop View Features
- 3-column / 4-column high-density telemetry grid.
- Interactive Three.js 3D attitude gyro cylinder.
- Real-time 3x3 tactical camera HUD with OpenCV style reticle.
- USB Web Serial direct connection via USB COM port (Chrome, Edge, Opera).
- Side-by-side post-flight review reports, SQL data query manager, and distributed lakehouse controls.

### Mobile View Features & Considerations
- **Viewport Tag**: All HTML templates include `<meta name="viewport" content="width=device-width, initial-scale=1.0">`.
- **Responsive Layout**: Tailwind and CSS grids automatically collapse to single-column cards on screens under 768px.
- **Web Serial on Mobile**:
  - iOS WebKit (Safari, Chrome on iPhone) does NOT support the Web Serial API.
  - On mobile, live telemetry streams seamlessly via the **Python Cloud Bridge WebSocket** (`wss://your-domain.com/ws/serial`) or runs in deterministic flight simulation / replay mode.
- **Touch-Friendly Controls**: Touch targets are sized for mobile fingertips (minimum 44x44px hit areas on key buttons).

---

## 5. Maintenance and Service Management

Check application service status:
```bash
systemctl status cansat.service
```

Restart application after pulling code updates:
```bash
cd /var/www/cansat
git pull origin main
systemctl restart cansat.service
```

View live server logs:
```bash
journalctl -u cansat.service -f
```
