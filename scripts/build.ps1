# Build Server Studio into a standalone Windows app folder.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\build.ps1
$ErrorActionPreference = "Stop"

Write-Host "Installing build dependencies..."
python -m pip install -e ".[dev,build]"

Write-Host "Running PyInstaller..."
python -m PyInstaller --noconfirm server-studio.spec

Write-Host ""
Write-Host "Done. App built at: dist\ServerStudio\ServerStudio.exe"
Write-Host "Tip: drop a 'bore.exe' into a 'vendor\' folder before building to bundle the"
Write-Host "internet-tunnel binary; otherwise install 'bore' separately for that feature."
