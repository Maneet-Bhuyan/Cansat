'use strict';
const fs = require('fs');
const path = require('path');

const testCasesDir = path.join(__dirname, 'test_cases');
if (!fs.existsSync(testCasesDir)) {
  fs.mkdirSync(testCasesDir, { recursive: true });
}

const CSV_HEADER = 'timestamp,temp,pressure,altitude,gx,gy,gz,ax,ay,az,lat,lon,humidity,batteryVoltage,pitch,roll,accelMag';
const HOME_LAT = 22.572700;
const HOME_LON = 88.365500;
const DT = 0.8; // seconds per sample
const START_ISO = '2026-08-30T10:00:00.000Z';

function noise(amp) {
  return (Math.random() - 0.5) * 2 * amp;
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

function formatRow(tSec, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat) {
  const date = new Date(new Date(START_ISO).getTime() + tSec * 1000);
  const k = calculateKinematics(ax, ay, az);
  return [
    date.toISOString(),
    temp.toFixed(2),
    press.toFixed(2),
    alt.toFixed(2),
    gx.toFixed(2),
    gy.toFixed(2),
    gz.toFixed(2),
    ax.toFixed(3),
    ay.toFixed(3),
    az.toFixed(3),
    lat.toFixed(6),
    lon.toFixed(6),
    hum.toFixed(2),
    vBat.toFixed(3),
    k.pitch.toFixed(2),
    k.roll.toFixed(2),
    k.accelMag.toFixed(3)
  ].join(',');
}

function writeCsv(filename, rows) {
  const content = CSV_HEADER + '\r\n' + rows.join('\r\n') + '\r\n';
  fs.writeFileSync(path.join(testCasesDir, filename), content, 'utf8');
  console.log(`Generated ${filename} (${rows.length} rows)`);
}

// 1. 01_nominal_sounding_flight.csv: Standard 800m balloon climb, clean apogee ejection, stable descent at -6.2 m/s, touchdown.
function genNominalFlight() {
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

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < padDuration) {
      alt = 0.5 + noise(0.1);
    } else if (t < apogeeTime) {
      alt = 0.5 + (t - padDuration) * ascentSpeed + noise(0.2);
      lat += 0.000008 * DT;
      lon += 0.000012 * DT;
      az = 1.05 + noise(0.03);
      gx = Math.sin(t * 0.5) * 5 + noise(1.5);
      gy = Math.cos(t * 0.4) * 4 + noise(1.5);
      gz = Math.sin(t * 0.2) * 8 + noise(1.0);
    } else if (t < apogeeTime + 3) {
      alt = apogeeAlt - (t - apogeeTime) * 1.5;
      ax = 1.8 + noise(0.4);
      ay = -1.5 + noise(0.4);
      az = 2.4 + noise(0.5);
      gx = 85 + noise(10);
      gy = -60 + noise(10);
      gz = 110 + noise(15);
    } else {
      const descentTime = t - (apogeeTime + 3);
      alt = apogeeAlt - 4.5 + descentTime * descentSpeed + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
        ax = noise(0.02);
        ay = noise(0.02);
        az = 0.99 + noise(0.01);
        gx = noise(0.3);
        gy = noise(0.3);
        gz = noise(0.3);
      } else {
        lat += 0.000015 * DT;
        lon += 0.000018 * DT;
        const swing = Math.sin((t - apogeeTime) * 1.8);
        ax = swing * 0.22 + noise(0.04);
        ay = Math.cos((t - apogeeTime) * 1.8) * 0.20 + noise(0.04);
        az = 0.96 + noise(0.03);
        gx = swing * 14 + noise(2.0);
        gy = Math.cos((t - apogeeTime) * 1.8) * 12 + noise(2.0);
        gz = Math.sin((t - apogeeTime) * 0.3) * 6 + noise(1.0);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.1);
    const hum = clamp(55 + (alt / 800) * 18 + noise(0.4), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('01_nominal_sounding_flight.csv', rows);
}

// 2. 02_high_altitude_burst_1200m.csv: 1200m apogee, pronounced cooling (15°C), rapid initial descent.
function genHighAltitudeBurst() {
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

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < padDuration) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + (t - padDuration) * ascentSpeed + noise(0.2);
      lat += 0.000010 * DT;
      lon += 0.000014 * DT;
      az = 1.06 + noise(0.03);
      gx = Math.sin(t * 0.4) * 6 + noise(1.5);
      gy = Math.cos(t * 0.3) * 5 + noise(1.5);
    } else if (t < apogeeTime + 4) {
      alt = apogeeAlt - (t - apogeeTime) * 3.0;
      ax = 2.4 + noise(0.5);
      ay = -2.1 + noise(0.5);
      az = 3.8 + noise(0.6);
      gx = 120 + noise(20);
      gy = -95 + noise(20);
      gz = 140 + noise(25);
    } else {
      const dtDesc = t - (apogeeTime + 4);
      const vDesc = -9.5 + Math.min(2.7, dtDesc * 0.04);
      alt = apogeeAlt - 12 + dtDesc * vDesc + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
        az = 0.99 + noise(0.01);
      } else {
        lat += 0.000022 * DT;
        lon += 0.000020 * DT;
        ax = Math.sin(t * 1.5) * 0.25 + noise(0.05);
        ay = Math.cos(t * 1.5) * 0.22 + noise(0.05);
        az = 0.94 + noise(0.04);
        gx = Math.sin(t * 1.5) * 16 + noise(3.0);
        gy = Math.cos(t * 1.5) * 15 + noise(3.0);
      }
    }

    const temp = 26.5 - (alt / 1000) * 7.2 + noise(0.06);
    const press = baroPressure(alt) + noise(0.1);
    const hum = clamp(60 + (alt / 1200) * 25 + noise(0.5), 10, 98);
    vBat = clamp(vBat - 0.00038 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('02_high_altitude_burst_1200m.csv', rows);
}

