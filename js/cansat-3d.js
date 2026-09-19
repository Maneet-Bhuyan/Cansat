/**
 * Cognitive CanSat - 3D Interactive CanSat Model Viewer
 * High-precision physical digital twin:
 *   - Hexstar Universe CanSat Kit: Black 3D-printed PLA cylinder with realistic layer micro-grooves
 *   - Countersunk M3 machine screws on 3D-printed top & bottom end-caps
 *   - Top deck: Brass SMA bulkhead connector with vertical whip antenna & metal power toggle switch
 *   - Bottom deck: Dedicated 9V battery compartment (HW 9V) with heavy-duty snap connector
 *   - Tier 1: Circular FR4 PCB hosting Arduino Nano ("Brain"), LoRa SX1278 (Ra-02), MPU6050,
 *     BMP180 barometer, DHT11 (blue slotted grid), NEO-6M GPS ceramic patch, and brass standoffs
 *   - Tier 2: AI-Thinker ESP32-CAM development board with OV2640/OV3660 camera turret on orange
 *     flexible ribbon cable, metal MicroSD socket, and flash LED
 *   - True spherical radial zoom (+/- buttons, mouse wheel, pinch-to-zoom)
 *   - Interactive component inspection with smooth camera framing and cutaway/solid shell toggle
 *   - Exploded view animation
 *   - Zero emojis.
 */

