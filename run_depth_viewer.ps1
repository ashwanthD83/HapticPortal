# Run Depth Viewer with Virtual Environment
# This script automatically activates the venv and runs the depth viewer

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
.\.venv\Scripts\Activate.ps1

Write-Host "Starting depth viewer..." -ForegroundColor Green
python depth_viewer_visual.py

Write-Host "`nDeactivating virtual environment..." -ForegroundColor Cyan
deactivate
