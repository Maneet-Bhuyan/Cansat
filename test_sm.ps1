# Test script to verify state machine transitions across all 10 test case files
$testCasesDir = "E:\Cansat\test_cases"

function Test-FlightStateMachine([string]$csvPath) {
    $lines = [System.IO.File]::ReadAllLines($csvPath)
    $dataLines = $lines | Select-Object -Skip 1
    
    $currentPhase = "PAD_IDLE"
    $apogee = 0.0
    $padBaselineAlt = 0.0
    $padRecorded = $false
    $previousAlt = $null
    $previousTs = $null
    
    $phasesSeen = New-Object System.Collections.Generic.HashSet[string]
    $phasesSeen.Add("PAD_IDLE") | Out-Null
    
    foreach ($line in $dataLines) {
        $parts = $line.Trim().Split(',')
        if ($parts.Length -lt 14) { continue }
        
        $alt = [double]::Parse($parts[3])
        $ax = [double]::Parse($parts[7])
        $ay = [double]::Parse($parts[8])
        $az = [double]::Parse($parts[9])
        $accelMag = [Math]::Sqrt($ax*$ax + $ay*$ay + $az*$az)
        
        if ($alt -gt $apogee) { $apogee = $alt }
        if (-not $padRecorded -and $alt -gt 0) {
            $padBaselineAlt = $alt
            $padRecorded = $true
        }
        
        $vSpd = 0.0
        if ($previousAlt -ne $null) {
            $vSpd = ($alt - $previousAlt) / 0.8
        }
        $previousAlt = $alt
        
        # State Machine Logic
        if ($currentPhase -eq "PAD_IDLE") {
            if ($alt -gt ($padBaselineAlt + 8.0) -and $vSpd -gt 1.0) {
                $currentPhase = "BALLOON_ASCENT"
            }
        } elseif ($currentPhase -eq "BALLOON_ASCENT") {
            if ($apogee -gt ($padBaselineAlt + 40.0)) {
                if (($alt -lt ($apogee - 2.5)) -or ($vSpd -le 0.2 -and $alt -gt ($apogee - 10.0)) -or ($accelMag -gt 2.2)) {
                    $currentPhase = "APOGEE_BURST"
                }
            }
        } elseif ($currentPhase -eq "APOGEE_BURST") {
            if ($vSpd -lt -2.0) {
                $currentPhase = "PARACHUTE_DESCENT"
            }
        } elseif ($currentPhase -eq "PARACHUTE_DESCENT") {
            if ($alt -le ($padBaselineAlt + 3.0) -and [Math]::Abs($vSpd) -lt 1.5) {
                $currentPhase = "TOUCHDOWN_RECOVERY"
            }
        }
        
        $phasesSeen.Add($currentPhase) | Out-Null
    }
    
    return [PSCustomObject]@{
        File = [System.IO.Path]::GetFileName($csvPath)
        Phases = ($phasesSeen -join " -> ")
        All5Phases = ($phasesSeen.Contains("PAD_IDLE") -and $phasesSeen.Contains("BALLOON_ASCENT") -and $phasesSeen.Contains("APOGEE_BURST") -and $phasesSeen.Contains("PARACHUTE_DESCENT") -and $phasesSeen.Contains("TOUCHDOWN_RECOVERY"))
    }
}

Get-ChildItem -Path $testCasesDir -Filter "*.csv" | ForEach-Object {
    $res = Test-FlightStateMachine $_.FullName
    Write-Host "$($res.File): $($res.Phases) | All5: $($res.All5Phases)"
}
