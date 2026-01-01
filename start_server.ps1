# ClipCut Backend Server Startup (Simplified)
Write-Host "Starting ClipCut Backend Server..."

# Check if .venv exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found. Creating..."
    py -3.12 -m venv .venv
}

# Activate venv
Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Create required directories (Clean on start)
Write-Host "Setting up storage (Clearing previous data)..."
if (Test-Path "data") { Remove-Item -Path "data" -Recurse -Force }
if (Test-Path "db") { Remove-Item -Path "db" -Recurse -Force }

@("data/videos", "data/audio", "data/renders", "data/artifacts", "data/transcripts", "data/heatmap", "db") | ForEach-Object {
    if (-not (Test-Path $_)) { 
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Set environment variables
$env:PYTHONPATH = "D:/clipcut/backend"
$env:DATABASE_URL = "sqlite:///D:/clipcut/db/app.db"

# Start the backend
Write-Host "Starting FastAPI backend on port 8001..."
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --log-level info
