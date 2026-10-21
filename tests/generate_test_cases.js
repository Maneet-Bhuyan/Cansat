'use strict';
/**
 * Stochastic & Empirically Calibrated Flight Test Case Generator
 * Cognitive CanSat Mission Control
 *
 * Calibrated against physical bench-top hardware telemetry recorded in
 * data/cansat_missions.db (MSN-20260920-192811-A2F9, MSN-20260920-194606-2DD8,
 * MSN-20260921-092203-74EE; N = 362 real packets):
 *   - Barometric altitude noise floor: sigma_h ~ 0.34 m (static) to 0.45 m (dynamic)
 *   - Barometric pressure noise floor: sigma_P ~ 0.28 hPa
 *   - Temperature noise floor: sigma_T ~ 0.15 deg C
 *   - Humidity noise floor: sigma_RH ~ 1.50 %
 *   - Accelerometer noise floor: sigma_a ~ 0.022 G
 *   - Gyroscope noise floor: sigma_g ~ 1.85 deg/s
 *   - UART / LoRa packet interval jitter: sigma_dt ~ 6 ms to 25 ms
 *   - Seeded Mulberry32 PRNG for 100% deterministic reproducibility.
 */
const fs = require('fs');
const path = require('path');

const testCasesDir = path.join(__dirname, '..', 'test_cases');
if (!fs.existsSync(testCasesDir)) {
  fs.mkdirSync(testCasesDir, { recursive: true });
}

const CSV_HEADER = 'timestamp,temp,pressure,altitude,gx,gy,gz,ax,ay,az,lat,lon,humidity,batteryVoltage,pitch,roll,accelMag';
const HOME_LAT = 22.572700;
const HOME_LON = 88.365500;
const DT = 0.8; // nominal seconds per sample (1.25 Hz downlink)
const START_ISO = '2026-08-30T10:00:00.000Z';

// Deterministic Mulberry32 PRNG + Box-Muller Gaussian sampler
let prngState = 0xCA45A701;
function seedPrng(seed) {
  prngState = seed >>> 0;
}

