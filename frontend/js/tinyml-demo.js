/**
 * Cognitive CanSat - TinyML Deep Dive & Interactive Replay Engine
 * Features:
 *   - Interactive Model Inspector (FP32 vs INT8 Quantization metrics)
 *   - Inference Saliency / Tensor Activation Heatmap Visualizer
 *   - Video Replay Simulator with selectable FPS (5 FPS, 10 FPS, Native 30 FPS)
 *   - Real-time 3x3 spatial hazard grid and EVADE theta HUD overlay
 *   - Zero emojis.
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. MODEL INSPECTOR (FP32 vs INT8 Quantization)
  // =========================================================================

  const MODEL_SPECS = {
    fp32: {
      label: 'FP32 Baseline (Floating-Point 32-bit)',
      sram: '1,840 KB',
      sramPct: 353, // 353% of 520KB (overflows!)
      sramStatus: 'EXCEEDS ESP32 SRAM (520 KB) - WILL CRASH',
      sramColor: '#ef4444',
      flash: '4.60 MB',
      flashPct: 115,
      flashStatus: 'Exceeds standard 4MB Flash partition',
      flashColor: '#ef4444',
      maccs: '12.4M',
      latency: '280 ms',
      fps: '3.5 FPS',
      accuracy: '94.2%',
      power: '640 mW',
      desc: 'Standard unquantized PyTorch/TensorFlow weights. Requires external PSRAM for every forward pass and consumes excessive power during aerial descent.'
    },
    int8: {
      label: 'INT8 Quantized (Edge Impulse / TFLite Micro)',
      sram: '142 KB',
      sramPct: 27, // 27% of 520KB (fits easily!)
      sramStatus: 'FITS COMFORTABLY IN INTERNAL SRAM (520 KB)',
      sramColor: '#10b981',
      flash: '0.38 MB (380 KB)',
      flashPct: 9.5,
      flashStatus: 'Leaves 3.6MB free for firmware & OTA updates',
      flashColor: '#10b981',
      maccs: '3.1M (4x Reduction)',
      latency: '38 ms (7.3x Speedup)',
      fps: '26.3 FPS',
      accuracy: '92.8% (Only 1.4% Delta)',
      power: '320 mW (50% Power Savings)',
      desc: 'Asymmetric 8-bit integer post-training quantization. Enables deterministic real-time inference entirely in fast internal SRAM without memory bus contention.'
    }
  };

  function initModelInspector() {
    const toggleFp32 = document.getElementById('toggle-fp32');
    const toggleInt8 = document.getElementById('toggle-int8');

    if (!toggleFp32 || !toggleInt8) return;

    toggleFp32.addEventListener('click', () => setModelMode('fp32'));
    toggleInt8.addEventListener('click', () => setModelMode('int8'));

    setModelMode('int8');
  }

  function setModelMode(mode) {
    const data = MODEL_SPECS[mode];
    if (!data) return;

    const btnFp32 = document.getElementById('toggle-fp32');
    const btnInt8 = document.getElementById('toggle-int8');

    if (btnFp32) btnFp32.classList.toggle('active', mode === 'fp32');
    if (btnInt8) btnInt8.classList.toggle('active', mode === 'int8');

    const sramVal = document.getElementById('inspector-sram-val');
    const sramBar = document.getElementById('inspector-sram-bar');
    const sramNote = document.getElementById('inspector-sram-note');

    const flashVal = document.getElementById('inspector-flash-val');
    const flashBar = document.getElementById('inspector-flash-bar');
    const flashNote = document.getElementById('inspector-flash-note');

    const maccsVal = document.getElementById('inspector-maccs-val');
    const latencyVal = document.getElementById('inspector-latency-val');
    const fpsVal = document.getElementById('inspector-fps-val');
    const accVal = document.getElementById('inspector-acc-val');
    const descVal = document.getElementById('inspector-desc-val');

    if (sramVal) sramVal.textContent = data.sram;
    if (sramBar) {
      sramBar.style.width = Math.min(100, data.sramPct) + '%';
      sramBar.style.backgroundColor = data.sramColor;
    }
    if (sramNote) {
      sramNote.textContent = data.sramStatus;
      sramNote.style.color = data.sramColor;
    }

    if (flashVal) flashVal.textContent = data.flash;
    if (flashBar) {
      flashBar.style.width = Math.min(100, data.flashPct) + '%';
      flashBar.style.backgroundColor = data.flashColor;
    }
    if (flashNote) {
      flashNote.textContent = data.flashStatus;
      flashNote.style.color = data.flashColor;
    }

    if (maccsVal) maccsVal.textContent = data.maccs;
    if (latencyVal) latencyVal.textContent = data.latency;
    if (fpsVal) fpsVal.textContent = data.fps;
    if (accVal) accVal.textContent = data.accuracy;
    if (descVal) descVal.textContent = data.desc;
  }

  // =========================================================================
  // 2. INFERENCE TENSOR ACTIVATION / SALIENCY VISUALIZER
  // =========================================================================

  const TERRAINS = {
    grass: {
      name: 'Open Grassland (Nominal LZ)',
      classification: 'SAFE_LZ',
      statusColor: '#10b981',
      confidence: '97.4%',
      riskScore: '0.04 (Low Risk)',
      decision: 'NOMINAL DESCENT - SAFE LANDING ZONE CONFIRMED',
      explanation: 'Low high-frequency spatial gradients, uniform vegetative chroma (520nm peak reflectance), zero abrupt structural edges.'
    },
    urban: {
      name: 'Urban Buildings & Rooftops',
      classification: 'CRITICAL_HAZARD',
      statusColor: '#ef4444',
      confidence: '96.8%',
      riskScore: '0.94 (Extreme Risk)',
      decision: 'CRITICAL HAZARD - ADVISORY EVADE 090 DEG TOWARD OPEN SECTOR',
      explanation: 'High edge density (>450 pixels), desaturated asphalt/concrete reflectance, and rectangular structural shadows trigger hazard classification.'
    },
    water: {
      name: 'Water Body (Lake / River)',
      classification: 'CRITICAL_HAZARD',
      statusColor: '#ef4444',
      confidence: '98.1%',
      riskScore: '0.96 (Extreme Risk)',
      decision: 'CRITICAL HAZARD - WATER IMMERSION RISK DETECTED',
      explanation: 'High specular glare, characteristic cyan-blue chromatic shift, and zero surface vegetative texture trigger emergency avoidance.'
    },
    boulders: {
      name: 'Mixed Terrain with Boulder Cluster',
      classification: 'OBSTACLE_DETECTED',
      statusColor: '#f59e0b',
      confidence: '91.5%',
      riskScore: '0.78 (Moderate Risk)',
      decision: 'OBSTACLE IN NADIR SECTOR - ADVISORY EVADE 180 DEG SOUTH',
      explanation: 'Localized high-contrast edge cluster in center nadir sector. Adjacent sectors exhibit flat terrain suitable for touchdown.'
    }
  };

  let activeTerrainKey = 'urban';

  function initInferenceVisualizer() {
    const rawCanvas = document.getElementById('visualizer-raw-canvas');
    const heatCanvas = document.getElementById('visualizer-heat-canvas');

    if (!rawCanvas || !heatCanvas) return;

    document.querySelectorAll('[data-terrain]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tKey = btn.getAttribute('data-terrain');
        if (tKey && TERRAINS[tKey]) {
          activeTerrainKey = tKey;
          document.querySelectorAll('[data-terrain]').forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          renderTerrainComparison(tKey);
        }
      });
    });

    renderTerrainComparison(activeTerrainKey);
  }

  function renderTerrainComparison(terrainKey) {
    const data = TERRAINS[terrainKey];
    if (!data) return;

    const rawCanvas = document.getElementById('visualizer-raw-canvas');
    const heatCanvas = document.getElementById('visualizer-heat-canvas');
    if (!rawCanvas || !heatCanvas) return;

    const rawCtx = rawCanvas.getContext('2d');
    const heatCtx = heatCanvas.getContext('2d');

    const w = rawCanvas.width;
    const h = rawCanvas.height;

    // 1. Draw Raw Downlinked Frame
    rawCtx.clearRect(0, 0, w, h);

    if (terrainKey === 'grass') {
      rawCtx.fillStyle = '#166534';
      rawCtx.fillRect(0, 0, w, h);
      // Grass texture
      rawCtx.fillStyle = '#15803d';
      for (let i = 0; i < 60; i++) {
        rawCtx.fillRect((i * 23) % w, (i * 37) % h, 4, 8);
      }
    } else if (terrainKey === 'urban') {
      rawCtx.fillStyle = '#1e3a1e';
      rawCtx.fillRect(0, 0, w, h);
      // Large building in center
      rawCtx.fillStyle = '#334155';
      rawCtx.fillRect(w * 0.25, h * 0.2, w * 0.5, h * 0.6);
      rawCtx.fillStyle = '#475569';
      rawCtx.fillRect(w * 0.3, h * 0.25, w * 0.4, h * 0.5);
      // Roof AC unit / texture
      rawCtx.fillStyle = '#64748b';
      rawCtx.fillRect(w * 0.4, h * 0.35, 25, 20);
      rawCtx.fillRect(w * 0.55, h * 0.5, 30, 20);
    } else if (terrainKey === 'water') {
      rawCtx.fillStyle = '#0369a1';
      rawCtx.fillRect(0, 0, w, h);
      // Water ripples
      rawCtx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      rawCtx.lineWidth = 1.5;
      for (let y = 30; y < h; y += 25) {
        rawCtx.beginPath();
        rawCtx.moveTo(10, y);
        rawCtx.bezierCurveTo(w * 0.3, y - 8, w * 0.6, y + 8, w - 10, y);
        rawCtx.stroke();
      }
    } else if (terrainKey === 'boulders') {
      rawCtx.fillStyle = '#22c55e';
      rawCtx.fillRect(0, 0, w, h);
      // Boulder cluster in center
      rawCtx.fillStyle = '#475569';
      rawCtx.beginPath();
      rawCtx.arc(w * 0.5, h * 0.45, 35, 0, Math.PI * 2);
      rawCtx.arc(w * 0.4, h * 0.55, 25, 0, Math.PI * 2);
      rawCtx.arc(w * 0.6, h * 0.55, 28, 0, Math.PI * 2);
      rawCtx.fill();
    }

    // 2. Draw Saliency / Tensor Activation Heatmap
    heatCtx.clearRect(0, 0, w, h);

    if (terrainKey === 'grass') {
      // Uniform low activation (dark blue/purple with slight green)
      const grad = heatCtx.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w / 2);
      grad.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
      grad.addColorStop(1, 'rgba(15, 23, 42, 0.9)');
      heatCtx.fillStyle = grad;
      heatCtx.fillRect(0, 0, w, h);
    } else if (terrainKey === 'urban') {
      // High activation over building edges (bright red and yellow)
      heatCtx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      heatCtx.fillRect(0, 0, w, h);

      const grad = heatCtx.createRadialGradient(w / 2, h / 2, 15, w / 2, h / 2, 80);
      grad.addColorStop(0, 'rgba(239, 68, 68, 0.95)');
      grad.addColorStop(0.5, 'rgba(245, 158, 11, 0.8)');
      grad.addColorStop(1, 'transparent');
      heatCtx.fillStyle = grad;
      heatCtx.fillRect(0, 0, w, h);

      // Edge highlights
      heatCtx.strokeStyle = '#f87171';
      heatCtx.lineWidth = 3;
      heatCtx.strokeRect(w * 0.25, h * 0.2, w * 0.5, h * 0.6);
    } else if (terrainKey === 'water') {
      // High activation across entire water surface
      heatCtx.fillStyle = 'rgba(239, 68, 68, 0.75)';
      heatCtx.fillRect(0, 0, w, h);
      heatCtx.fillStyle = 'rgba(245, 158, 11, 0.5)';
      heatCtx.fillRect(w * 0.2, h * 0.2, w * 0.6, h * 0.6);
    } else if (terrainKey === 'boulders') {
      // Localized hotspot in center
      heatCtx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      heatCtx.fillRect(0, 0, w, h);

      const grad = heatCtx.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, 60);
      grad.addColorStop(0, 'rgba(239, 68, 68, 0.9)');
      grad.addColorStop(0.6, 'rgba(245, 158, 11, 0.7)');
      grad.addColorStop(1, 'transparent');
      heatCtx.fillStyle = grad;
      heatCtx.fillRect(0, 0, w, h);
    }

    // 3. Update Text Info
    const titleEl = document.getElementById('visualizer-terrain-title');
    const classEl = document.getElementById('visualizer-classification');
    const confEl = document.getElementById('visualizer-confidence');
    const riskEl = document.getElementById('visualizer-risk');
    const decEl = document.getElementById('visualizer-decision');
    const expEl = document.getElementById('visualizer-explanation');

    if (titleEl) titleEl.textContent = data.name;
    if (classEl) {
      classEl.textContent = data.classification;
      classEl.style.color = data.statusColor;
    }
    if (confEl) confEl.textContent = data.confidence;
    if (riskEl) riskEl.textContent = data.riskScore;
    if (decEl) {
      decEl.textContent = data.decision;
      decEl.style.color = data.statusColor;
    }
    if (expEl) expEl.textContent = data.explanation;
  }

  // =========================================================================
  // 3. INTERACTIVE VIDEO REPLAY SIMULATOR & FPS SELECTOR
  // =========================================================================

  let videoElement = null;
  let videoCanvas = null;
  let videoCtx = null;
  let isPlaying = false;
  let playbackFps = 10; // Default CanSat high-rate simulation
  let lastFrameTime = 0;
  let animFrameId = null;

  function initVideoReplay() {
    videoCanvas = document.getElementById('replay-hud-canvas');
    if (!videoCanvas) return;
    videoCtx = videoCanvas.getContext('2d');

    const fileInput = document.getElementById('replay-file-input');
    const playBtn = document.getElementById('btn-replay-play');
    const scrubSlider = document.getElementById('replay-scrubber');
    const loadSampleBtn = document.getElementById('btn-load-sample-video');

    // FPS Selector Buttons
    document.querySelectorAll('[data-fps-mode]').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-fps-mode]').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const fps = parseInt(btn.getAttribute('data-fps-mode'), 10);
        playbackFps = fps;
        const fpsBadge = document.getElementById('replay-fps-indicator');
        if (fpsBadge) fpsBadge.textContent = fps + ' FPS';
      });
    });

    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          loadVideoSource(URL.createObjectURL(file));
        }
      });
    }

    if (loadSampleBtn) {
      loadSampleBtn.addEventListener('click', () => {
        // Generate procedural descent flight if no video file
        startProceduralFlightReplay();
      });
    }

    if (playBtn) {
      playBtn.addEventListener('click', () => {
        isPlaying = !isPlaying;
        playBtn.textContent = isPlaying ? 'PAUSE' : 'PLAY';
        if (isPlaying) {
          if (videoElement && !videoElement.paused) videoElement.play();
          playLoop(performance.now());
        } else {
          if (videoElement) videoElement.pause();
          if (animFrameId) cancelAnimationFrame(animFrameId);
        }
      });
    }

    if (scrubSlider) {
      scrubSlider.addEventListener('input', () => {
        if (videoElement && videoElement.duration) {
          videoElement.currentTime = (scrubSlider.value / 100) * videoElement.duration;
        }
      });
    }

    const presetSelect = document.getElementById('replay-preset-select');
    if (presetSelect) {
      presetSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) {
          loadVideoSource(val);
        }
      });
    }

    // Initial render placeholder
    renderReplayHudFrame();
  }

  function loadVideoSource(url) {
    if (!videoElement) {
      videoElement = document.createElement('video');
      videoElement.crossOrigin = 'anonymous';
      videoElement.loop = true;
      videoElement.muted = true;
    }
    videoElement.src = url;
    videoElement.play().then(() => {
      isPlaying = true;
      const playBtn = document.getElementById('btn-replay-play');
      if (playBtn) playBtn.textContent = 'PAUSE';
      playLoop(performance.now());
    }).catch((err) => {
      console.warn('Video autoplay prevented or source error:', err);
    });
  }

  let proceduralTime = 0;
  function startProceduralFlightReplay() {
    if (videoElement) {
      videoElement.pause();
    }
    isPlaying = true;
    const playBtn = document.getElementById('btn-replay-play');
    if (playBtn) playBtn.textContent = 'PAUSE';
    playLoop(performance.now());
  }

  function playLoop(timestamp) {
    if (!isPlaying) return;

    const frameInterval = 1000 / playbackFps;
    const elapsed = timestamp - lastFrameTime;

    if (elapsed >= frameInterval) {
      lastFrameTime = timestamp - (elapsed % frameInterval);

      if (videoElement && !videoElement.paused && videoElement.readyState >= 2) {
        // Extract real video frame
        videoCtx.drawImage(videoElement, 0, 0, videoCanvas.width, videoCanvas.height);
        analyzeAndDrawHud(videoCtx, videoCanvas.width, videoCanvas.height);
      } else if (!videoElement || videoElement.paused) {
        // Procedural descent simulation
        proceduralTime += 0.05;
        renderProceduralFrame(proceduralTime);
      }
    }

    animFrameId = requestAnimationFrame(playLoop);
  }

  function renderProceduralFrame(t) {
    const w = videoCanvas.width;
    const h = videoCanvas.height;

    // Draw scrolling aerial landscape
    videoCtx.fillStyle = '#166534';
    videoCtx.fillRect(0, 0, w, h);

    // Simulated building moving with descent drift
    const bX = (w * 0.35) + Math.sin(t * 0.8) * 40;
    const bY = (h * 0.3) + Math.cos(t * 0.5) * 20;

    videoCtx.fillStyle = '#334155';
    videoCtx.fillRect(bX, bY, 110, 80);
    videoCtx.fillStyle = '#475569';
    videoCtx.fillRect(bX + 10, bY + 10, 90, 60);

    analyzeAndDrawHud(videoCtx, w, h);
  }

  let offscreenReplayCanvas = null;
  let offscreenReplayCtx = null;

  function analyzeAndDrawHud(ctx, w, h) {
    if (!offscreenReplayCanvas) {
      offscreenReplayCanvas = document.createElement('canvas');
      offscreenReplayCanvas.width = 32;
      offscreenReplayCanvas.height = 24;
      offscreenReplayCtx = offscreenReplayCanvas.getContext('2d', { willReadFrequently: true });
    }

    // Downsample the rendered frame for rapid sector evaluation
    offscreenReplayCtx.drawImage(videoCanvas, 0, 0, 32, 24);
    const imgData = offscreenReplayCtx.getImageData(0, 0, 32, 24);
    const pixels = imgData.data;

    const cellW = w / 3;
    const cellH = h / 3;
    const cw = Math.floor(32 / 3);
    const ch = Math.floor(24 / 3);

    const sectorGrid = [];
    let bestCell = [1, 1];
    let maxScore = -999;
    let centerLabel = 'CRITICAL_HAZARD';
    let centerVari = 0;

    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        let sumR = 0, sumG = 0, sumB = 0, count = 0;
        for (let y = r * ch; y < (r + 1) * ch; y++) {
          for (let x = c * cw; x < (c + 1) * cw; x++) {
            const idx = (y * 32 + x) * 4;
            sumR += pixels[idx];
            sumG += pixels[idx + 1];
            sumB += pixels[idx + 2];
            count++;
          }
        }
        const avgR = sumR / count;
        const avgG = sumG / count;
        const avgB = sumB / count;

        const maxC = Math.max(avgR, avgG, avgB);
        const minC = Math.min(avgR, avgG, avgB);
        const saturation = maxC > 0 ? (maxC - minC) / maxC : 0;
        const sVari = (avgG - avgR) / Math.max(1, (avgG + avgR - avgB));

        let sLabel = 'CRITICAL_HAZARD';
        let sScore = -0.5;
        let sColor = 'rgba(239, 68, 68, 0.20)';
        let sBorder = 'rgba(239, 68, 68, 0.55)';

        if (avgB > avgR * 1.08 && avgB > avgG * 0.95 && avgB > 80) {
          sLabel = 'WATER_HAZARD';
          sScore = -1.0;
          sColor = 'rgba(6, 182, 212, 0.22)';
          sBorder = 'rgba(6, 182, 212, 0.65)';
        } else if (saturation < 0.10 || (avgR > 185 && avgG > 185 && avgB > 175)) {
          sLabel = 'CRITICAL_HAZARD';
          sScore = -0.8;
          sColor = 'rgba(239, 68, 68, 0.20)';
          sBorder = 'rgba(239, 68, 68, 0.55)';
        } else if (sVari > 0.06 && avgG > avgR * 1.04 && saturation > 0.08) {
          sLabel = 'SAFE_LZ';
          sScore = 1.0 + sVari;
          sColor = 'rgba(16, 185, 129, 0.24)';
          sBorder = 'rgba(16, 185, 129, 0.8)';
        } else if (sVari >= -0.02 && avgG > avgR && avgG > avgB) {
          sLabel = 'OBSTACLE_CANOPY';
          sScore = 0.2 + sVari;
          sColor = 'rgba(245, 158, 11, 0.20)';
          sBorder = 'rgba(245, 158, 11, 0.65)';
        }

        if (r === 1 && c === 1) {
          centerLabel = sLabel;
          centerVari = sVari;
        }

        if (sScore > maxScore) {
          maxScore = sScore;
          bestCell = [r, c];
        }

        sectorGrid.push({ r, c, label: sLabel, color: sColor, border: sBorder });
      }
    }

    // 1. Draw Sector Grid Fills & Borders
    for (const sec of sectorGrid) {
      const x = sec.c * cellW;
      const y = sec.r * cellH;

      ctx.fillStyle = sec.color;
      ctx.fillRect(x, y, cellW, cellH);

      ctx.strokeStyle = sec.border;
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 1, y + 1, cellW - 2, cellH - 2);

      // Label Sector Tag
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px "JetBrains Mono", monospace';
      ctx.fillText(sec.label.replace('_', ' '), x + 6, y + 16);
    }

    // 2. Draw 3x3 Grid Divider Lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
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

    // 3. Highlight Optimal LZ Sector
    const bx = bestCell[1] * cellW;
    const by = bestCell[0] * cellH;
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 2;
    ctx.strokeRect(bx + 2, by + 2, cellW - 4, cellH - 4);

    ctx.fillStyle = '#10B981';
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    ctx.fillText('OPTIMAL LZ', bx + 6, by + 28);

    // 4. Center Crosshairs Reticle
    const cx = w / 2;
    const cy = h / 2;
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.8)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx - 10, cy);
    ctx.lineTo(cx + 10, cy);
    ctx.moveTo(cx, cy - 10);
    ctx.lineTo(cx, cy + 10);
    ctx.stroke();

    // 5. Evasion Vector Calculation
    const needsEvade = (centerLabel !== 'SAFE_LZ') && (bestCell[0] !== 1 || bestCell[1] !== 1);
    let evadeAngle = 0;
    let evadeText = 'ON TARGET (SAFE LZ)';

    if (needsEvade) {
      const tx = bx + cellW / 2;
      const ty = by + cellH / 2;
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(tx, ty);
      ctx.stroke();

      // Arrowhead
      const angle = Math.atan2(ty - cy, tx - cx);
      ctx.fillStyle = '#10B981';
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(tx - 10 * Math.cos(angle - Math.PI / 6), ty - 10 * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(tx - 10 * Math.cos(angle + Math.PI / 6), ty - 10 * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();

      let deg = Math.round((angle * 180 / Math.PI + 90 + 360) % 360);
      evadeAngle = deg;
      evadeText = `EVADE ${String(deg).padStart(3, '0')} deg`;
    }

    // 6. Top HUD Status Bar
    ctx.fillStyle = 'rgba(7, 10, 19, 0.85)';
    ctx.fillRect(0, 0, w, 26);

    ctx.fillStyle = centerLabel === 'SAFE_LZ' ? '#34d399' : (centerLabel === 'OBSTACLE_CANOPY' ? '#fbbf24' : '#f87171');
    ctx.font = '10px "JetBrains Mono", monospace';
    const variStr = `VARI ${centerVari >= 0 ? '+' : ''}${centerVari.toFixed(2)}`;
    ctx.fillText(`SLAI: ${centerLabel} | ${variStr} | NADIR: [1,1] | ${evadeText} | RATE: ${playbackFps} FPS`, 10, 17);

    // 7. Update External UI Badges
    const slaiBadge = document.getElementById('replay-slai-badge');
    const evadeBadge = document.getElementById('replay-evade-badge');
    if (slaiBadge) {
      slaiBadge.textContent = centerLabel.replace('_', ' ');
      slaiBadge.style.color = centerLabel === 'SAFE_LZ' ? 'var(--accent-green)' : (centerLabel === 'OBSTACLE_CANOPY' ? 'var(--accent-yellow)' : 'var(--accent-red)');
    }
    if (evadeBadge) {
      evadeBadge.textContent = evadeText;
      evadeBadge.style.color = needsEvade ? '#ffffff' : 'var(--accent-green)';
    }
  }

  function renderReplayHudFrame() {
    if (!videoCtx || !videoCanvas) return;
    renderProceduralFrame(1.5);
  }

  window.addEventListener('DOMContentLoaded', () => {
    initModelInspector();
    initInferenceVisualizer();
    initVideoReplay();
  });
})();
