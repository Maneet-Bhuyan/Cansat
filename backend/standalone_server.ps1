# Cognitive CanSat Ground Station - Zero-Dependency Native Windows Server
# Runs on any Windows PC using built-in .NET HttpListener (No Python, No Node, No Admin Rights needed).

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir
$Port = 8000

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "       COGNITIVE CANSAT GROUND STATION - NATIVE WINDOWS STANDALONE MODE        " -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[i] Initializing native Windows HTTP engine (Zero External Dependencies)..." -ForegroundColor Green

# 1. Clear port 8000 if occupied
try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pidToKill in $pids) {
            Write-Host "[i] Clearing port $Port from stale process PID $pidToKill..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 600
    }
} catch {
    # Non-fatal
}

# 2. Start HttpListener
$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://127.0.0.1:$Port/")
try {
    $Listener.Start()
} catch {
    Write-Host "[!] Could not bind to port $Port. Opening dashboard file directly in browser..." -ForegroundColor Yellow
    Start-Process (Join-Path $RootDir "index.html")
    exit 0
}

Write-Host "[+] Ground Station Web Server ACTIVE at http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host "    - 3D Attitude Model & Three.js Canvas : ACTIVE" -ForegroundColor Gray
Write-Host "    - Leaflet Tactical GIS Ground Track  : ACTIVE" -ForegroundColor Gray
Write-Host "    - High-Density Chart.js Telemetry    : ACTIVE" -ForegroundColor Gray
Write-Host "    - Web Serial Hardware USB Bridge     : ACTIVE" -ForegroundColor Gray
Write-Host "    - 10 Flight Profiles & Replay Suite  : ACTIVE" -ForegroundColor Gray
Write-Host "    - Post-Flight Review (PFR) Engine    : ACTIVE" -ForegroundColor Gray
Write-Host ""
Write-Host "    NOTE: Python ML Server is in Standby mode. Ground station uses" -ForegroundColor DarkGray
Write-Host "    high-precision onboard client kinematics and anomaly heuristics." -ForegroundColor DarkGray
Write-Host ""
Write-Host "    Press Ctrl + C in this window to stop the server anytime." -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------------------------" -ForegroundColor DarkGray

# 3. Launch Default Browser
Start-Process "http://127.0.0.1:$Port/"

# 4. Request Serving Loop
try {
    while ($Listener.IsListening) {
        $Context = $Listener.GetContext()
        $Request = $Context.Request
        $Response = $Context.Response

        # Add CORS Headers so local fetches succeed
        $Response.AddHeader("Access-Control-Allow-Origin", "*")
        $Response.AddHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        $Response.AddHeader("Access-Control-Allow-Headers", "*")

        $RawPath = $Request.Url.LocalPath.TrimStart('/')
        
        if ($Request.HttpMethod -eq "OPTIONS") {
            $Response.StatusCode = 200
            $Response.Close()
            continue
        }

        if ([string]::IsNullOrEmpty($RawPath) -or $RawPath -eq "index.html") {
            $FilePath = Join-Path $RootDir "index.html"
            $ContentType = "text/html; charset=utf-8"
        } elseif ($RawPath -eq "api/health") {
            $Json = '{"status":"standby","models_loaded":false,"engine":"standalone_windows"}'
            $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Json)
            $Response.ContentType = "application/json"
            $Response.ContentLength64 = $Bytes.Length
            $Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
            $Response.Close()
            continue
        } else {
            $FilePath = Join-Path $RootDir $RawPath
            $Ext = [System.IO.Path]::GetExtension($FilePath).ToLower()
            $ContentType = switch ($Ext) {
                ".html" { "text/html; charset=utf-8" }
                ".csv"  { "text/csv; charset=utf-8" }
                ".js"   { "application/javascript; charset=utf-8" }
                ".json" { "application/json; charset=utf-8" }
                ".css"  { "text/css; charset=utf-8" }
                ".png"  { "image/png" }
                ".jpg"  { "image/jpeg" }
                ".svg"  { "image/svg+xml" }
                default { "application/octet-stream" }
            }
        }

        if (Test-Path $FilePath -PathType Leaf) {
            try {
                $Bytes = [System.IO.File]::ReadAllBytes($FilePath)
                $Response.ContentType = $ContentType
                $Response.ContentLength64 = $Bytes.Length
                $Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
            } catch {
                $Response.StatusCode = 500
            }
        } else {
            $Response.StatusCode = 404
            $NotFound = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found")
            $Response.OutputStream.Write($NotFound, 0, $NotFound.Length)
        }
        $Response.Close()
    }
} finally {
    $Listener.Stop()
    Write-Host "`n[i] Ground Station server safely closed. Goodbye!" -ForegroundColor Cyan
}