function randUniform() {
  let t = (prngState += 0x6D2B79F5);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

function noise(amp) {
  return (randUniform() - 0.5) * 2 * amp;
}

function gaussNoise(sigma) {
  const u1 = Math.max(1e-9, randUniform());
  const u2 = randUniform();
  const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  return z0 * sigma;
}

function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

function baroPressure(alt, p0 = 1013.25, t0 = 288.15, lapse = 0.0065) {
  return p0 * Math.pow(1 - (lapse * alt) / t0, 5.255);
}

function calculateKinematics(ax, ay, az) {
  const accelMag = Math.sqrt(ax * ax + ay * ay + az * az);
  const pitch = Math.atan2(ay, az) * (180 / Math.PI);
  const roll = Math.atan2(-ax, Math.sqrt(ay * ay + az * az)) * (180 / Math.PI);
  return { accelMag, pitch, roll };
}

function formatRow(tSec, jitterSec, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat, overrides = {}) {
  const actualTimeMs = Math.max(0, Math.round((tSec + jitterSec) * 1000));
  const date = new Date(new Date(START_ISO).getTime() + actualTimeMs);
  const k = calculateKinematics(ax, ay, az);
  return [
    date.toISOString(),
    overrides.temp !== undefined ? overrides.temp : temp.toFixed(2),
    overrides.press !== undefined ? overrides.press : press.toFixed(2),
    overrides.alt !== undefined ? overrides.alt : alt.toFixed(2),
    gx.toFixed(2),
    gy.toFixed(2),
    gz.toFixed(2),
    ax.toFixed(3),
    ay.toFixed(3),
    az.toFixed(3),
    lat.toFixed(6),
    lon.toFixed(6),
    overrides.hum !== undefined ? overrides.hum : hum.toFixed(2),
    vBat.toFixed(3),
    k.pitch.toFixed(2),
    k.roll.toFixed(2),
    k.accelMag.toFixed(3)
  ].join(',');
}

function isDroppedWindow(t, dropWindows) {
  for (const [start, end] of dropWindows) {
    if (t >= start - 1e-6 && t <= end + 1e-6) {
      return true;
    }
  }
  return false;
}

function writeCsv(filename, rows) {
  const content = CSV_HEADER + '\r\n' + rows.join('\r\n') + '\r\n';
  fs.writeFileSync(path.join(testCasesDir, filename), content, 'utf8');
  console.log(`Generated ${filename} (${rows.length} rows)`);
}

// 1. 01_nominal_sounding_flight.csv: Standard 800m balloon climb, clean apogee ejection, stable descent at -6.2 m/s, touchdown.
// Includes 1 brief 2-packet RF fade during apogee ejection plasma/staging (t=211.2..212.0s) and 9ms UART clock jitter.
function genNominalFlight() {
  seedPrng(1001);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.18;
  const totalTime = 340;
  const padDuration = 20;
  const ascentSpeed = 4.2;
  const apogeeAlt = 800;
  const apogeeTime = padDuration + (apogeeAlt / ascentSpeed);
  const descentSpeed = -6.2;
  const dropWindows = [[211.1, 212.1]]; // 2 packets dropped during pyrotechnic separation

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.022);
    let ay = -0.01 + gaussNoise(0.019);
    let az = 0.99 + gaussNoise(0.018);
    let gx = -0.35 + gaussNoise(1.75);
    let gy = 0.08 + gaussNoise(1.85);
    let gz = -0.05 + gaussNoise(1.90);

    if (t < padDuration) {
      alt = 0.5 + gaussNoise(0.32);
    } else if (t < apogeeTime) {
      alt = 0.5 + (t - padDuration) * ascentSpeed + gaussNoise(0.38);
      lat += 0.000008 * DT;
      lon += 0.000012 * DT;
      az = 1.05 + gaussNoise(0.028);
      gx = Math.sin(t * 0.5) * 5 + gaussNoise(1.85);
      gy = Math.cos(t * 0.4) * 4 + gaussNoise(1.85);
      gz = Math.sin(t * 0.2) * 8 + gaussNoise(2.10);
    } else if (t < apogeeTime + 3) {
      alt = apogeeAlt - (t - apogeeTime) * 1.5 + gaussNoise(0.45);
      ax = 1.8 + gaussNoise(0.25);
      ay = -1.5 + gaussNoise(0.25);
      az = 2.4 + gaussNoise(0.30);
      gx = 85 + gaussNoise(6.0);
      gy = -60 + gaussNoise(6.0);
      gz = 110 + gaussNoise(8.5);
    } else {
      const descentTime = t - (apogeeTime + 3);
      alt = apogeeAlt - 4.5 + descentTime * descentSpeed + gaussNoise(0.36);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
        ax = gaussNoise(0.020);
        ay = gaussNoise(0.018);
        az = 0.99 + gaussNoise(0.015);
        gx = gaussNoise(1.40);
        gy = gaussNoise(1.40);
        gz = gaussNoise(1.50);
      } else {
        lat += 0.000015 * DT;
        lon += 0.000018 * DT;
        const swing = Math.sin((t - apogeeTime) * 1.8);
        ax = swing * 0.22 + gaussNoise(0.032);
        ay = Math.cos((t - apogeeTime) * 1.8) * 0.20 + gaussNoise(0.030);
        az = 0.96 + gaussNoise(0.025);
        gx = swing * 14 + gaussNoise(2.10);
        gy = Math.cos((t - apogeeTime) * 1.8) * 12 + gaussNoise(2.10);
        gz = Math.sin((t - apogeeTime) * 0.3) * 6 + gaussNoise(1.95);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + gaussNoise(0.14);
    const press = baroPressure(alt) + gaussNoise(0.26);
    const hum = clamp(55 + (alt / 800) * 18 + gaussNoise(1.25), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.009);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('01_nominal_sounding_flight.csv', rows);
}

// 2. 02_high_altitude_burst_1200m.csv: 1200m apogee, pronounced cooling, rapid initial descent, slant-range RF dropouts.
function genHighAltitudeBurst() {
  seedPrng(2002);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.15;
  const totalTime = 420;
  const padDuration = 15;
  const ascentSpeed = 4.8;
  const apogeeAlt = 1200;
  const apogeeTime = padDuration + (apogeeAlt / ascentSpeed);
  // 3 slant-range LoRa fade windows near 1050-1200m apogee (total 8 lost packets)
  const dropWindows = [
    [232.7, 234.5], // 3 packets lost during high-slant climb
    [265.5, 267.3], // 3 packets lost at 1200m burst shock
    [296.7, 297.7]  // 2 packets lost in high-rate upper descent
  ];

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.024);
    let ay = 0.01 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.80);
    let gy = gaussNoise(1.85);
    let gz = gaussNoise(1.95);

    if (t < padDuration) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + (t - padDuration) * ascentSpeed + gaussNoise(0.42);
      lat += 0.000010 * DT;
      lon += 0.000014 * DT;
      az = 1.06 + gaussNoise(0.030);
      gx = Math.sin(t * 0.4) * 6 + gaussNoise(1.90);
      gy = Math.cos(t * 0.3) * 5 + gaussNoise(1.90);
    } else if (t < apogeeTime + 4) {
      alt = apogeeAlt - (t - apogeeTime) * 3.0 + gaussNoise(0.55);
      ax = 2.4 + gaussNoise(0.35);
      ay = -2.1 + gaussNoise(0.35);
      az = 3.8 + gaussNoise(0.40);
      gx = 120 + gaussNoise(12.0);
      gy = -95 + gaussNoise(12.0);
      gz = 140 + gaussNoise(15.0);
    } else {
      const dtDesc = t - (apogeeTime + 4);
      const vDesc = -9.5 + Math.min(2.7, dtDesc * 0.04);
      alt = apogeeAlt - 12 + dtDesc * vDesc + gaussNoise(0.40);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.24));
        az = 0.99 + gaussNoise(0.015);
      } else {
        lat += 0.000022 * DT;
        lon += 0.000020 * DT;
        ax = Math.sin(t * 1.5) * 0.25 + gaussNoise(0.038);
        ay = Math.cos(t * 1.5) * 0.22 + gaussNoise(0.036);
        az = 0.94 + gaussNoise(0.032);
        gx = Math.sin(t * 1.5) * 16 + gaussNoise(2.60);
        gy = Math.cos(t * 1.5) * 15 + gaussNoise(2.60);
      }
    }

    const temp = 26.5 - (alt / 1000) * 7.2 + gaussNoise(0.15);
    const press = baroPressure(alt) + gaussNoise(0.29);
    const hum = clamp(60 + (alt / 1200) * 25 + gaussNoise(1.40), 10, 98);
    vBat = clamp(vBat - 0.00038 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.016);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('02_high_altitude_burst_1200m.csv', rows);
}

