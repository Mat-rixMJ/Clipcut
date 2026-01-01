# One-Click Setup for ClipCut
# Usage: Right-click -> Run with PowerShell

$ErrorActionPreference = "Stop"

function Write-Header($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host " [OK] $msg" -ForegroundColor Green }
function Write-ErrorMsg($msg) { Write-Host " [ERROR] $msg" -ForegroundColor Red }
function Write-Warn($msg) { Write-Host " [WARN] $msg" -ForegroundColor Yellow }

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              ClipCut - One Click Setup                       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# 1. Check Prerequisites
Write-Header "Checking Prerequisites"

# Check Python
try {
    $pyVersion = py --version 2>$null
    if (-not $pyVersion) { 
        $pyVersion = python --version 2>$null 
        if (-not $pyVersion) { throw "Python not found" }
        $pythonCmd = "python"
    } else {
        $pythonCmd = "py"
    }
    Write-Success "Python detected: $pyVersion"
} catch {
    Write-ErrorMsg "Python is not installed or not in PATH."
    Write-Host "Please install Python 3.10+ from python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check FFmpeg
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Success "FFmpeg detected"
} else {
    Write-ErrorMsg "FFmpeg not found in PATH!"
    Write-Host "FFmpeg is required for video processing."
    Write-Host "1. Download from https://gyan.dev/ffmpeg/builds/"
    Write-Host "2. Extract and add 'bin' folder to System PATH"
    Write-Warn "Setup will continue, but video processing will fail until installed."
    pause
}

# 2. Virtual Environment
Write-Header "Setting up Virtual Environment"
if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..."
    & $pythonCmd -m venv .venv
    Write-Success "Created virtual environment"
} else {
    Write-Success "Virtual environment already exists"
}

# 3. Install Dependencies
Write-Header "Installing Dependencies"
Write-Host "Upgrading pip..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null

if (Test-Path "backend\requirements.txt") {
    Write-Host "Installing requirements from backend\requirements.txt..."
    & .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    
    # Explicitly install critical tools if missed
    & .\.venv\Scripts\python.exe -m pip install yt-dlp openai-whisper
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Dependencies installed"
    } else {
        Write-ErrorMsg "Failed to install dependencies"
        pause
        exit 1
    }
} else {
    Write-ErrorMsg "backend\requirements.txt not found!"
    pause
    exit 1
}

# 4. Configuration
Write-Header "Configuration"
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success "Created .env from example"
    } else {
        # Create minimal .env
        $envContent = @"
# ClipCut Configuration
DATABASE_URL=sqlite:///db/app.db
LOG_LEVEL=INFO
# Add your API keys below
# OPENAI_API_KEY=
# GOOGLE_API_KEY=
"@
        Set-Content ".env" $envContent
        Write-Success "Created new .env file"
    }
} else {
    Write-Success ".env file exists"
}

# 5. Storage Setup
Write-Header "Setting up Storage"
$folders = @("data/videos", "data/audio", "data/renders", "data/artifacts", "data/transcripts", "data/heatmap", "db")
foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Success "Created $folder"
    }
}

# 6. YouTube Auth Check
Write-Header "YouTube Authentication"
if (Test-Path "token.pickle") {
    Write-Success "YouTube authentication token found"
} else {
    Write-Warn "YouTube token not found."
    if (Test-Path "backend\client_secrets.json") {
        $files = Get-ChildItem "backend" -Filter "client_secrets.json"
        if ($files) {
             # Move to root if needed or just use logic in setup_youtube_auth.py
             pass
        }
        
        $choice = Read-Host "Do you want to set up YouTube authentication now? (y/n)"
        if ($choice -eq 'y') {
            Write-Host "Running auth setup..."
            & .\.venv\Scripts\python.exe setup_youtube_auth.py
        }
    } else {
        Write-Warn "backend\client_secrets.json not found. YouTube upload will not work."
        Write-Host "To enable YouTube uploads:"
        Write-Host "1. Download OAuth 2.0 credentials JSON from Google Cloud Console"
        Write-Host "2. Save as 'backend/client_secrets.json'"
        Write-Host "3. Run 'setup_youtube_auth.py'"
    }
}

Write-Header "Setup Complete!"
Write-Host "To start the server, run: .\start_server.ps1" -ForegroundColor Green
Write-Host ""
pause
