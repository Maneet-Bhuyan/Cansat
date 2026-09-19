/**
 * Cognitive CanSat - Interactive Mission Timeline Scrubber
 * Simulates the 6 flight phases with synchronized telemetry, camera views,
 * and onboard event logs.
 * Zero emojis.
 */

(function () {
  'use strict';

  const PHASES = [
    {
      id: 'boost',
      name: 'Rocket Launch & Boost',
      time: 0,
      alt: 0,
      vspd: 32.5,
      accel: 4.8,
      packetType: 'CALIBRATION & BOOST TELEMETRY (CSV @ 9600)',
      cameraState: 'LAUNCH_PAD',
      cameraDesc: 'Camera unpowered in launch tube. Optical aperture protected from booster particulate.',
      eventLog: 'T+ 00:00.0 - Ground pad baseline established (1013.25 hPa). High-G booster ignition detected.'
    },
    {
      id: 'apogee',
      name: 'Apex & Apogee Burst',
      time: 45,
      alt: 1200,
      vspd: 0.2,
      accel: 0.12,
      packetType: 'APOGEE_EVENT_TELEMETRY (CSV @ 9600)',
      cameraState: 'APOGEE_CLOUDS',
      cameraDesc: 'Upper atmospheric high-altitude horizon. Horizon detection confirms nadir orientation.',
      eventLog: 'T+ 00:45.0 - Vertical velocity zero-crossing. Peak apogee registered at 1200.4m AGL.'
    },
    {
      id: 'separation',
      name: 'Separation & Ejection Shock',
      time: 50,
      alt: 1150,
      vspd: -4.2,
      accel: 3.6,
      packetType: 'EJECTION_SHOCK_TELEMETRY (CSV @ 9600)',
      cameraState: 'TUMBLE_HORIZON',
      cameraDesc: 'Rapid angular rotation during separation. IMU complementary filter damping attitude tumble.',
      eventLog: 'T+ 00:50.0 - Ejection shock transient (3.6G). CanSat clears rocket airframe.'
    },
    {
      id: 'descent',
      name: 'Steady Terminal Descent',
      time: 70,
      alt: 950,
      vspd: -5.2,
      accel: 1.02,
      packetType: 'NOMINAL_ATMOSPHERIC_SOUNDING (CSV @ 9600)',
      cameraState: 'DISTANT_TERRAIN',
      cameraDesc: 'Descent stabilizes at 5.2 m/s. High-altitude landscape visible below.',
      eventLog: 'T+ 01:10.0 - Terminal velocity reached. Atmospheric sounding engine logging temperature lapse rate.'
    },
    {
      id: 'tinyml_window',
      name: 'TinyML Vision & Evasion Window',
      time: 120,
      alt: 320,
      vspd: -5.0,
      accel: 1.01,
      packetType: 'DUAL-LINK: LoRa Telemetry + ESP-NOW 3x3 Hazard Vector',
      cameraState: 'TINYML_ACTIVE_GRID',
      cameraDesc: 'OV3660 captures 64x48 frames at 10 FPS. TinyLandingNet classifies 3x3 sectors: Center=HAZARD, commands EVADE 090.',
      eventLog: 'T+ 02:00.0 - Altitude < 500m. Edge TinyML active. Obstacle detected in center nadir sector. Evasion vector calculated.'
    },
    {
      id: 'touchdown',
      name: 'Touchdown & Recovery Beacon',
      time: 180,
      alt: 0,
      vspd: 0.0,
      accel: 1.0,
      packetType: 'RECOVERY_BEACON (GPS Lat/Lon @ 9600)',
      cameraState: 'GROUND_TOUCHDOWN',
      cameraDesc: 'CanSat rests safely in open grass field. Camera confirms zero motion.',
      eventLog: 'T+ 03:00.0 - Touchdown confirmed. GPS coordinates locked: 22.5727 N, 88.3655 E. Acoustic beacon active.'
    }
  ];

  let slider, altDisplay, vspdDisplay, timeDisplay, phaseBadge, packetBadge, eventLogDisplay, cameraCanvas;
  let ctx;

  function initMissionSlider() {
    slider = document.getElementById('mission-scrubber');
    altDisplay = document.getElementById('scrubber-alt');
    vspdDisplay = document.getElementById('scrubber-vspd');
    timeDisplay = document.getElementById('scrubber-time');
    phaseBadge = document.getElementById('scrubber-phase-badge');
    packetBadge = document.getElementById('scrubber-packet-badge');
    eventLogDisplay = document.getElementById('scrubber-event-log');
    cameraCanvas = document.getElementById('scrubber-camera-canvas');

    if (!slider || !cameraCanvas) return;

    ctx = cameraCanvas.getContext('2d');

    slider.addEventListener('input', () => {
      updateTimeline(parseInt(slider.value, 10));
    });

    // Preset buttons
    document.querySelectorAll('[data-scrubber-phase]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetIndex = parseInt(btn.getAttribute('data-scrubber-phase'), 10);
        slider.value = targetIndex;
        updateTimeline(targetIndex);
      });
    });

    // Initial draw
    updateTimeline(0);
  }

  function updateTimeline(phaseIndex) {
    const phase = PHASES[phaseIndex] || PHASES[0];

    // Update text readouts
    if (altDisplay) altDisplay.textContent = phase.alt + ' m';
    if (vspdDisplay) vspdDisplay.textContent = (phase.vspd > 0 ? '+' : '') + phase.vspd.toFixed(1) + ' m/s';
    if (timeDisplay) {
      const mins = Math.floor(phase.time / 60);
      const secs = phase.time % 60;
      timeDisplay.textContent = 'T+ ' + String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
    }
    if (phaseBadge) phaseBadge.textContent = phase.name;
    if (packetBadge) packetBadge.textContent = phase.packetType;
    if (eventLogDisplay) eventLogDisplay.textContent = phase.eventLog;

    // Update phase button states
    document.querySelectorAll('[data-scrubber-phase]').forEach((btn, idx) => {
      btn.classList.toggle('active', idx === phaseIndex);
    });

    // Render Simulated Camera View
    renderSimulatedCamera(phase);
  }

  function renderSimulatedCamera(phase) {
    if (!ctx) return;
    const w = cameraCanvas.width;
    const h = cameraCanvas.height;

    ctx.clearRect(0, 0, w, h);

    if (phase.cameraState === 'LAUNCH_PAD') {
      // Dark tube interior
      ctx.fillStyle = '#05070c';
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 2;
      ctx.strokeRect(10, 10, w - 20, h - 20);
      ctx.fillStyle = '#64748b';
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText('CAMERA STANDBY // SENSOR GATED', 20, h / 2);
    } else if (phase.cameraState === 'APOGEE_CLOUDS') {
      // High altitude sky & clouds
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, '#0c4a6e');
      grad.addColorStop(0.6, '#38bdf8');
      grad.addColorStop(1, '#e0f2fe');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Cloud puffs
      ctx.fillStyle = 'rgba(255, 255, 255, 0.65)';
      ctx.beginPath();
      ctx.arc(w * 0.3, h * 0.7, 40, 0, Math.PI * 2);
      ctx.arc(w * 0.5, h * 0.75, 55, 0, Math.PI * 2);
      ctx.arc(w * 0.7, h * 0.7, 45, 0, Math.PI * 2);
      ctx.fill();
    } else if (phase.cameraState === 'TUMBLE_HORIZON') {
      // Tumbled horizon
      ctx.save();
      ctx.translate(w / 2, h / 2);
      ctx.rotate(0.45);
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(-w, 0, w * 2, h);
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(-w, -h, w * 2, h);
      ctx.restore();
    } else if (phase.cameraState === 'DISTANT_TERRAIN') {
      // Distant patchwork terrain
      ctx.fillStyle = '#1e3a1e';
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = '#2d5a27';
      ctx.fillRect(w * 0.2, h * 0.2, w * 0.6, h * 0.5);
      ctx.fillStyle = '#475569';
      ctx.fillRect(w * 0.5, h * 0.1, 15, h * 0.8); // Road
    } else if (phase.cameraState === 'TINYML_ACTIVE_GRID') {
      // Terrain with building in center and open grass to right
      ctx.fillStyle = '#166534'; // Grass base
      ctx.fillRect(0, 0, w, h);

      // Center building / asphalt hazard
      ctx.fillStyle = '#334155';
      ctx.fillRect(w * 0.3, h * 0.25, w * 0.4, h * 0.5);
      ctx.fillStyle = '#475569';
      ctx.fillRect(w * 0.35, h * 0.3, w * 0.3, h * 0.4);

      // Overlay 3x3 Spatial Hazard Grid
      const cellW = w / 3;
      const cellH = h / 3;
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.4)';
      ctx.lineWidth = 1;

      for (let i = 1; i < 3; i++) {
        ctx.beginPath();
        ctx.moveTo(i * cellW, 0);
        ctx.lineTo(i * cellW, h);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(0, i * cellH);
        ctx.lineTo(w, i * cellH);
        ctx.stroke();
      }

      // Highlight Center Sector [1,1] as CRITICAL_HAZARD
      ctx.fillStyle = 'rgba(239, 68, 68, 0.45)';
      ctx.fillRect(cellW, cellH, cellW, cellH);
      ctx.fillStyle = '#ef4444';
      ctx.font = 'bold 10px "JetBrains Mono", monospace';
      ctx.fillText('HAZARD', cellW + 15, cellH + 35);

      // Highlight Right Sector [1,2] as SAFE_LZ
      ctx.fillStyle = 'rgba(16, 185, 129, 0.35)';
      ctx.fillRect(cellW * 2, cellH, cellW, cellH);
      ctx.fillStyle = '#10b981';
      ctx.fillText('SAFE LZ', cellW * 2 + 15, cellH + 35);

      // Evasion Arrow pointing right
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(w / 2, h / 2);
      ctx.lineTo(w * 0.8, h / 2);
      ctx.lineTo(w * 0.75, h / 2 - 8);
      ctx.moveTo(w * 0.8, h / 2);
      ctx.lineTo(w * 0.75, h / 2 + 8);
      ctx.stroke();

      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 11px "JetBrains Mono", monospace';
      ctx.fillText('EVADE 090 deg', w * 0.55, h * 0.4);
    } else if (phase.cameraState === 'GROUND_TOUCHDOWN') {
      // Grass closeup
      ctx.fillStyle = '#15803d';
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = '#166534';
      for (let i = 0; i < 30; i++) {
        const x = (i * 17) % w;
        const y = (i * 29) % h;
        ctx.fillRect(x, y, 6, 12);
      }
      ctx.fillStyle = '#86efac';
      ctx.font = 'bold 11px "JetBrains Mono", monospace';
      ctx.fillText('TOUCHDOWN CONFIRMED // SAFE LZ', 15, h - 15);
    }

    // Top HUD bar on camera
    ctx.fillStyle = 'rgba(7, 10, 19, 0.75)';
    ctx.fillRect(0, 0, w, 22);
    ctx.fillStyle = '#38bdf8';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.fillText('ALT: ' + phase.alt + 'm | VSPD: ' + phase.vspd + 'm/s | CAM: ' + phase.cameraState, 8, 15);
  }

  window.addEventListener('DOMContentLoaded', initMissionSlider);
})();