// 3. 03_severe_wind_shear_drift.csv: Strong lateral wind shear causing significant GPS coordinate drift and heading swings.
function genWindShearDrift() {
  seedPrng(3003);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.12;
  const totalTime = 300;
  const apogeeTime = 160;
  const apogeeAlt = 650;
  // 2 multipath/wind-gust antenna fade windows (5 packets lost)
  const dropWindows = [
    [104.7, 106.5], // 3 packets lost entering shear layer
    [208.7, 209.7]  // 2 packets lost during turbulent descent gust
  ];

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.024);
    let ay = 0.01 + gaussNoise(0.022);
    let az = 0.99 + gaussNoise(0.020);
    let gx = gaussNoise(1.85);
    let gy = gaussNoise(1.85);
    let gz = gaussNoise(1.90);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.42);
      const shear = alt > 300 && alt < 550 ? 4.5 : 1.2;
      lat += (0.000025 * shear) * DT;
      lon += (0.000035 * shear) * DT;
      ax = 0.35 * Math.sin(t * 0.8) + gaussNoise(0.042);
      ay = 0.40 * Math.cos(t * 0.6) + gaussNoise(0.042);
      gz = 25 * Math.sin(t * 0.4) + gaussNoise(2.80);
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.8 + gaussNoise(0.40);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        const driftFactor = 3.8;
        lat += 0.000045 * driftFactor * DT * Math.cos(t * 0.05);
        lon += 0.000060 * driftFactor * DT * Math.sin(t * 0.04);
        ax = 0.45 * Math.sin(t * 2.2) + gaussNoise(0.055);
        ay = 0.42 * Math.cos(t * 1.9) + gaussNoise(0.055);
        az = 0.92 + gaussNoise(0.040);
        gx = 28 * Math.sin(t * 2.2) + gaussNoise(3.20);
        gy = 25 * Math.cos(t * 1.9) + gaussNoise(3.20);
        gz = 40 * Math.sin(t * 0.8) + gaussNoise(3.80);
      }
    }

    const temp = 24.0 - (alt / 1000) * 6.5 + gaussNoise(0.15);
    const press = baroPressure(alt) + gaussNoise(0.30);
    const hum = clamp(50 + (alt / 650) * 20 + gaussNoise(1.45), 10, 95);
    vBat = clamp(vBat - 0.00032 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.020);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('03_severe_wind_shear_drift.csv', rows);
}

