# ClipCut Backend Server Startup (PowerShell)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "   ClipCut Backend Server" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    py -3.12 -m venv .venv
    Write-Host ""
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
Write-Host ""

# Create directories
@("backend\data\videos", "backend\data\audio", "backend\data\artifacts", "backend\db") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host "Server: http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

# Run server from backend directory with .venv Python
Push-Location backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