// 3. 03_severe_wind_shear_drift.csv: Strong lateral wind shear causing significant GPS coordinate drift and heading swings.
function genWindShearDrift() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.12;
  const totalTime = 300;
  const apogeeTime = 160;
  const apogeeAlt = 650;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      const shear = alt > 300 && alt < 550 ? 4.5 : 1.2;
      lat += (0.000025 * shear) * DT;
      lon += (0.000035 * shear) * DT;
      ax = 0.35 * Math.sin(t * 0.8) + noise(0.05);
      ay = 0.40 * Math.cos(t * 0.6) + noise(0.05);
      gz = 25 * Math.sin(t * 0.4) + noise(3.0);
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.8 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
      } else {
        const driftFactor = 3.8;
        lat += 0.000045 * driftFactor * DT * Math.cos(t * 0.05);
        lon += 0.000060 * driftFactor * DT * Math.sin(t * 0.04);
        ax = 0.45 * Math.sin(t * 2.2) + noise(0.08);
        ay = 0.42 * Math.cos(t * 1.9) + noise(0.08);
        az = 0.92 + noise(0.05);
        gx = 28 * Math.sin(t * 2.2) + noise(4.0);
        gy = 25 * Math.cos(t * 1.9) + noise(4.0);
        gz = 40 * Math.sin(t * 0.8) + noise(5.0);
      }
    }

    const temp = 24.0 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.12);
    const hum = clamp(50 + (alt / 650) * 20 + noise(0.5), 10, 95);
    vBat = clamp(vBat - 0.00032 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('03_severe_wind_shear_drift.csv', rows);
}

// 4. 04_apogee_ejection_shock_tumble.csv: 5.2g peak ejection shock with rapid 3-axis tumbling (>160°/s) triggering anomaly flags.
function genApogeeShockTumble() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.10;
  const totalTime = 280;
  const apogeeTime = 140;
  const apogeeAlt = 600;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.02 + noise(0.02);
    let ay = 0.02 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      lat += 0.000010 * DT;
      lon += 0.000012 * DT;
    } else if (t < apogeeTime + 8) {
      const shockDt = t - apogeeTime;
      alt = apogeeAlt - shockDt * 3.5;
      ax = 3.2 * Math.sin(shockDt * 5) + noise(0.4);
      ay = -2.8 * Math.cos(shockDt * 4) + noise(0.4);
      az = 4.1 + Math.exp(-shockDt * 0.5) * 1.1 + noise(0.5);
      gx = 175 * Math.sin(shockDt * 6) + noise(15);
      gy = -165 * Math.cos(shockDt * 5) + noise(15);
      gz = 190 * Math.sin(shockDt * 4) + noise(20);
    } else {
      const dtDesc = t - (apogeeTime + 8);
      alt = apogeeAlt - 28 - dtDesc * 6.4 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
      } else {
        lat += 0.000018 * DT;
        lon += 0.000022 * DT;
        ax = 0.2 * Math.sin(t * 1.2) + noise(0.04);
        ay = 0.2 * Math.cos(t * 1.2) + noise(0.04);
        az = 0.95 + noise(0.03);
        gx = 12 * Math.sin(t * 1.2) + noise(2.0);
        gy = 10 * Math.cos(t * 1.2) + noise(2.0);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.15);
    const hum = clamp(52 + (alt / 600) * 18 + noise(0.4), 10, 95);
    vBat = clamp(vBat - 0.00034 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('04_apogee_ejection_shock_tumble.csv', rows);
}