// 4. 04_apogee_ejection_shock_tumble.csv: 5.2g peak ejection shock with rapid 3-axis tumbling (>160 deg/s) triggering anomaly flags.
function genApogeeShockTumble() {
  seedPrng(4004);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.10;
  const totalTime = 280;
  const apogeeTime = 140;
  const apogeeAlt = 600;
  // 2 deep polarization-nulling RF gaps during violent 3-axis tumble (6 packets lost)
  const dropWindows = [
    [141.5, 143.3], // 3 packets lost during initial 5G shock + tumble
    [145.5, 147.3]  // 3 packets lost during secondary spin reversal
  ];

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.02 + gaussNoise(0.022);
    let ay = 0.02 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.80);
    let gy = gaussNoise(1.80);
    let gz = gaussNoise(1.90);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.38);
      lat += 0.000010 * DT;
      lon += 0.000012 * DT;
    } else if (t < apogeeTime + 8) {
      const shockDt = t - apogeeTime;
      alt = apogeeAlt - shockDt * 3.5 + gaussNoise(0.60);
      ax = 3.2 * Math.sin(shockDt * 5) + gaussNoise(0.30);
      ay = -2.8 * Math.cos(shockDt * 4) + gaussNoise(0.30);
      az = 4.1 + Math.exp(-shockDt * 0.5) * 1.1 + gaussNoise(0.35);
      gx = 175 * Math.sin(shockDt * 6) + gaussNoise(10.0);
      gy = -165 * Math.cos(shockDt * 5) + gaussNoise(10.0);
      gz = 190 * Math.sin(shockDt * 4) + gaussNoise(12.0);
    } else {
      const dtDesc = t - (apogeeTime + 8);
      alt = apogeeAlt - 28 - dtDesc * 6.4 + gaussNoise(0.38);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        lat += 0.000018 * DT;
        lon += 0.000022 * DT;
        ax = 0.2 * Math.sin(t * 1.2) + gaussNoise(0.032);
        ay = 0.2 * Math.cos(t * 1.2) + gaussNoise(0.032);
        az = 0.95 + gaussNoise(0.025);
        gx = 12 * Math.sin(t * 1.2) + gaussNoise(2.10);
        gy = 10 * Math.cos(t * 1.2) + gaussNoise(2.10);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + gaussNoise(0.14);
    const press = baroPressure(alt) + gaussNoise(0.28);
    const hum = clamp(52 + (alt / 600) * 18 + gaussNoise(1.35), 10, 95);
    vBat = clamp(vBat - 0.00034 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.023);
      // Inject 1 transient I2C bus shock glitch on pressure at t=140.8s (pyro fire instant)
      const overrides = Math.abs(t - 140.8) < 0.05 ? { press: '' } : {};
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat, overrides));
    }
  }
  writeCsv('04_apogee_ejection_shock_tumble.csv', rows);
}