(function () {
  'use strict';

  const COMPONENT_DATA = {
    'casing_pla': {
      name: '3D-Printed PLA Airframe & End-Caps',
      tier: 'Structural Airframe',
      mass: '68 g',
      specs: '66 mm dia x 115 mm height, matte black PLA, countersunk M3 screws, side observation aperture',
      desc: 'Cylindrical 3D-printed PLA body built conforming to international CanSat regulations. Features top and bottom end-plates secured with machine screws, internal standoff mounting bosses, a dedicated bottom 9V battery bay, and a side sensor aperture.'
    },
    'arduino_nano': {
      name: 'Arduino Nano Microcontroller (Brain)',
      tier: 'Tier 1 Core Flight Computer',
      mass: '7 g',
      specs: 'ATmega328P @ 16MHz, 32KB Flash, 2KB SRAM, Mini-USB port, 5V/3.3V power rails, I2C & UART buses',
      desc: 'The central processing brain that executes the telemetry packetizer, samples environmental sensors (BMP180, DHT11, MPU6050, GPS NEO-6M), and commands the LoRa radio downlink.'
    },
    'esp32_cam': {
      name: 'AI-Thinker ESP32-CAM & Development Board',
      tier: 'Tier 2 Optical Edge AI & TinyML',
      mass: '22 g',
      specs: 'ESP32-S dual-core Xtensa LX6 @ 240MHz, 520KB SRAM + 8MB PSRAM, MicroSD socket, onboard bright LED flash, dual header pins',
      desc: 'Dedicated edge computing vision tier. Powers real-time visual inspection, image capture, and executes quantized TinyLandingNet inference locally without relying on ground radio bandwidth.'
    },
    'nadir_camera': {
      name: 'OV2640 / OV3660 Camera Sensor Module',
      tier: 'Tier 2 Optical Subsystem',
      mass: '5 g',
      specs: 'DVP parallel interface, flexible orange FPC ribbon cable, adjustable focal lens turret, downward/nadir-facing optical alignment',
      desc: 'High-resolution optical camera module connected via flexible ribbon cable to the ESP32-CAM. Captures aerial terrain imagery during parachute descent.'
    },
    'lora_sx1278': {
      name: 'LoRa SX1278 (Ra-02) 433MHz Transceiver',
      tier: 'Long-Range Telemetry Downlink',
      mass: '9 g',
      specs: 'Semtech SX1278, metal RF shield can, +20 dBm (100mW) output, SPI interface, 433MHz ISM band, 9600 baud, 300m+ range',
      desc: 'The radio voice of the CanSat. Transmits the real-time 13-field telemetry stream (temperature, pressure, altitude, gyro, accel, GPS, battery) to the ground station.'
    },
    'sensor_dht11': {
      name: 'DHT11 Digital Humidity & Temperature Sensor',
      tier: 'Environmental Sounding Array',
      mass: '4 g',
      specs: '20-90% RH (5% accuracy), 0-50 deg C (2 deg C accuracy), single-wire digital interface, signature blue slotted grid housing',
      desc: 'Measures atmospheric relative humidity and ambient temperature for atmospheric boundary layer profiling, sounding dew point estimation, and air density calculation.'
    },
    'sensor_bmp180': {
      name: 'BMP180 Digital Barometric Pressure Sensor',
      tier: 'Environmental Sounding Array',
      mass: '2 g',
      specs: '300-1100 hPa range (+9000m to -500m), 0.02 hPa (17 cm) resolution, I2C interface at 0x77, metal can pressure port',
      desc: 'Measures high-precision barometric pressure to derive hypsometric altitude AGL, compute vertical ascent/descent velocity (vSpd), and calculate atmospheric lapse rate.'
    },
    'sensor_mpu6050': {
      name: 'MPU6050 6-Axis Motion Tracking IMU',
      tier: 'Kinematics & Inertial Navigation',
      mass: '3 g',
      specs: '3-axis MEMS accelerometer (+/-16g) + 3-axis MEMS gyroscope (+/-2000 deg/s), integrated 16-bit ADCs, I2C at 0x68',
      desc: 'Captures body-frame pitch, roll, and yaw dynamics, tumble rates, and impact/deployment G-shocks during balloon ascent, apogee burst, and parachute landing.'
    },
    'sensor_gps': {
      name: 'u-blox NEO-6M GPS & Ceramic Patch Antenna',
      tier: 'Geodetic Navigation & Recovery',
      mass: '18 g',
      specs: '50-channel receiver, 25x25mm ceramic patch antenna, NMEA 0183 output, UART @ 9600 baud, WGS84 coordinates',
      desc: 'Mounted in the dedicated side bracket slot of the cylindrical airframe. Tracks outdoor geodetic position (latitude, longitude, ground speed) to feed the live tactical GIS ground track and enable recovery team navigation in Google Maps.'
    },
    'power_battery': {
      name: '9V Alkaline Battery & Heavy-Duty Snap Clip',
      tier: 'Power Subsystem',
      mass: '46 g',
      specs: '9V nominal (HW 9V block), heavy-duty snap terminal clip, isolated bottom compartment, regulated to 5V and 3.3V rails',
      desc: 'Installed in the dedicated bottom section of the CanSat. Powers the Arduino Nano, sensor stack, and ESP32-CAM throughout the sounding flight duration.'
    },
    'top_assembly': {
      name: 'Top Cap with SMA Whip Antenna & Power Switch',
      tier: 'Antenna & Power Management',
      mass: '16 g',
      specs: 'Brass SMA bulkhead connector, 433MHz rubber duck whip antenna, metal bat-lever toggle switch, 4x M3 machine screws',
      desc: 'Top 3D-printed lid housing the central SMA antenna feedthrough for maximum RF omnidirectional radiation and the physical mission start toggle switch.'
    }
  };

  let scene, camera, renderer, container;
  let cansatGroup;
  let interactiveMeshes = [];
  let raycaster, mouse;
  let hoveredMesh = null;
  let selectedComponentId = null;
  let isExploded = false;
  let autoRotate = true;
  let isCutawayView = true;

  let targetRotationX = 0.2;
  let targetRotationY = -0.3;

  // Camera Framing & Orbit Targets
  const defaultLookAt = new THREE.Vector3(0, 0, 0);
  const currentLookAt = new THREE.Vector3(0, 0, 0);
  const targetLookAt = new THREE.Vector3(0, 0, 0);

  const defaultCameraPos = new THREE.Vector3(3.8, 2.8, 5.0);
  const targetCameraPos = new THREE.Vector3(3.8, 2.8, 5.0);

  let shellMat = null;
  let highlightedMeshes = [];

  const assemblies = {
    shell: { mesh: null, origY: 0, targetY: 0 },
    topCap: { mesh: null, origY: 1.08, targetY: 1.08 },
    tier1: { mesh: null, origY: 0.45, targetY: 0.45 },
    battery: { mesh: null, origY: -0.05, targetY: -0.05 },
    tier2: { mesh: null, origY: -0.58, targetY: -0.58 },
    botCap: { mesh: null, origY: -1.08, targetY: -1.08 }
  };

  function init3DViewer() {
    container = document.getElementById('cansat-3d-canvas-container');
    if (!container) return;

    let width = container.clientWidth || 580;
    let height = container.clientHeight || 520;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.copy(defaultCameraPos);
    camera.lookAt(defaultLookAt);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // Studio Rim Lighting for Resend Jet-Black Aesthetic
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.4);
    sunLight.position.set(6, 9, 6);
    scene.add(sunLight);

    const rimLight = new THREE.DirectionalLight(0x00e5ff, 0.6);
    rimLight.position.set(-6, -3, -4);
    scene.add(rimLight);

    const fillLight = new THREE.DirectionalLight(0xa855f7, 0.4);
    fillLight.position.set(4, -6, 4);
    scene.add(fillLight);

    const grid = new THREE.GridHelper(8, 8, 0x262626, 0x141414);
    grid.position.y = -1.5;
    scene.add(grid);

    cansatGroup = new THREE.Group();
    cansatGroup.rotation.x = targetRotationX;
    cansatGroup.rotation.y = targetRotationY;
    scene.add(cansatGroup);

    buildCanSatModel();

    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2(-999, -999);

    container.addEventListener('mousemove', onMouseMove);
    container.addEventListener('click', onClick);
    window.addEventListener('resize', onWindowResize);

    // Smooth Orbit Drag
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };

    container.addEventListener('mousedown', (e) => {
      isDragging = true;
      autoRotate = false;
      prevMouse = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    container.addEventListener('mousemove', (e) => {
      if (isDragging) {
        const dx = e.clientX - prevMouse.x;
        const dy = e.clientY - prevMouse.y;
        cansatGroup.rotation.y += dx * 0.008;
        cansatGroup.rotation.x += dy * 0.008;
        targetRotationY = cansatGroup.rotation.y;
        targetRotationX = cansatGroup.rotation.x;
        prevMouse = { x: e.clientX, y: e.clientY };
      }
    });

    // Spherical Line-of-Sight Zoom
    container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1.08 : 0.92;
      zoomCamera(factor);
    }, { passive: false });

    // Double-click to reset view
    container.addEventListener('dblclick', () => {
      resetCameraView();
    });

    setupControls();
    animate();
  }

  // True Spherical Line-of-Sight Zoom
  function zoomCamera(factor) {
    if (!camera) return;
    const offset = camera.position.clone().sub(targetLookAt);
    const currentDist = offset.length();
    const newDist = Math.max(1.8, Math.min(12.0, currentDist * factor));
    offset.setLength(newDist);
    targetCameraPos.copy(targetLookAt).add(offset);
  }

  function resetCameraView() {
    targetLookAt.copy(defaultLookAt);
    targetCameraPos.copy(defaultCameraPos);
    targetRotationX = 0.2;
    targetRotationY = -0.3;
    autoRotate = true;
    selectedComponentId = null;
    clearComponentHighlights();
    resetHoverEffect();
    setCutawayMode(true);
    updateInspectionCard('casing_pla');
  }

  function setCutawayMode(cutaway) {
    isCutawayView = cutaway;
    if (shellMat) {
      shellMat.opacity = cutaway ? 0.35 : 0.92;
      shellMat.transparent = cutaway;
      shellMat.roughness = cutaway ? 0.50 : 0.82;
      shellMat.needsUpdate = true;
    }
    const btn = document.getElementById('btn-shell-toggle');
    if (btn) {
      btn.textContent = cutaway ? 'Solid Shell' : 'Cutaway View';
      btn.classList.toggle('active', !cutaway);
    }
  }

  function buildCanSatModel() {
    // -------------------------------------------------------------------------
    // 1. 3D-PRINTED PLA CYLINDRICAL AIRFRAME BODY (66mm dia x 115mm height)
    // -------------------------------------------------------------------------
    const shellGroup = new THREE.Group();

    // Cylindrical Body (Height 2.1, Radius 0.70)
    const shellGeo = new THREE.CylinderGeometry(0.70, 0.70, 2.1, 36, 1, false);
    shellMat = new THREE.MeshStandardMaterial({
      color: 0x18181b, // Matte Black PLA
      roughness: 0.82,
      metalness: 0.12,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide
    });
    const shellMesh = new THREE.Mesh(shellGeo, shellMat);
    shellMesh.userData = { id: 'casing_pla' };
    shellGroup.add(shellMesh);
    interactiveMeshes.push(shellMesh);

    // 3D-Print Micro-Layer Rings
    const layerRingGeo = new THREE.TorusGeometry(0.702, 0.008, 8, 36);
    const layerRingMat = new THREE.MeshStandardMaterial({ color: 0x27272a, roughness: 0.95 });
    for (let y = -0.95; y <= 0.95; y += 0.22) {
      const ring = new THREE.Mesh(layerRingGeo, layerRingMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = y;
      shellGroup.add(ring);
    }

    // Side-Mounted NEO-6M GPS Module Assembly (Vertical slot on cylinder wall)
    // 1. Blue FR4 GPS PCB Board
    const gpsBoardGeo = new THREE.BoxGeometry(0.05, 0.68, 0.44);
    const gpsBoardMat = new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.45, metalness: 0.2 });
    const gpsBoard = new THREE.Mesh(gpsBoardGeo, gpsBoardMat);
    gpsBoard.position.set(0.69, 0.20, 0);
    gpsBoard.userData = { id: 'sensor_gps' };
    shellGroup.add(gpsBoard);
    interactiveMeshes.push(gpsBoard);

    // 2. Tan Ceramic Patch Antenna (Mounted on outer face of PCB)
    const gpsPatchGeo = new THREE.BoxGeometry(0.06, 0.34, 0.34);
    const gpsPatchMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.65, metalness: 0.1 });
    const gpsPatch = new THREE.Mesh(gpsPatchGeo, gpsPatchMat);
    gpsPatch.position.set(0.74, 0.20, 0);
    gpsPatch.userData = { id: 'sensor_gps' };
    shellGroup.add(gpsPatch);
    interactiveMeshes.push(gpsPatch);

    // 3. Center Metallic Feed Pin on Ceramic Patch
    const gpsPinGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.02, 8);
    const gpsPinMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.95, roughness: 0.2 });
    const gpsPin = new THREE.Mesh(gpsPinGeo, gpsPinMat);
    gpsPin.rotation.z = Math.PI / 2;
    gpsPin.position.set(0.77, 0.20, 0);
    gpsPin.userData = { id: 'sensor_gps' };
    shellGroup.add(gpsPin);
    interactiveMeshes.push(gpsPin);

    // 4. GPS Fix Status / PPS Indicator LED
    const gpsLedGeo = new THREE.BoxGeometry(0.02, 0.03, 0.03);
    const gpsLedMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, emissive: 0x16a34a, emissiveIntensity: 0.8 });
    const gpsLed = new THREE.Mesh(gpsLedGeo, gpsLedMat);
    gpsLed.position.set(0.72, 0.44, 0.12);
    gpsLed.userData = { id: 'sensor_gps' };
    shellGroup.add(gpsLed);
    interactiveMeshes.push(gpsLed);

    cansatGroup.add(shellGroup);
    assemblies.shell.mesh = shellGroup;
    assemblies.shell.origY = 0;

    // -------------------------------------------------------------------------
    // 2. 3D-PRINTED TOP CAP WITH SMA CONNECTOR, WHIP ANTENNA & TOGGLE SWITCH
    // -------------------------------------------------------------------------
    const topCapGroup = new THREE.Group();
    topCapGroup.position.y = 1.08;

    // Bevelled Top End-Plate (Dedicated Material)
    const topCapMat = new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.80, metalness: 0.15 });
    const capGeo = new THREE.CylinderGeometry(0.73, 0.73, 0.09, 36);
    const topCap = new THREE.Mesh(capGeo, topCapMat);
    topCap.userData = { id: 'top_assembly' };
    topCapGroup.add(topCap);
    interactiveMeshes.push(topCap);

    // M3 Screws on Caps (Passive hardware)
    const screwMat = new THREE.MeshStandardMaterial({ color: 0xa1a1aa, metalness: 0.95, roughness: 0.2 });
    const screwGeo = new THREE.CylinderGeometry(0.026, 0.026, 0.02, 12);
    for (let i = 0; i < 4; i++) {
      const ang = (i * Math.PI / 2) + Math.PI / 4;
      const sTop = new THREE.Mesh(screwGeo, screwMat);
      sTop.position.set(0.60 * Math.cos(ang), 0.05, 0.60 * Math.sin(ang));
      topCapGroup.add(sTop);
    }

    // Brass SMA Bulkhead Hex Nut (Dedicated Material)
    const smaGeom = new THREE.CylinderGeometry(0.065, 0.065, 0.07, 6);
    const smaMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.92, roughness: 0.25 });
    const smaNut = new THREE.Mesh(smaGeom, smaMat);
    smaNut.position.set(0, 0.08, 0);
    smaNut.userData = { id: 'top_assembly' };
    topCapGroup.add(smaNut);
    interactiveMeshes.push(smaNut);

    // 433MHz Vertical Rubber Duck Whip Antenna (Dedicated Material)
    const whipGeom = new THREE.CylinderGeometry(0.022, 0.038, 1.35, 16);
    const whipMat = new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.8, metalness: 0.15 });
    const whip = new THREE.Mesh(whipGeom, whipMat);
    whip.position.set(0, 0.76, 0);
    whip.userData = { id: 'top_assembly' };
    topCapGroup.add(whip);
    interactiveMeshes.push(whip);

    // Metal Power Toggle Switch (Dedicated Materials)
    const switchBaseGeom = new THREE.CylinderGeometry(0.05, 0.05, 0.05, 12);
    const swBaseMat = new THREE.MeshStandardMaterial({ color: 0x71717a, metalness: 0.9 });
    const swBase = new THREE.Mesh(switchBaseGeom, swBaseMat);
    swBase.position.set(0.35, 0.07, 0.18);
    swBase.userData = { id: 'top_assembly' };
    topCapGroup.add(swBase);
    interactiveMeshes.push(swBase);

    const leverGeom = new THREE.CylinderGeometry(0.012, 0.02, 0.15, 10);
    const swLeverMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, metalness: 0.95 });
    const swLever = new THREE.Mesh(leverGeom, swLeverMat);
    swLever.position.set(0.35, 0.15, 0.18);
    swLever.rotation.z = -0.3;
    swLever.userData = { id: 'top_assembly' };
    topCapGroup.add(swLever);
    interactiveMeshes.push(swLever);

    cansatGroup.add(topCapGroup);
    assemblies.topCap.mesh = topCapGroup;
    assemblies.topCap.origY = 1.08;

    // -------------------------------------------------------------------------
    // 3. TIER 1: ARDUINO NANO & SENSOR STACK (Upper Deck, Y = 0.45)
    // -------------------------------------------------------------------------
    const tier1Group = new THREE.Group();
    tier1Group.position.y = 0.45;

    // Circular FR4 Green PCB Base (Passive structural disc)
    const pcb1Mat = new THREE.MeshStandardMaterial({ color: 0x064e3b, roughness: 0.5, metalness: 0.3 });
    const pcb1Geo = new THREE.CylinderGeometry(0.64, 0.64, 0.03, 32);
    const pcb1 = new THREE.Mesh(pcb1Geo, pcb1Mat);
    tier1Group.add(pcb1);

    // 4 Hexagonal Brass Standoffs connecting Tier 1 down to Middle Battery Deck
    const standoffMat = new THREE.MeshStandardMaterial({ color: 0xeab308, metalness: 0.9, roughness: 0.25 });
    const standoffGeom = new THREE.CylinderGeometry(0.016, 0.016, 0.42, 6);
    for (let i = 0; i < 4; i++) {
      const angle = (i * Math.PI / 2) + Math.PI / 4;
      const standoff = new THREE.Mesh(standoffGeom, standoffMat);
      standoff.position.set(0.52 * Math.cos(angle), -0.21, 0.52 * Math.sin(angle));
      tier1Group.add(standoff);
    }

    // Arduino Nano (Blue PCB with ATmega328P - Dedicated Material)
    const nanoGeom = new THREE.BoxGeometry(0.28, 0.03, 0.64);
    const nanoMat = new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.5 });
    const nano = new THREE.Mesh(nanoGeom, nanoMat);
    nano.position.set(-0.20, 0.03, 0);
    nano.userData = { id: 'arduino_nano' };
    tier1Group.add(nano);
    interactiveMeshes.push(nano);

    // Mini-USB Jack on Nano (Dedicated Material)
    const usbGeom = new THREE.BoxGeometry(0.12, 0.05, 0.12);
    const usbMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, metalness: 0.95, roughness: 0.2 });
    const usb = new THREE.Mesh(usbGeom, usbMat);
    usb.position.set(-0.20, 0.05, 0.28);
    usb.userData = { id: 'arduino_nano' };
    tier1Group.add(usb);
    interactiveMeshes.push(usb);

    // LoRa SX1278 (Ra-02) with Metal Shield Can (Dedicated Material)
    const loraGeom = new THREE.BoxGeometry(0.26, 0.04, 0.28);
    const loraMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.92, roughness: 0.2 });
    const lora = new THREE.Mesh(loraGeom, loraMat);
    lora.position.set(0.22, 0.03, -0.20);
    lora.userData = { id: 'lora_sx1278' };
    tier1Group.add(lora);
    interactiveMeshes.push(lora);

    // DHT11 Sensor (Signature Blue Slotted Box - Dedicated Material)
    const dhtGeom = new THREE.BoxGeometry(0.20, 0.22, 0.13);
    const dhtMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.5 });
    const dht = new THREE.Mesh(dhtGeom, dhtMat);
    dht.position.set(0.24, 0.13, 0.12);
    dht.userData = { id: 'sensor_dht11' };
    tier1Group.add(dht);
    interactiveMeshes.push(dht);

    // BMP180 Barometer (Dedicated Material)
    const bmpGeom = new THREE.CylinderGeometry(0.035, 0.035, 0.03, 12);
    const bmpMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.95 });
    const bmp = new THREE.Mesh(bmpGeom, bmpMat);
    bmp.position.set(0.04, 0.03, 0.24);
    bmp.userData = { id: 'sensor_bmp180' };
    tier1Group.add(bmp);
    interactiveMeshes.push(bmp);

    // MPU6050 6-DOF IMU (Dedicated Material)
    const mpuGeom = new THREE.BoxGeometry(0.18, 0.025, 0.22);
    const mpuMat = new THREE.MeshStandardMaterial({ color: 0x1e40af, roughness: 0.45 });
    const mpu = new THREE.Mesh(mpuGeom, mpuMat);
    mpu.position.set(-0.02, 0.03, -0.18);
    mpu.userData = { id: 'sensor_mpu6050' };
    tier1Group.add(mpu);
    interactiveMeshes.push(mpu);


    cansatGroup.add(tier1Group);
    assemblies.tier1.mesh = tier1Group;
    assemblies.tier1.origY = 0.45;

    // -------------------------------------------------------------------------
    // 4. MIDDLE DECK: 9V BATTERY COMPARTMENT (Y = -0.05)
    // -------------------------------------------------------------------------
    const battGroup = new THREE.Group();
    battGroup.position.y = -0.05;

    // Circular FR4 Battery Bracket Shelf (Passive structural plate)
    const battShelfMat = new THREE.MeshStandardMaterial({ color: 0x064e3b, roughness: 0.5, metalness: 0.3 });
    const battShelfGeo = new THREE.CylinderGeometry(0.64, 0.64, 0.025, 32);
    const battShelf = new THREE.Mesh(battShelfGeo, battShelfMat);
    battShelf.position.y = 0.20;
    battGroup.add(battShelf);

    // 4 Hexagonal Brass Standoffs connecting Middle Deck down to Bottom Camera Deck
    const standoffBotGeom = new THREE.CylinderGeometry(0.016, 0.016, 0.48, 6);
    for (let i = 0; i < 4; i++) {
      const angle = (i * Math.PI / 2) + Math.PI / 4;
      const standoff = new THREE.Mesh(standoffBotGeom, standoffMat);
      standoff.position.set(0.52 * Math.cos(angle), -0.25, 0.52 * Math.sin(angle));
      battGroup.add(standoff);
    }

    // 9V Battery Block (HW 9V, Deep Blue - Dedicated Material)
    const battGeom = new THREE.BoxGeometry(0.36, 0.68, 0.24);
    const battMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, roughness: 0.4, metalness: 0.4 });
    const batt = new THREE.Mesh(battGeom, battMat);
    batt.userData = { id: 'power_battery' };
    battGroup.add(batt);
    interactiveMeshes.push(batt);

    // Snap Terminals
    const termMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, metalness: 0.95, roughness: 0.15 });
    const term1 = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.05, 12), termMat);
    term1.position.set(-0.09, 0.36, 0);
    battGroup.add(term1);

    const term2 = new THREE.Mesh(new THREE.CylinderGeometry(0.048, 0.048, 0.05, 6), termMat);
    term2.position.set(0.09, 0.36, 0);
    battGroup.add(term2);

    // Snap Clip Housing (Dedicated Material)
    const clipGeo = new THREE.BoxGeometry(0.34, 0.05, 0.22);
    const clipMat = new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.8 });
    const clip = new THREE.Mesh(clipGeo, clipMat);
    clip.position.set(0, 0.40, 0);
    clip.userData = { id: 'power_battery' };
    battGroup.add(clip);
    interactiveMeshes.push(clip);

    cansatGroup.add(battGroup);
    assemblies.battery.mesh = battGroup;
    assemblies.battery.origY = -0.05;

    // -------------------------------------------------------------------------
    // 5. TIER 2: ESP32-CAM AI VISION & NADIR CAMERA (Bottom Deck, Y = -0.58)
    // Mounted at bottom-most facing DOWNWARDS for terrain imaging during descent
    // -------------------------------------------------------------------------
    const tier2Group = new THREE.Group();
    tier2Group.position.y = -0.58;

    // Circular FR4 Green PCB Base (Passive structural plate)
    const pcb2Mat = new THREE.MeshStandardMaterial({ color: 0x064e3b, roughness: 0.5, metalness: 0.3 });
    const pcb2Geo = new THREE.CylinderGeometry(0.64, 0.64, 0.03, 32);
    const pcb2 = new THREE.Mesh(pcb2Geo, pcb2Mat);
    tier2Group.add(pcb2);

    // AI-Thinker ESP32-CAM Board (Black PCB mounted underneath, facing downwards - Dedicated Material)
    const espGeom = new THREE.BoxGeometry(0.42, 0.03, 0.58);
    const espMat = new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.6 });
    const esp = new THREE.Mesh(espGeom, espMat);
    esp.position.set(0, -0.03, 0);
    esp.userData = { id: 'esp32_cam' };
    tier2Group.add(esp);
    interactiveMeshes.push(esp);

    // Metal MicroSD Card Socket (Dedicated Material)
    const sdGeom = new THREE.BoxGeometry(0.28, 0.025, 0.28);
    const sdMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, metalness: 0.95, roughness: 0.2 });
    const sdSocket = new THREE.Mesh(sdGeom, sdMat);
    sdSocket.position.set(0, -0.02, -0.12);
    sdSocket.userData = { id: 'esp32_cam' };
    tier2Group.add(sdSocket);
    interactiveMeshes.push(sdSocket);

    // Flash LED (Pointing Downwards - Dedicated Material)
    const flashGeom = new THREE.BoxGeometry(0.07, 0.02, 0.07);
    const flashMat = new THREE.MeshStandardMaterial({ color: 0xfef08a, emissive: 0xfef08a, emissiveIntensity: 0.8 });
    const flashLed = new THREE.Mesh(flashGeom, flashMat);
    flashLed.position.set(-0.13, -0.05, 0.21);
    flashLed.userData = { id: 'esp32_cam' };
    tier2Group.add(flashLed);
    interactiveMeshes.push(flashLed);

    // Flexible Orange FPC Camera Ribbon Cable (Dedicated Material)
    const ribbonGeom = new THREE.BoxGeometry(0.14, 0.01, 0.26);
    const ribbonMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.4, metalness: 0.2 });
    const ribbon = new THREE.Mesh(ribbonGeom, ribbonMat);
    ribbon.position.set(0, -0.06, 0.08);
    ribbon.userData = { id: 'nadir_camera' };
    tier2Group.add(ribbon);
    interactiveMeshes.push(ribbon);

    // Camera Lens Turret (Pointing DOWNWARDS along -Y - Dedicated Material)
    const turretGeom = new THREE.CylinderGeometry(0.08, 0.08, 0.12, 16);
    const turretMat = new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.3, metalness: 0.7 });
    const turret = new THREE.Mesh(turretGeom, turretMat);
    turret.position.set(0, -0.12, 0.14);
    turret.userData = { id: 'nadir_camera' };
    tier2Group.add(turret);
    interactiveMeshes.push(turret);

    // Camera Lens Glass (Facing DOWNWARDS - Dedicated Material)
    const lensGeom = new THREE.CircleGeometry(0.06, 16);
    const lensMat = new THREE.MeshStandardMaterial({ color: 0x00e5ff, metalness: 0.9, roughness: 0.1, side: THREE.DoubleSide });
    const lens = new THREE.Mesh(lensGeom, lensMat);
    lens.rotation.x = Math.PI / 2; // Facing downwards along -Y
    lens.position.set(0, -0.18, 0.14);
    lens.userData = { id: 'nadir_camera' };
    tier2Group.add(lens);
    interactiveMeshes.push(lens);

    cansatGroup.add(tier2Group);
    assemblies.tier2.mesh = tier2Group;
    assemblies.tier2.origY = -0.58;

    // -------------------------------------------------------------------------
    // 6. 3D-PRINTED BOTTOM END-CAP WITH OPTICAL APERTURE (Y = -1.08)
    // -------------------------------------------------------------------------
    const botCapGroup = new THREE.Group();
    botCapGroup.position.y = -1.08;

    // Dedicated Material for Bottom Cap
    const botCapMat = new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.80, metalness: 0.15 });
    const botCap = new THREE.Mesh(capGeo, botCapMat);
    botCap.userData = { id: 'casing_pla' };
    botCapGroup.add(botCap);
    interactiveMeshes.push(botCap);

    // Optical Camera Aperture Ring Bezel (Center Hole for Downward Camera)
    const apertureRingGeom = new THREE.CylinderGeometry(0.14, 0.14, 0.10, 24);
    const apertureRingMat = new THREE.MeshStandardMaterial({ color: 0x27272a, roughness: 0.8, metalness: 0.3 });
    const apertureRing = new THREE.Mesh(apertureRingGeom, apertureRingMat);
    apertureRing.position.set(0, 0, 0.14);
    apertureRing.userData = { id: 'casing_pla' };
    botCapGroup.add(apertureRing);
    interactiveMeshes.push(apertureRing);

    // Dark Aperture Viewport Center
    const apertureGlassGeom = new THREE.CircleGeometry(0.11, 24);
    const apertureGlassMat = new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.1, metalness: 0.9, side: THREE.DoubleSide });
    const apertureGlass = new THREE.Mesh(apertureGlassGeom, apertureGlassMat);
    apertureGlass.rotation.x = Math.PI / 2;
    apertureGlass.position.set(0, -0.052, 0.14);
    apertureGlass.userData = { id: 'casing_pla' };
    botCapGroup.add(apertureGlass);
    interactiveMeshes.push(apertureGlass);

    for (let i = 0; i < 4; i++) {
      const ang = (i * Math.PI / 2) + Math.PI / 4;
      const sBot = new THREE.Mesh(screwGeo, screwMat);
      sBot.position.set(0.60 * Math.cos(ang), -0.05, 0.60 * Math.sin(ang));
      botCapGroup.add(sBot);
    }

    cansatGroup.add(botCapGroup);
    assemblies.botCap.mesh = botCapGroup;
    assemblies.botCap.origY = -1.08;
  }

  function onMouseMove(event) {
    const rect = container.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    checkRaycast();
  }

  function onClick() {
    checkRaycast(true);
  }

  function checkRaycast(isClick = false) {
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(interactiveMeshes, true);

    if (intersects.length > 0) {
      let hit = null;

      if (isCutawayView) {
        // In cutaway view, prefer internal components over the outer casing/shell
        const internalHit = intersects.find(i => i.object.userData?.id && i.object.userData.id !== 'casing_pla');
        if (internalHit) {
          hit = internalHit.object;
        }
      }

      if (!hit) {
        hit = intersects[0].object;
      }

      const componentId = hit.userData?.id;

      if (componentId && COMPONENT_DATA[componentId]) {
        updateInspectionCard(componentId);

        if (!isClick) {
          setHoverHighlight(hit);
        }

        if (isClick) {
          focusComponent(componentId);
          highlightComponentMeshes(componentId);
        }
        return;
      }
    }

    if (!isClick) {
      resetHoverEffect();
    }
  }

  function setHoverHighlight(mesh) {
    if (hoveredMesh === mesh) return;
    resetHoverEffect();
    hoveredMesh = mesh;
    if (hoveredMesh && !highlightedMeshes.includes(hoveredMesh) && hoveredMesh.material) {
      const mats = Array.isArray(hoveredMesh.material) ? hoveredMesh.material : [hoveredMesh.material];
      mats.forEach(mat => {
        if ('emissive' in mat) {
          if (hoveredMesh.userData.origEmissive === undefined) {
            hoveredMesh.userData.origEmissive = mat.emissive.getHex();
          }
          mat.emissive.setHex(0x38bdf8); // Cyan hover glow
          mat.emissiveIntensity = 1.4;
        }
      });
    }
  }

  function resetHoverEffect() {
    if (hoveredMesh) {
      if (!highlightedMeshes.includes(hoveredMesh) && hoveredMesh.material) {
        const mats = Array.isArray(hoveredMesh.material) ? hoveredMesh.material : [hoveredMesh.material];
        const orig = hoveredMesh.userData.origEmissive !== undefined ? hoveredMesh.userData.origEmissive : 0x000000;
        mats.forEach(mat => {
          if ('emissive' in mat) {
            mat.emissive.setHex(orig);
            mat.emissiveIntensity = 1.0;
          }
        });
      }
      hoveredMesh = null;
    }
  }

  // Highlight all meshes of a selected component on the 3D model
  function highlightComponentMeshes(componentId) {
    clearComponentHighlights();

    const matches = interactiveMeshes.filter(m => m.userData?.id === componentId);
    matches.forEach(mesh => {
      if (mesh.material) {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        mats.forEach(mat => {
          if ('emissive' in mat) {
            if (mesh.userData.origEmissive === undefined) {
              mesh.userData.origEmissive = mat.emissive.getHex();
            }
            mat.emissive.setHex(0x00e5ff); // Cyan active highlight
            mat.emissiveIntensity = 1.8;
          }
        });
        highlightedMeshes.push(mesh);
      }
    });
  }

  function clearComponentHighlights() {
    highlightedMeshes.forEach(mesh => {
      if (mesh.material) {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        const orig = mesh.userData.origEmissive !== undefined ? mesh.userData.origEmissive : 0x000000;
        mats.forEach(mat => {
          if ('emissive' in mat) {
            mat.emissive.setHex(orig);
            mat.emissiveIntensity = 1.0;
          }
        });
      }
    });
    highlightedMeshes = [];
  }

  // Smoothly frame and focus a component up close
  function focusComponent(componentId) {
    selectedComponentId = componentId;
    updateInspectionCard(componentId);

    // Automatically enable cutaway mode so internal parts are visible
    setCutawayMode(true);

    let targetY = 0;
    let zoomDist = 5.2;
    let dir = new THREE.Vector3(3.0, 1.8, 3.8).normalize();

    switch (componentId) {
      case 'top_assembly':
        targetY = 1.15;
        zoomDist = 3.6;
        dir = new THREE.Vector3(2.5, 2.0, 3.0).normalize();
        break;
      case 'arduino_nano':
      case 'lora_sx1278':
      case 'sensor_bmp180':
      case 'sensor_mpu6050':
      case 'sensor_dht11':
        targetY = 0.45;
        zoomDist = 3.2;
        dir = new THREE.Vector3(3.0, 1.5, 3.2).normalize();
        break;
      case 'sensor_gps':
        targetY = 0.20;
        zoomDist = 3.2;
        // Direct view of the +X side bracket slot where the NEO-6M GPS module is mounted
        dir = new THREE.Vector3(3.6, 0.4, 1.2).normalize();
        break;
      case 'power_battery':
        targetY = -0.05;
        zoomDist = 3.4;
        dir = new THREE.Vector3(3.0, 0.8, 3.2).normalize();
        break;
      case 'esp32_cam':
        targetY = -0.62;
        zoomDist = 3.2;
        dir = new THREE.Vector3(2.8, -0.6, 3.2).normalize();
        break;
      case 'nadir_camera':
        targetY = -0.75;
        zoomDist = 3.0;
        // Looking up from below to clearly inspect the downward-facing lens
        dir = new THREE.Vector3(2.2, -1.8, 3.0).normalize();
        break;
      case 'casing_pla':
      default:
        targetY = 0;
        zoomDist = 5.8;
        dir = new THREE.Vector3(3.0, 1.8, 3.8).normalize();
        break;
    }

    targetLookAt.set(0, targetY, 0);
    targetCameraPos.copy(targetLookAt).add(dir.multiplyScalar(zoomDist));
    autoRotate = false;
  }

  function updateInspectionCard(componentId) {
    const data = COMPONENT_DATA[componentId];
    if (!data) return;

    const titleEl = document.getElementById('inspection-comp-title');
    const tierEl = document.getElementById('inspection-comp-tier');
    const massEl = document.getElementById('inspection-comp-mass');
    const specsEl = document.getElementById('inspection-comp-specs');
    const descEl = document.getElementById('inspection-comp-desc');

    if (titleEl) titleEl.textContent = data.name;
    if (tierEl) tierEl.textContent = data.tier;
    if (massEl) massEl.textContent = data.mass;
    if (specsEl) specsEl.textContent = data.specs;
    if (descEl) descEl.textContent = data.desc;

    // Highlight active pill
    document.querySelectorAll('[data-inspect-target]').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-inspect-target') === componentId);
    });
  }

  function setupControls() {
    const explodeBtn = document.getElementById('btn-explode-3d');
    const rotateBtn = document.getElementById('btn-rotate-3d');
    const resetBtn = document.getElementById('btn-reset-3d');
    const zoomInBtn = document.getElementById('btn-zoom-in-3d');
    const zoomOutBtn = document.getElementById('btn-zoom-out-3d');
    const shellToggleBtn = document.getElementById('btn-shell-toggle');

    if (explodeBtn) {
      explodeBtn.addEventListener('click', () => {
        isExploded = !isExploded;
        explodeBtn.textContent = isExploded ? 'Assemble' : 'Explode';
        explodeBtn.classList.toggle('active', isExploded);

        assemblies.shell.targetY = isExploded ? 0 : assemblies.shell.origY;
        assemblies.topCap.targetY = isExploded ? 2.4 : assemblies.topCap.origY;
        assemblies.tier1.targetY = isExploded ? 1.2 : assemblies.tier1.origY;
        assemblies.battery.targetY = isExploded ? 0.0 : assemblies.battery.origY;
        assemblies.tier2.targetY = isExploded ? -1.2 : assemblies.tier2.origY;
        assemblies.botCap.targetY = isExploded ? -2.4 : assemblies.botCap.origY;

        if (isExploded) {
          setCutawayMode(true);
        }
      });
    }

    if (rotateBtn) {
      rotateBtn.addEventListener('click', () => {
        autoRotate = !autoRotate;
        rotateBtn.classList.toggle('active', autoRotate);
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        resetCameraView();
      });
    }

    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        zoomCamera(0.85);
      });
    }

    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        zoomCamera(1.15);
      });
    }

    if (shellToggleBtn) {
      shellToggleBtn.addEventListener('click', () => {
        setCutawayMode(!isCutawayView);
      });
    }

    document.querySelectorAll('[data-inspect-target]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-inspect-target');
        if (targetId && COMPONENT_DATA[targetId]) {
          focusComponent(targetId);
          highlightComponentMeshes(targetId);
        }
      });
    });
  }

  function animate() {
    requestAnimationFrame(animate);

    if (autoRotate) {
      targetRotationY += 0.005;
    }

    cansatGroup.rotation.y += (targetRotationY - cansatGroup.rotation.y) * 0.05;
    cansatGroup.rotation.x += (targetRotationX - cansatGroup.rotation.x) * 0.05;

    // Smooth Camera & LookAt Lerp
    camera.position.lerp(targetCameraPos, 0.08);
    currentLookAt.lerp(targetLookAt, 0.08);
    camera.lookAt(currentLookAt);

    // Exploded View Assembly Lerp
    const lerpSpeed = 0.08;
    for (const key in assemblies) {
      const item = assemblies[key];
      if (item.mesh) {
        item.mesh.position.y += (item.targetY - item.mesh.position.y) * lerpSpeed;
      }
    }

    // High-visibility blinking beacon pulse on highlighted component meshes
    if (highlightedMeshes.length > 0) {
      // 550ms cycle: 340ms bright neon cyan flash (2.8 intensity), 210ms dimmed baseline (0.18 intensity)
      const blinkCycle = (Date.now() % 550) / 550;
      const isFlash = blinkCycle < 0.62;
      const pulse = isFlash ? 2.8 : 0.18;
      highlightedMeshes.forEach(mesh => {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        mats.forEach(mat => {
          if (mat && 'emissiveIntensity' in mat) {
            mat.emissiveIntensity = pulse;
          }
        });
      });
    }

    renderer.render(scene, camera);
  }

  function onWindowResize() {
    if (!container || !renderer || !camera) return;
    const width = container.clientWidth;
    const height = container.clientHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  window.addEventListener('DOMContentLoaded', () => {
    init3DViewer();
    setTimeout(onWindowResize, 150);
  });
})();