// 5. 05_parachute_pendulum_resonance.csv: Harmonic pitch/roll swing (±18° at 0.7 Hz) under turbulent canopy.
function genPendulumResonance() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.14;
  const totalTime = 260;
  const apogeeTime = 110;
  const apogeeAlt = 500;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      lat += 0.000008 * DT;
      lon += 0.000010 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.9 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
      } else {
        lat += 0.000016 * DT;
        lon += 0.000018 * DT;
        const omega = 2 * Math.PI * 0.7;
        const swingAngleRad = (18 * Math.PI / 180) * Math.sin(dtDesc * omega);
        const swingAngleRollRad = (16 * Math.PI / 180) * Math.cos(dtDesc * omega);
        ax = -Math.sin(swingAngleRollRad) + noise(0.03);
        ay = Math.sin(swingAngleRad) + noise(0.03);
        az = Math.cos(swingAngleRad) * Math.cos(swingAngleRollRad) + noise(0.03);
        gx = (18 * omega) * Math.cos(dtDesc * omega) + noise(2.0);
        gy = -(16 * omega) * Math.sin(dtDesc * omega) + noise(2.0);
        gz = 8 * Math.sin(dtDesc * 1.5) + noise(1.5);
      }
    }

    const temp = 24.5 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.12);
    const hum = clamp(54 + (alt / 500) * 16 + noise(0.4), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('05_parachute_pendulum_resonance.csv', rows);
}

// 6. 06_delayed_chute_deployment.csv: 4-second freefall exceeding -25 m/s followed by sharp deceleration spike.
function genDelayedChuteDeployment() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.15;
  const totalTime = 260;
  const apogeeTime = 120;
  const apogeeAlt = 650;
  const freefallDuration = 5.0;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      lat += 0.000009 * DT;
      lon += 0.000011 * DT;
    } else if (t < apogeeTime + freefallDuration) {
      const dtFF = t - apogeeTime;
      alt = apogeeAlt + 0.5 * (-9.81 * 0.85) * dtFF * dtFF;
      ax = noise(0.08);
      ay = noise(0.08);
      az = 0.05 + noise(0.05);
      gx = 45 * Math.sin(dtFF * 2) + noise(5);
      gy = 40 * Math.cos(dtFF * 2) + noise(5);
      gz = 60 * Math.sin(dtFF * 3) + noise(8);
    } else if (t < apogeeTime + freefallDuration + 3.0) {
      const dtSnatch = t - (apogeeTime + freefallDuration);
      const ffEndAlt = apogeeAlt - 90;
      alt = ffEndAlt - dtSnatch * 12.0;
      ax = -1.2 + noise(0.3);
      ay = 1.4 + noise(0.3);
      az = 4.8 + noise(0.4);
      gx = 80 + noise(10);
      gy = -70 + noise(10);
      gz = 90 + noise(12);
    } else {
      const dtDesc = t - (apogeeTime + freefallDuration + 3.0);
      const chuteStartAlt = apogeeAlt - 126;
      alt = chuteStartAlt - dtDesc * 6.1 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
      } else {
        lat += 0.000015 * DT;
        lon += 0.000017 * DT;
        ax = 0.15 * Math.sin(t * 1.4) + noise(0.03);
        ay = 0.15 * Math.cos(t * 1.4) + noise(0.03);
        az = 0.97 + noise(0.02);
        gx = 10 * Math.sin(t * 1.4) + noise(1.5);
        gy = 9 * Math.cos(t * 1.4) + noise(1.5);
      }
    }

    const temp = 25.0 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.15);
    const hum = clamp(52 + (alt / 650) * 20 + noise(0.4), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('06_delayed_chute_deployment.csv', rows);
}

