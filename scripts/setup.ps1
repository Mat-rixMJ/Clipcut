# One-click setup for ClipCut (Windows)
param(
  [string]$PythonExe = "python",
  [string]$CudaFlavor = "cu118"  # options: cu118, cu121, cpu
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERR ] $msg" -ForegroundColor Red }

# 1) Verify Python
Write-Info "Checking Python..."
$pyVersion = & $PythonExe --version 2>$null
if (-not $pyVersion) { Write-Err "Python not found. Install Python 3.11+ and re-run."; exit 1 }
Write-Ok "Python detected: $pyVersion"

# 2) Create venv
if (-not (Test-Path ".venv")) {
  Write-Info "Creating venv..."
  & $PythonExe -m venv .venv
}
$venvPy = Join-Path ".venv" "Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Err "venv missing. Abort."; exit 1 }
Write-Ok "venv ready"

# 3) Activate venv for this session
& ".\.venv\Scripts\Activate.ps1"

# 4) Ensure winget/choco available for FFmpeg fallback
$hasWinget = (Get-Command winget -ErrorAction SilentlyContinue) -ne $null
$hasChoco = (Get-Command choco -ErrorAction SilentlyContinue) -ne $null

# 5) Ensure FFmpeg/FFprobe
function Ensure-FFmpeg {
  if ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -and (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Ok "FFmpeg/FFprobe already installed"
    return
  }
  Write-Warn "FFmpeg/FFprobe not found, installing..."
  if ($hasWinget) {
    winget install -e --id Gyan.FFmpeg --source winget --accept-package-agreements --accept-source-agreements
  } elseif ($hasChoco) {
    choco install ffmpeg --yes
  } else {
    Write-Err "Neither winget nor choco available. Install FFmpeg manually and re-run."
    exit 1
  }
  Write-Ok "FFmpeg/FFprobe installed"
}
Ensure-FFmpeg

# 6) Base Python deps
Write-Info "Installing base dependencies..."
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings requests yt-dlp openai-whisper

# 7) GPU detection & Torch install
$hasNvidiaSmi = (Get-Command nvidia-smi -ErrorAction SilentlyContinue) -ne $null
if ($hasNvidiaSmi) {
  Write-Info "NVIDIA GPU detected; installing Torch ($CudaFlavor)..."
  if ($CudaFlavor -eq "cu118") {
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  } elseif ($CudaFlavor -eq "cu121") {
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  } else {
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  }
  Write-Ok "Torch installed for GPU"
} else {
  Write-Warn "No NVIDIA GPU detected; installing CPU Torch..."
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
}

# 8) Env vars for this session
$env:PYTHONPATH = "D:/clipcut/backend"
$env:DATABASE_URL = "sqlite:///D:/clipcut/db/app.db"

# Persist to .env.local for reuse
@"
PYTHONPATH=D:/clipcut/backend
DATABASE_URL=sqlite:///D:/clipcut/db/app.db
WHISPER_DEVICE=cuda
FFMPEG_HWACCEL=cuda
"@ | Out-File -Encoding ASCII -FilePath ".env.local"

Write-Ok "Wrote .env.local"

# 9) Quick import check
Write-Info "Running import check..."
& $venvPy - <<'PYCODE'
import sys
mods = ["fastapi","uvicorn","sqlalchemy","pydantic","yt_dlp","whisper","torch"]
bad = []
for m in mods:
    try:
        __import__(m)
    except Exception as e:
        bad.append((m, str(e)))
if bad:
    print("Missing/broken:", bad); sys.exit(1)
print("All imports OK")
PYCODE

Write-Ok "Setup complete. Activate with: & .\\.venv\\Scripts\\Activate.ps1"
Write-Info "To start server: cd backend; $env:PYTHONPATH='D:/clipcut/backend'; $env:DATABASE_URL='sqlite:///D:/clipcut/db/app.db'; uvicorn app.main:app --host 127.0.0.1 --port 8000"