// 5. 05_parachute_pendulum_resonance.csv: Harmonic pitch/roll swing (+-18 deg at 0.7 Hz) under turbulent canopy.
function genPendulumResonance() {
  seedPrng(5005);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.14;
  const totalTime = 260;
  const apogeeTime = 110;
  const apogeeAlt = 500;
  const dropWindows = [[164.7, 165.7]]; // 2 packets lost at peak canopy swing angle

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.022);
    let ay = 0.01 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.75);
    let gy = gaussNoise(1.75);
    let gz = gaussNoise(1.85);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.36);
      lat += 0.000008 * DT;
      lon += 0.000010 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.9 + gaussNoise(0.36);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        lat += 0.000016 * DT;
        lon += 0.000018 * DT;
        const omega = 2 * Math.PI * 0.7;
        const swingAngleRad = (18 * Math.PI / 180) * Math.sin(dtDesc * omega);
        const swingAngleRollRad = (16 * Math.PI / 180) * Math.cos(dtDesc * omega);
        ax = -Math.sin(swingAngleRollRad) + gaussNoise(0.028);
        ay = Math.sin(swingAngleRad) + gaussNoise(0.028);
        az = Math.cos(swingAngleRad) * Math.cos(swingAngleRollRad) + gaussNoise(0.025);
        gx = (18 * omega) * Math.cos(dtDesc * omega) + gaussNoise(2.10);
        gy = -(16 * omega) * Math.sin(dtDesc * omega) + gaussNoise(2.10);
        gz = 8 * Math.sin(dtDesc * 1.5) + gaussNoise(1.90);
      }
    }

    const temp = 24.5 - (alt / 1000) * 6.5 + gaussNoise(0.14);
    const press = baroPressure(alt) + gaussNoise(0.27);
    const hum = clamp(54 + (alt / 500) * 16 + gaussNoise(1.30), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.012);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('05_parachute_pendulum_resonance.csv', rows);
}

// 6. 06_delayed_chute_deployment.csv: 5-second freefall exceeding -25 m/s followed by sharp 4.8G deceleration spike.
function genDelayedChuteDeployment() {
  seedPrng(6006);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.15;
  const totalTime = 260;
  const apogeeTime = 120;
  const apogeeAlt = 650;
  const freefallDuration = 5.0;
  const dropWindows = [
    [122.3, 123.3], // 2 packets lost during high-velocity freefall Doppler/tumbling
    [126.3, 128.1]  // 3 packets lost during 4.8G canopy snatch deceleration
  ];

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.022);
    let ay = 0.01 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.80);
    let gy = gaussNoise(1.80);
    let gz = gaussNoise(1.90);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.38);
      lat += 0.000009 * DT;
      lon += 0.000011 * DT;
    } else if (t < apogeeTime + freefallDuration) {
      const dtFF = t - apogeeTime;
      alt = apogeeAlt + 0.5 * (-9.81 * 0.85) * dtFF * dtFF + gaussNoise(0.65);
      ax = gaussNoise(0.06);
      ay = gaussNoise(0.06);
      az = 0.05 + gaussNoise(0.04);
      gx = 45 * Math.sin(dtFF * 2) + gaussNoise(4.0);
      gy = 40 * Math.cos(dtFF * 2) + gaussNoise(4.0);
      gz = 60 * Math.sin(dtFF * 3) + gaussNoise(6.0);
    } else if (t < apogeeTime + freefallDuration + 3.0) {
      const dtSnatch = t - (apogeeTime + freefallDuration);
      const ffEndAlt = apogeeAlt - 90;
      alt = ffEndAlt - dtSnatch * 12.0 + gaussNoise(0.50);
      ax = -1.2 + gaussNoise(0.25);
      ay = 1.4 + gaussNoise(0.25);
      az = 4.8 + gaussNoise(0.30);
      gx = 80 + gaussNoise(8.0);
      gy = -70 + gaussNoise(8.0);
      gz = 90 + gaussNoise(10.0);
    } else {
      const dtDesc = t - (apogeeTime + freefallDuration + 3.0);
      const chuteStartAlt = apogeeAlt - 126;
      alt = chuteStartAlt - dtDesc * 6.1 + gaussNoise(0.36);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        lat += 0.000015 * DT;
        lon += 0.000017 * DT;
        ax = 0.15 * Math.sin(t * 1.4) + gaussNoise(0.028);
        ay = 0.15 * Math.cos(t * 1.4) + gaussNoise(0.028);
        az = 0.97 + gaussNoise(0.022);
        gx = 10 * Math.sin(t * 1.4) + gaussNoise(1.90);
        gy = 9 * Math.cos(t * 1.4) + gaussNoise(1.90);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + gaussNoise(0.14);
    const press = baroPressure(alt) + gaussNoise(0.28);
    const hum = clamp(52 + (alt / 650) * 20 + gaussNoise(1.35), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.018);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('06_delayed_chute_deployment.csv', rows);
}

