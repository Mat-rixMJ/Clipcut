# ClipCut Backend Server Startup (PowerShell)
# Activates .venv and starts the FastAPI backend on port 8001

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           ClipCut Backend Server Startup Script             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if .venv exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "✗ Virtual environment not found at .venv\" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    py -3.12 -m venv .venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
    Write-Host ""
}

# Activate venv
Write-Host "1️⃣  Activating virtual environment (.venv)..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
Write-Host "   ✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Check and install dependencies if needed
Write-Host "2️⃣  Checking dependencies..." -ForegroundColor Yellow
if (Test-Path "backend\requirements.txt") {
    pip list | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Dependencies ready" -ForegroundColor Green
    }
}
Write-Host ""

# Create required directories (unified storage)
Write-Host "3️⃣  Setting up unified storage..." -ForegroundColor Yellow
@("data\videos", "data\audio", "data\renders", "data\artifacts", "data\transcripts", "data\heatmap", "db") | ForEach-Object {
    if (-not (Test-Path $_)) { 
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
        Write-Host "   ✓ Created: $_" -ForegroundColor Green
    }
}
Write-Host ""

# Set environment variables
Write-Host "4️⃣  Setting environment variables..." -ForegroundColor Yellow
$env:PYTHONPATH = "D:/clipcut/backend"
$env:DATABASE_URL = "sqlite:///D:/clipcut/db/app.db"
Write-Host "   ✓ PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Green
Write-Host "   ✓ DATABASE_URL=$env:DATABASE_URL" -ForegroundColor Green
Write-Host ""

# Start the backend
Write-Host "5️⃣  Starting FastAPI backend..." -ForegroundColor Yellow
Write-Host "   Press Ctrl+C to stop the server" -ForegroundColor Cyan
Write-Host ""

cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --log-level info

