# Run Hand Tracking Sprint 2 with MediaPipe detection
# Enhanced performance monitoring and real-time calibration

$venvPath = ""
if (Test-Path ".\.venv311\Scripts\Activate.ps1") {
    $venvPath = ".\.venv311\Scripts\Activate.ps1"
} elseif (Test-Path ".\.venv\Scripts\Activate.ps1") {
    $venvPath = ".\.venv\Scripts\Activate.ps1"
} else {
    throw "No virtual environment found. Expected .venv311 or .venv."
}

$pythonExe = Join-Path (Split-Path $venvPath) "python.exe"

Write-Host "Using Python interpreter: $pythonExe" -ForegroundColor Cyan

Write-Host ""
Write-Host "Starting Hand Tracking Sprint 2 with MediaPipe Detection..." -ForegroundColor Green
Write-Host ""
Write-Host "Sprint 2 Features:" -ForegroundColor Yellow
Write-Host "  - MediaPipe hand detection with 21 landmarks"
Write-Host "  - Performance profiling with FPS monitoring"
Write-Host "  - Real-time calibration controls"
Write-Host "  - Configuration persistence"
Write-Host "  - Optimized rendering with caching"
Write-Host ""
Write-Host "4 Windows will open:" -ForegroundColor Yellow
Write-Host "  1. RGB Camera - Live feed with MediaPipe hand detection box"
Write-Host "  2. Depth Map - Colorized depth visualization"
Write-Host "  3. Hand Region - Zoomed view of detected hand"
Write-Host "  4. 5x5 Matrix - Large depth matrix with performance stats"
Write-Host ""
Write-Host "Controls:" -ForegroundColor Yellow
Write-Host "  q - Quit"
Write-Host "  s - Toggle UDP on/off"
Write-Host "  c - Auto-calibrate depth range"
Write-Host "  r - Reset to defaults"
Write-Host "  + / = - Increase max depth"
Write-Host "  - / _ - Decrease max depth"
Write-Host "  [ - Decrease min depth"
Write-Host "  ] - Increase min depth"
Write-Host "  p - Save calibration to config"
Write-Host ""

& $pythonExe hand_tracking_sprint2.py