// 7. 07_thermal_inversion_sounding.csv: Lapse rate anomalies and humidity inversion layers during descent.
function genThermalInversionSounding() {
  seedPrng(7007);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.16;
  const totalTime = 320;
  const apogeeTime = 160;
  const apogeeAlt = 750;
  const dropWindows = [[188.7, 189.7]]; // 2 packets lost passing through ducting inversion boundary

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.022);
    let ay = 0.01 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.75);
    let gy = gaussNoise(1.75);
    let gz = gaussNoise(1.85);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.36);
      lat += 0.000008 * DT;
      lon += 0.000010 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.6 + gaussNoise(0.36);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        lat += 0.000014 * DT;
        lon += 0.000016 * DT;
        ax = 0.12 * Math.sin(t * 1.3) + gaussNoise(0.026);
        ay = 0.12 * Math.cos(t * 1.3) + gaussNoise(0.026);
        az = 0.98 + gaussNoise(0.020);
      }
    }

    let temp = 22.0;
    if (alt < 250) {
      temp = 22.0 - (alt / 250) * 2.0;
    } else if (alt <= 450) {
      temp = 20.0 + ((alt - 250) / 200) * 4.5;
    } else {
      temp = 24.5 - ((alt - 450) / 300) * 4.0;
    }
    temp += gaussNoise(0.14);

    let hum = 60;
    if (alt < 250) {
      hum = 85 - (alt / 250) * 15;
    } else if (alt <= 450) {
      hum = 42 + gaussNoise(1.60);
    } else {
      hum = 75 + gaussNoise(1.40);
    }
    hum = clamp(hum, 10, 98);

    const press = baroPressure(alt) + gaussNoise(0.26);
    vBat = clamp(vBat - 0.00033 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.010);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('07_thermal_inversion_sounding.csv', rows);
}

// 8. 08_sensor_glitch_gps_recovery.csv: Transient GPS lock loss (0.0, 0.0), I2C bus glitches, and satellite re-acquisition.
function genSensorGlitchGpsRecovery() {
  seedPrng(8008);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.15;
  const totalTime = 260;
  const apogeeTime = 120;
  const apogeeAlt = 600;
  const dropWindows = [[114.3, 116.1]]; // 3 packets lost during RF/EMI burst that also resets GNSS

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.022);
    let ay = 0.01 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.80);
    let gy = gaussNoise(1.80);
    let gz = gaussNoise(1.90);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.38);
      lat += 0.000009 * DT;
      lon += 0.000012 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 6.0 + gaussNoise(0.36);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        lat += 0.000015 * DT;
        lon += 0.000018 * DT;
      }
    }

    let outLat = lat;
    let outLon = lon;

    if (t >= 90 && t <= 140) {
      if (t >= 100 && t <= 125) {
        outLat = 0.0;
        outLon = 0.0;
      } else {
        outLat = lat + noise(0.005);
        outLon = lon + noise(0.005);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + gaussNoise(0.14);
    const press = baroPressure(alt) + gaussNoise(0.28);
    const hum = clamp(55 + (alt / 600) * 18 + gaussNoise(1.35), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + gaussNoise(0.004), 3.4, 4.2);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.015);
      const overrides = {};
      // Inject 2 transient sensor framing glitches during EMI window
      if (Math.abs(t - 96.0) < 0.05) overrides.hum = '';
      if (Math.abs(t - 131.2) < 0.05) overrides.temp = 'ERR';
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, outLat, outLon, hum, vBat, overrides));
    }
  }
  writeCsv('08_sensor_glitch_gps_recovery.csv', rows);
}