// 7. 07_thermal_inversion_sounding.csv: Lapse rate anomalies and humidity inversion layers during descent.
function genThermalInversionSounding() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.16;
  const totalTime = 320;
  const apogeeTime = 160;
  const apogeeAlt = 750;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      lat += 0.000008 * DT;
      lon += 0.000010 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.6 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
      } else {
        lat += 0.000014 * DT;
        lon += 0.000016 * DT;
        ax = 0.12 * Math.sin(t * 1.3) + noise(0.03);
        ay = 0.12 * Math.cos(t * 1.3) + noise(0.03);
        az = 0.98 + noise(0.02);
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
    temp += noise(0.05);

    let hum = 60;
    if (alt < 250) {
      hum = 85 - (alt / 250) * 15;
    } else if (alt <= 450) {
      hum = 42 + noise(2.0);
    } else {
      hum = 75 + noise(1.5);
    }
    hum = clamp(hum, 10, 98);

    const press = baroPressure(alt) + noise(0.1);
    vBat = clamp(vBat - 0.00033 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('07_thermal_inversion_sounding.csv', rows);
}

// 8. 08_sensor_glitch_gps_recovery.csv: Transient GPS lock loss (0.0, 0.0) and subsequent satellite re-acquisition.
function genSensorGlitchGpsRecovery() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 4.15;
  const totalTime = 260;
  const apogeeTime = 120;
  const apogeeAlt = 600;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      lat += 0.000009 * DT;
      lon += 0.000012 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 6.0 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
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

    const temp = 25.0 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.12);
    const hum = clamp(55 + (alt / 600) * 18 + noise(0.4), 10, 95);
    vBat = clamp(vBat - 0.00035 * DT + noise(0.001), 3.4, 4.2);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, outLat, outLon, hum, vBat));
  }
  writeCsv('08_sensor_glitch_gps_recovery.csv', rows);
}

// 9. 09_low_battery_voltage_sag.csv: Battery decaying from 4.18V to 3.35V triggering low-voltage safety alarms.
function genLowBatterySag() {
  const rows = [];
  let alt = 0.5;
  let lat = HOME_LAT;
  let lon = HOME_LON;
  let vBat = 3.65;
  const totalTime = 240;
  const apogeeTime = 110;
  const apogeeAlt = 500;

  for (let t = 0; t <= totalTime; t += DT) {
    let ax = 0.01 + noise(0.02);
    let ay = 0.01 + noise(0.02);
    let az = 0.99 + noise(0.02);
    let gx = noise(1.0);
    let gy = noise(1.0);
    let gz = noise(0.5);

    if (t < 15) {
      alt = 0.5 + noise(0.05);
    } else if (t < apogeeTime) {
      alt = 0.5 + ((t - 15) / (apogeeTime - 15)) * apogeeAlt + noise(0.2);
      lat += 0.000008 * DT;
      lon += 0.000010 * DT;
    } else {
      const dtDesc = t - apogeeTime;
      alt = apogeeAlt - dtDesc * 5.8 + noise(0.2);
      if (alt <= 0.2) {
        alt = 0.2 + Math.abs(noise(0.05));
      } else {
        lat += 0.000015 * DT;
        lon += 0.000017 * DT;
      }
    }

    const rfBursts = (Math.sin(t * 1.5) > 0.8) ? 0.08 : 0.0;
    vBat = clamp(3.65 - (t / totalTime) * 0.32 - rfBursts + noise(0.005), 3.25, 4.20);

    const temp = 25.0 - (alt / 1000) * 6.5 + noise(0.05);
    const press = baroPressure(alt) + noise(0.12);
    const hum = clamp(52 + (alt / 500) * 16 + noise(0.4), 10, 95);

    rows.push(formatRow(t, temp, press, alt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('09_low_battery_voltage_sag.csv', rows);
}

// 10. 10_ground_pad_static_test.csv: 3-minute pre-launch ground integration run showing baseline calibration drift and 1G gravity alignment.
function genGroundPadStaticTest() {
  const rows = [];
  const alt = 0.2;
  const lat = HOME_LAT;
  const lon = HOME_LON;
  let vBat = 4.19;
  const totalTime = 180;

  for (let t = 0; t <= totalTime; t += DT) {
    const ax = 0.005 + Math.sin(t * 0.05) * 0.01 + noise(0.008);
    const ay = -0.004 + Math.cos(t * 0.04) * 0.01 + noise(0.008);
    const az = 0.998 + noise(0.006);
    const gx = 0.12 + noise(0.25);
    const gy = -0.08 + noise(0.25);
    const gz = 0.02 + noise(0.15);

    const curAlt = alt + noise(0.08);
    const temp = 25.2 + Math.sin(t * 0.02) * 0.4 + noise(0.03);
    const press = 1013.25 + noise(0.08);
    const hum = 58.5 + noise(0.2);
    vBat = clamp(vBat - 0.00015 * DT + noise(0.0008), 3.9, 4.2);

    rows.push(formatRow(t, temp, press, curAlt, gx, gy, gz, ax, ay, az, lat, lon, hum, vBat));
  }
  writeCsv('10_ground_pad_static_test.csv', rows);
}

console.log('Generating 10 comprehensive flight test cases in test_cases/...');
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
