# PowerShell generator for 10 Comprehensive CanSat Test Cases
$testCasesDir = "E:\Cansat\test_cases"
if (!(Test-Path -Path $testCasesDir)) {
    New-Item -ItemType Directory -Path $testCasesDir -Force | Out-Null
}

$CSV_HEADER = "timestamp,temp,pressure,altitude,gx,gy,gz,ax,ay,az,lat,lon,humidity,batteryVoltage,pitch,roll,accelMag"
$HOME_LAT = 22.572700
$HOME_LON = 88.365500
$DT = 0.8
$START_TIME = [DateTime]::Parse("2026-08-30T10:00:00.000Z").ToUniversalTime()
$rand = New-Object System.Random(42)

function Get-Noise([double]$amp) {
    return ($rand.NextDouble() - 0.5) * 2.0 * $amp
}

function Clamp([double]$v, [double]$min, [double]$max) {
    if ($v -lt $min) { return $min }
    if ($v -gt $max) { return $max }
    return $v
}

function Get-BaroPressure([double]$alt) {
    $p0 = 1013.25
    $t0 = 288.15
    $lapse = 0.0065
    return $p0 * [Math]::Pow(1.0 - ($lapse * $alt) / $t0, 5.255)
}

function Format-Row([double]$tSec, [double]$temp, [double]$press, [double]$alt, [double]$gx, [double]$gy, [double]$gz, [double]$ax, [double]$ay, [double]$az, [double]$lat, [double]$lon, [double]$hum, [double]$vBat) {
    $dtObj = $START_TIME.AddSeconds($tSec)
    $tsIso = $dtObj.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $accelMag = [Math]::Sqrt($ax * $ax + $ay * $ay + $az * $az)
    $pitch = [Math]::Atan2($ay, $az) * (180.0 / [Math]::PI)
    $roll = [Math]::Atan2(-$ax, [Math]::Sqrt($ay * $ay + $az * $az)) * (180.0 / [Math]::PI)
    
    return "{0},{1:F2},{2:F2},{3:F2},{4:F2},{5:F2},{6:F2},{7:F3},{8:F3},{9:F3},{10:F6},{11:F6},{12:F2},{13:F3},{14:F2},{15:F2},{16:F3}" -f `
        $tsIso, $temp, $press, $alt, $gx, $gy, $gz, $ax, $ay, $az, $lat, $lon, $hum, $vBat, $pitch, $roll, $accelMag
}

function Write-TestCaseCsv([string]$filename, [System.Collections.Generic.List[string]]$rows) {
    $filePath = Join-Path $testCasesDir $filename
    $content = $CSV_HEADER + "`r`n" + ($rows -join "`r`n") + "`r`n"
    [System.IO.File]::WriteAllText($filePath, $content, [System.Text.Encoding]::UTF8)
    Write-Host "Generated $filename ($($rows.Count) rows)"
}

# 1. 01_nominal_sounding_flight.csv (Full trajectory to Touchdown)
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.18
$padDuration = 20.0; $ascentSpeed = 4.5; $apogeeAlt = 800.0; $apogeeTime = $padDuration + ($apogeeAlt / $ascentSpeed)
$descentSpeed = -6.0; $descentDuration = ($apogeeAlt / [Math]::Abs($descentSpeed)); $touchdownTime = $apogeeTime + 3.0 + $descentDuration; $totalTime = $touchdownTime + 25.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt $padDuration) {
        $alt = 0.5 + (Get-Noise 0.1)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + ($t - $padDuration) * $ascentSpeed + (Get-Noise 0.2)
        $lat += 0.000008 * $DT; $lon += 0.000012 * $DT
        $az = 1.05 + (Get-Noise 0.03)
        $gx = [Math]::Sin($t * 0.5) * 5.0 + (Get-Noise 1.5)
        $gy = [Math]::Cos($t * 0.4) * 4.0 + (Get-Noise 1.5)
        $gz = [Math]::Sin($t * 0.2) * 8.0 + (Get-Noise 1.0)
    } elseif ($t -lt ($apogeeTime + 3.0)) {
        $alt = $apogeeAlt - ($t - $apogeeTime) * 1.5
        $ax = 1.8 + (Get-Noise 0.4); $ay = -1.5 + (Get-Noise 0.4); $az = 2.4 + (Get-Noise 0.5)
        $gx = 85.0 + (Get-Noise 10.0); $gy = -60.0 + (Get-Noise 10.0); $gz = 110.0 + (Get-Noise 15.0)
    } elseif ($t -lt $touchdownTime) {
        $descentTime = $t - ($apogeeTime + 3.0)
        $alt = [Math]::Max(0.2, $apogeeAlt - 4.5 + $descentTime * $descentSpeed + (Get-Noise 0.2))
        $lat += 0.000015 * $DT; $lon += 0.000018 * $DT
        $swing = [Math]::Sin(($t - $apogeeTime) * 1.8)
        $ax = $swing * 0.22 + (Get-Noise 0.04)
        $ay = [Math]::Cos(($t - $apogeeTime) * 1.8) * 0.20 + (Get-Noise 0.04)
        $az = 0.96 + (Get-Noise 0.03)
        $gx = $swing * 14.0 + (Get-Noise 2.0); $gy = [Math]::Cos(($t - $apogeeTime) * 1.8) * 12.0 + (Get-Noise 2.0); $gz = [Math]::Sin(($t - $apogeeTime) * 0.3) * 6.0 + (Get-Noise 1.0)
    } else {
        # Landed on ground
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 25.0 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.1)
    $hum = Clamp (55.0 + ($alt / 800.0) * 18.0 + (Get-Noise 0.4)) 10.0 95.0
    $vBat = Clamp ($vBat - 0.00035 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "01_nominal_sounding_flight.csv" $rows

# 2. 02_high_altitude_burst_1200m.csv (Full trajectory to Touchdown)
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.15
$padDuration = 15.0; $ascentSpeed = 5.5; $apogeeAlt = 1200.0; $apogeeTime = $padDuration + ($apogeeAlt / $ascentSpeed)
$descentSpeed = -7.5; $descentDuration = ($apogeeAlt / [Math]::Abs($descentSpeed)); $touchdownTime = $apogeeTime + 4.0 + $descentDuration; $totalTime = $touchdownTime + 25.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt $padDuration) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + ($t - $padDuration) * $ascentSpeed + (Get-Noise 0.2)
        $lat += 0.000010 * $DT; $lon += 0.000014 * $DT
        $az = 1.06 + (Get-Noise 0.03)
        $gx = [Math]::Sin($t * 0.4) * 6.0 + (Get-Noise 1.5); $gy = [Math]::Cos($t * 0.3) * 5.0 + (Get-Noise 1.5)
    } elseif ($t -lt ($apogeeTime + 4.0)) {
        $alt = $apogeeAlt - ($t - $apogeeTime) * 3.0
        $ax = 2.4 + (Get-Noise 0.5); $ay = -2.1 + (Get-Noise 0.5); $az = 3.8 + (Get-Noise 0.6)
        $gx = 120.0 + (Get-Noise 20.0); $gy = -95.0 + (Get-Noise 20.0); $gz = 140.0 + (Get-Noise 25.0)
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - ($apogeeTime + 4.0)
        $alt = [Math]::Max(0.2, $apogeeAlt - 12.0 + $dtDesc * $descentSpeed + (Get-Noise 0.2))
        $lat += 0.000022 * $DT; $lon += 0.000020 * $DT
        $ax = [Math]::Sin($t * 1.5) * 0.25 + (Get-Noise 0.05); $ay = [Math]::Cos($t * 1.5) * 0.22 + (Get-Noise 0.05); $az = 0.94 + (Get-Noise 0.04)
        $gx = [Math]::Sin($t * 1.5) * 16.0 + (Get-Noise 3.0); $gy = [Math]::Cos($t * 1.5) * 15.0 + (Get-Noise 3.0)
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 26.5 - ($alt / 1000.0) * 7.2 + (Get-Noise 0.06)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.1)
    $hum = Clamp (60.0 + ($alt / 1200.0) * 25.0 + (Get-Noise 0.5)) 10.0 98.0
    $vBat = Clamp ($vBat - 0.00038 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "02_high_altitude_burst_1200m.csv" $rows

# 3. 03_severe_wind_shear_drift.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.12
$totalTime = 300.0; $apogeeTime = 140.0; $apogeeAlt = 650.0; $touchdownTime = 265.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $shear = if ($alt -gt 300 -and $alt -lt 550) { 4.5 } else { 1.2 }
        $lat += (0.000025 * $shear) * $DT; $lon += (0.000035 * $shear) * $DT
        $ax = 0.35 * [Math]::Sin($t * 0.8) + (Get-Noise 0.05); $ay = 0.40 * [Math]::Cos($t * 0.6) + (Get-Noise 0.05); $gz = 25.0 * [Math]::Sin($t * 0.4) + (Get-Noise 3.0)
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - $apogeeTime
        $alt = [Math]::Max(0.2, $apogeeAlt - $dtDesc * 5.5 + (Get-Noise 0.2))
        $driftFactor = 3.8
        $lat += 0.000045 * $driftFactor * $DT * [Math]::Cos($t * 0.05)
        $lon += 0.000060 * $driftFactor * $DT * [Math]::Sin($t * 0.04)
        $ax = 0.45 * [Math]::Sin($t * 2.2) + (Get-Noise 0.08); $ay = 0.42 * [Math]::Cos($t * 1.9) + (Get-Noise 0.08); $az = 0.92 + (Get-Noise 0.05)
        $gx = 28.0 * [Math]::Sin($t * 2.2) + (Get-Noise 4.0); $gy = 25.0 * [Math]::Cos($t * 1.9) + (Get-Noise 4.0); $gz = 40.0 * [Math]::Sin($t * 0.8) + (Get-Noise 5.0)
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 24.0 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.12)
    $hum = Clamp (50.0 + ($alt / 650.0) * 20.0 + (Get-Noise 0.5)) 10.0 95.0
    $vBat = Clamp ($vBat - 0.00032 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "03_severe_wind_shear_drift.csv" $rows

# 4. 04_apogee_ejection_shock_tumble.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.10
$totalTime = 280.0; $apogeeTime = 130.0; $apogeeAlt = 600.0; $touchdownTime = 245.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.02 + (Get-Noise 0.02); $ay = 0.02 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $lat += 0.000010 * $DT; $lon += 0.000012 * $DT
    } elseif ($t -lt ($apogeeTime + 8.0)) {
        $shockDt = $t - $apogeeTime
        $alt = $apogeeAlt - $shockDt * 3.5
        $ax = 3.2 * [Math]::Sin($shockDt * 5.0) + (Get-Noise 0.4)
        $ay = -2.8 * [Math]::Cos($shockDt * 4.0) + (Get-Noise 0.4)
        $az = 4.1 + [Math]::Exp(-$shockDt * 0.5) * 1.1 + (Get-Noise 0.5)
        $gx = 175.0 * [Math]::Sin($shockDt * 6.0) + (Get-Noise 15.0)
        $gy = -165.0 * [Math]::Cos($shockDt * 5.0) + (Get-Noise 15.0)
        $gz = 190.0 * [Math]::Sin($shockDt * 4.0) + (Get-Noise 20.0)
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - ($apogeeTime + 8.0)
        $alt = [Math]::Max(0.2, $apogeeAlt - 28.0 - $dtDesc * 5.5 + (Get-Noise 0.2))
        $lat += 0.000018 * $DT; $lon += 0.000022 * $DT
        $ax = 0.2 * [Math]::Sin($t * 1.2) + (Get-Noise 0.04); $ay = 0.2 * [Math]::Cos($t * 1.2) + (Get-Noise 0.04); $az = 0.95 + (Get-Noise 0.03)
        $gx = 12.0 * [Math]::Sin($t * 1.2) + (Get-Noise 2.0); $gy = 10.0 * [Math]::Cos($t * 1.2) + (Get-Noise 2.0)
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 25.0 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.15)
    $hum = Clamp (52.0 + ($alt / 600.0) * 18.0 + (Get-Noise 0.4)) 10.0 95.0
    $vBat = Clamp ($vBat - 0.00034 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "04_apogee_ejection_shock_tumble.csv" $rows

# 5. 05_parachute_pendulum_resonance.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.14
$totalTime = 260.0; $apogeeTime = 110.0; $apogeeAlt = 500.0; $touchdownTime = 220.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $lat += 0.000008 * $DT; $lon += 0.000010 * $DT
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - $apogeeTime
        $alt = [Math]::Max(0.2, $apogeeAlt - $dtDesc * 5.0 + (Get-Noise 0.2))
        $lat += 0.000016 * $DT; $lon += 0.000018 * $DT
        $omega = 2.0 * [Math]::PI * 0.7
        $swingAngleRad = (18.0 * [Math]::PI / 180.0) * [Math]::Sin($dtDesc * $omega)
        $swingAngleRollRad = (16.0 * [Math]::PI / 180.0) * [Math]::Cos($dtDesc * $omega)
        $ax = -[Math]::Sin($swingAngleRollRad) + (Get-Noise 0.03)
        $ay = [Math]::Sin($swingAngleRad) + (Get-Noise 0.03)
        $az = [Math]::Cos($swingAngleRad) * [Math]::Cos($swingAngleRollRad) + (Get-Noise 0.03)
        $gx = (18.0 * $omega) * [Math]::Cos($dtDesc * $omega) + (Get-Noise 2.0)
        $gy = -(16.0 * $omega) * [Math]::Sin($dtDesc * $omega) + (Get-Noise 2.0)
        $gz = 8.0 * [Math]::Sin($dtDesc * 1.5) + (Get-Noise 1.5)
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 24.5 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.12)
    $hum = Clamp (54.0 + ($alt / 500.0) * 16.0 + (Get-Noise 0.4)) 10.0 95.0
    $vBat = Clamp ($vBat - 0.00035 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "05_parachute_pendulum_resonance.csv" $rows

# 6. 06_delayed_chute_deployment.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.15
$totalTime = 260.0; $apogeeTime = 110.0; $apogeeAlt = 650.0; $freefallDuration = 5.0; $touchdownTime = 225.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $lat += 0.000009 * $DT; $lon += 0.000011 * $DT
    } elseif ($t -lt ($apogeeTime + $freefallDuration)) {
        $dtFF = $t - $apogeeTime
        $alt = $apogeeAlt + 0.5 * (-9.81 * 0.85) * $dtFF * $dtFF
        $ax = (Get-Noise 0.08); $ay = (Get-Noise 0.08); $az = 0.05 + (Get-Noise 0.05)
        $gx = 45.0 * [Math]::Sin($dtFF * 2.0) + (Get-Noise 5.0)
        $gy = 40.0 * [Math]::Cos($dtFF * 2.0) + (Get-Noise 5.0)
        $gz = 60.0 * [Math]::Sin($dtFF * 3.0) + (Get-Noise 8.0)
    } elseif ($t -lt ($apogeeTime + $freefallDuration + 3.0)) {
        $dtSnatch = $t - ($apogeeTime + $freefallDuration)
        $ffEndAlt = $apogeeAlt - 90.0
        $alt = $ffEndAlt - $dtSnatch * 12.0
        $ax = -1.2 + (Get-Noise 0.3); $ay = 1.4 + (Get-Noise 0.3); $az = 4.8 + (Get-Noise 0.4)
        $gx = 80.0 + (Get-Noise 10.0); $gy = -70.0 + (Get-Noise 10.0); $gz = 90.0 + (Get-Noise 12.0)
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - ($apogeeTime + $freefallDuration + 3.0)
        $chuteStartAlt = $apogeeAlt - 126.0
        $alt = [Math]::Max(0.2, $chuteStartAlt - $dtDesc * 5.5 + (Get-Noise 0.2))
        $lat += 0.000015 * $DT; $lon += 0.000017 * $DT
        $ax = 0.15 * [Math]::Sin($t * 1.4) + (Get-Noise 0.03); $ay = 0.15 * [Math]::Cos($t * 1.4) + (Get-Noise 0.03); $az = 0.97 + (Get-Noise 0.02)
        $gx = 10.0 * [Math]::Sin($t * 1.4) + (Get-Noise 1.5); $gy = 9.0 * [Math]::Cos($t * 1.4) + (Get-Noise 1.5)
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 25.0 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.15)
    $hum = Clamp (52.0 + ($alt / 650.0) * 20.0 + (Get-Noise 0.4)) 10.0 95.0
    $vBat = Clamp ($vBat - 0.00035 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "06_delayed_chute_deployment.csv" $rows

# 7. 07_thermal_inversion_sounding.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.16
$totalTime = 320.0; $apogeeTime = 150.0; $apogeeAlt = 750.0; $touchdownTime = 285.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $lat += 0.000008 * $DT; $lon += 0.000010 * $DT
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - $apogeeTime
        $alt = [Math]::Max(0.2, $apogeeAlt - $dtDesc * 5.8 + (Get-Noise 0.2))
        $lat += 0.000014 * $DT; $lon += 0.000016 * $DT
        $ax = 0.12 * [Math]::Sin($t * 1.3) + (Get-Noise 0.03); $ay = 0.12 * [Math]::Cos($t * 1.3) + (Get-Noise 0.03); $az = 0.98 + (Get-Noise 0.02)
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $temp = 22.0
    if ($alt -lt 250.0) {
        $temp = 22.0 - ($alt / 250.0) * 2.0
    } elseif ($alt -le 450.0) {
        $temp = 20.0 + (($alt - 250.0) / 200.0) * 4.5
    } else {
        $temp = 24.5 - (($alt - 450.0) / 300.0) * 4.0
    }
    $temp += (Get-Noise 0.05)
    $hum = 60.0
    if ($alt -lt 250.0) {
        $hum = 85.0 - ($alt / 250.0) * 15.0
    } elseif ($alt -le 450.0) {
        $hum = 42.0 + (Get-Noise 2.0)
    } else {
        $hum = 75.0 + (Get-Noise 1.5)
    }
    $hum = Clamp $hum 10.0 98.0
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.1)
    $vBat = Clamp ($vBat - 0.00033 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "07_thermal_inversion_sounding.csv" $rows

# 8. 08_sensor_glitch_gps_recovery.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.15
$totalTime = 260.0; $apogeeTime = 120.0; $apogeeAlt = 600.0; $touchdownTime = 225.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $lat += 0.000009 * $DT; $lon += 0.000012 * $DT
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - $apogeeTime
        $alt = [Math]::Max(0.2, $apogeeAlt - $dtDesc * 6.0 + (Get-Noise 0.2))
        $lat += 0.000015 * $DT; $lon += 0.000018 * $DT
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $outLat = $lat; $outLon = $lon
    if ($t -ge 90.0 -and $t -le 140.0) {
        if ($t -ge 100.0 -and $t -le 125.0) {
            $outLat = 0.0; $outLon = 0.0
        } else {
            $outLat = $lat + (Get-Noise 0.005)
            $outLon = $lon + (Get-Noise 0.005)
        }
    }
    $temp = 25.0 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.12)
    $hum = Clamp (55.0 + ($alt / 600.0) * 18.0 + (Get-Noise 0.4)) 10.0 95.0
    $vBat = Clamp ($vBat - 0.00035 * $DT + (Get-Noise 0.001)) 3.4 4.2
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $outLat $outLon $hum $vBat))
}
Write-TestCaseCsv "08_sensor_glitch_gps_recovery.csv" $rows

# 9. 09_low_battery_voltage_sag.csv
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.5; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 3.65
$totalTime = 240.0; $apogeeTime = 110.0; $apogeeAlt = 500.0; $touchdownTime = 205.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.01 + (Get-Noise 0.02); $ay = 0.01 + (Get-Noise 0.02); $az = 0.99 + (Get-Noise 0.02)
    $gx = (Get-Noise 1.0); $gy = (Get-Noise 1.0); $gz = (Get-Noise 0.5)
    if ($t -lt 15.0) {
        $alt = 0.5 + (Get-Noise 0.05)
    } elseif ($t -lt $apogeeTime) {
        $alt = 0.5 + (($t - 15.0) / ($apogeeTime - 15.0)) * $apogeeAlt + (Get-Noise 0.2)
        $lat += 0.000008 * $DT; $lon += 0.000010 * $DT
    } elseif ($t -lt $touchdownTime) {
        $dtDesc = $t - $apogeeTime
        $alt = [Math]::Max(0.2, $apogeeAlt - $dtDesc * 5.5 + (Get-Noise 0.2))
        $lat += 0.000015 * $DT; $lon += 0.000017 * $DT
    } else {
        $alt = 0.2 + [Math]::Abs((Get-Noise 0.05))
        $ax = (Get-Noise 0.01); $ay = (Get-Noise 0.01); $az = 0.998 + (Get-Noise 0.008)
        $gx = (Get-Noise 0.2); $gy = (Get-Noise 0.2); $gz = (Get-Noise 0.2)
    }
    $rfBursts = if ([Math]::Sin($t * 1.5) -gt 0.8) { 0.08 } else { 0.0 }
    $vBat = Clamp (3.65 - ($t / $totalTime) * 0.32 - $rfBursts + (Get-Noise 0.005)) 3.25 4.20
    $temp = 25.0 - ($alt / 1000.0) * 6.5 + (Get-Noise 0.05)
    $press = (Get-BaroPressure $alt) + (Get-Noise 0.12)
    $hum = Clamp (52.0 + ($alt / 500.0) * 16.0 + (Get-Noise 0.4)) 10.0 95.0
    $rows.Add((Format-Row $t $temp $press $alt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "09_low_battery_voltage_sag.csv" $rows

# 10. 10_ground_pad_static_test.csv (Nominal pad test)
$rows = New-Object System.Collections.Generic.List[string]
$alt = 0.2; $lat = $HOME_LAT; $lon = $HOME_LON; $vBat = 4.19
$totalTime = 180.0
for ($t = 0.0; $t -le $totalTime; $t += $DT) {
    $ax = 0.005 + [Math]::Sin($t * 0.05) * 0.01 + (Get-Noise 0.008)
    $ay = -0.004 + [Math]::Cos($t * 0.04) * 0.01 + (Get-Noise 0.008)
    $az = 0.998 + (Get-Noise 0.006)
    $gx = 0.12 + (Get-Noise 0.25)
    $gy = -0.08 + (Get-Noise 0.25)
    $gz = 0.02 + (Get-Noise 0.15)
    $curAlt = $alt + (Get-Noise 0.08)
    $temp = 25.2 + [Math]::Sin($t * 0.02) * 0.4 + (Get-Noise 0.03)
    $press = 1013.25 + (Get-Noise 0.08)
    $hum = 58.5 + (Get-Noise 0.2)
    $vBat = Clamp ($vBat - 0.00015 * $DT + (Get-Noise 0.0008)) 3.9 4.2
    $rows.Add((Format-Row $t $temp $press $curAlt $gx $gy $gz $ax $ay $az $lat $lon $hum $vBat))
}
Write-TestCaseCsv "10_ground_pad_static_test.csv" $rows

Write-Host "All 10 test case CSV files generated successfully in $testCasesDir"
