# Run Depth Viewer with Virtual Environment
# This script automatically activates the venv and runs the depth viewer

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

Write-Host "Starting depth viewer..." -ForegroundColor Green
& $pythonExe depth_viewer_visual.py