// 9. 09_low_battery_voltage_sag.csv: Battery decaying from 3.65V to 3.25V triggering low-voltage safety alarms and brownout RF drops.
function genLowBatterySag() {
  seedPrng(9009);
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 3.65;
  const totalTime = 240;
  const apogeeTime = 110;
  const apogeeAlt = 500;
  // 2 LoRa PA brownout gaps during deep voltage sag below 3.35V (6 lost packets)
  const dropWindows = [
    [191.9, 193.7], // 3 packets lost during PA current spike sag
    [223.9, 225.7]  // 3 packets lost near end-of-discharge brownout
  ];

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + gaussNoise(0.022);
    let ay = 0.01 + gaussNoise(0.020);
    let az = 0.99 + gaussNoise(0.018);
    let gx = gaussNoise(1.80);
    let gy = gaussNoise(1.80);
    let gz = gaussNoise(1.90);

    if (t < 15) {
      alt = 0.5 + gaussNoise(0.30);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + gaussNoise(0.36);
      lat += 0.000008 * DT;
      lon += 0.000010 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.8 + gaussNoise(0.36);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(gaussNoise(0.22));
      } else {
        lat += 0.000015 * DT;
        lon += 0.000017 * DT;
      }
    }

    const rfBursts = (Math.sin(t * 1.5) > 0.8) ? 0.08 : 0.0;
    vBat = clamp(3.65 - (t / totalTime) * 0.32 - rfBursts + gaussNoise(0.006), 3.25, 4.20);

    const temp = 25.0 - (alt / 1000) * 6.5 + gaussNoise(0.14);
    const press = baroPressure(alt) + gaussNoise(0.28);
    const hum = clamp(52 + (alt / 500) * 16 + gaussNoise(1.35), 10, 95);

    if (!isDroppedWindow(t, dropWindows)) {
      const jitter = t === 0 ? 0 : gaussNoise(0.022);
      rows.push(formatRow(t, jitter, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
    }
  }
  writeCsv('09_low_battery_voltage_sag.csv', rows);
}

// 10. 10_ground_pad_static_test.csv: 3-minute pre-launch ground integration run showing baseline calibration drift and 1G gravity alignment.
// Matches physical bench-top noise floors (sigma_h=0.34m, sigma_P=0.28hPa, sigma_T=0.15C, sigma_RH=1.50%, 100% packet completeness).
function genGroundPadStaticTest() {
  seedPrng(1010);
  const rows = [];
  const alt = 0.35;
  const lat = HOME_LAT;
  const lon = HOME_LON;
  let vBat = 4.19;
  const totalTime = 180;

  for (let t = 0; t <= totalTime; t += DT) {
    const ax = 0.005 + Math.sin(t * 0.05) * 0.008 + gaussNoise(0.022);
    const ay = -0.004 + Math.cos(t * 0.04) * 0.008 + gaussNoise(0.019);
    const az = 0.992 + gaussNoise(0.016);
    const gx = -0.36 + gaussNoise(1.75);
    const gy = 0.08 + gaussNoise(2.10);
    const gz = -0.05 + gaussNoise(2.40);

    const curAlt = Math.max(0.02, alt + gaussNoise(0.34));
    const temp = 27.83 + Math.sin(t * 0.02) * 0.12 + gaussNoise(0.15);
    const press = 1013.25 + gaussNoise(0.28);
    const hum = 67.34 + gaussNoise(1.50);
    vBat = clamp(vBat - 0.00015 * DT + gaussNoise(0.003), 3.9, 4.2);

    const jitter = t === 0 ? 0 : gaussNoise(0.006);
    rows.push(formatRow(t, jitter, temp, press, curAlt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('10_ground_pad_static_test.csv', rows);
}

console.log('Generating 10 empirically calibrated stochastic flight test cases in test_cases/...');
genNominalFlight();
genHighAltitudeBurst();
genWindShearDrift();
genApogeeShockTumble();
genPendulumResonance();
genDelayedChuteDeployment();
genThermalInversionSounding();
genSensorGlitchGpsRecovery();
genLowBatterySag();
genGroundPadStaticTest();
console.log('All 10 test cases generated successfully!');
