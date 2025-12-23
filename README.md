# ClipCut Backend

End-to-end pipeline for turning long-form videos (YouTube URL or local upload) into short, vertical clips suitable for Shorts/Reels/TikTok. The pipeline covers: download → ingest → transcription → analysis/scoring → clip selection → rendering.

---

## Features

- Unified pipeline for YouTube or local uploads
- Idempotent, retry-capable stages (safe to re-run)
- FastAPI API with job tracking and clip downloading
- Web UI with live progress bars, GPU/CPU toggle, stop control, clip settings (duration/score/quality/codec), and YouTube download quality selector (capped at 1080p)
- SQLite via SQLAlchemy ORM
- GPU acceleration (optional): Whisper CUDA + FFmpeg NVDEC/D3D11VA
- Robust monitoring: adaptive progress script with stage timings
- Per-video clip folders with consistent naming
- Hard 1080p ceiling for downloads and rendered clips (inputs can be higher; outputs and downloads are clamped to 1080p)

## Architecture

- API: FastAPI (server in `backend/app/main.py`)
- Services: `backend/app/services/*` (download, ingest, transcription, analysis, clip)
- Models: SQLAlchemy + Pydantic (`backend/app/models/*`)
- Config: `backend/app/core/config.py` (env + directories)
- Data layout: relative to server working directory
  - `backend/data/videos` (original downloads/uploads)
  - `backend/data/audio` (extracted audio)
  - `backend/data/renders/{video_id}` (final clips)
  - `backend/data/transcripts` (optional)
- Logs: `D:\clipcut\pipeline.log`

---

## Prerequisites

- Windows (PowerShell)
- Python 3.12 (recommended)
- FFmpeg + FFprobe installed and in PATH (required)
- Optional (GPU): NVIDIA drivers + CUDA-capable FFmpeg, CUDA-enabled PyTorch

Check FFmpeg:

```powershell
ffmpeg -version
ffprobe -version
```

---

## Setup (One-Time)

Create and activate a virtual environment:

```powershell
cd D:\clipcut
python -m venv .venv
& .venv\Scripts\Activate.ps1
```

Install packages:

```powershell
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings requests yt-dlp openai-whisper
```

If using GPU for Whisper (NVIDIA):

```powershell
pip uninstall -y torch torchvision torchaudio
& .venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## Configuration

Environment variables (set before starting the server):

```powershell
# Required
$env:PYTHONPATH = "D:/clipcut/backend"
$env:DATABASE_URL = "sqlite:///D:/clipcut/db/app.db"

# Optional GPU
$env:WHISPER_DEVICE = "cuda"      # or "cpu"
$env:FFMPEG_HWACCEL = "cuda"      # or "d3d11va", "dxva2", "qsv", "" (none)
```

Note on paths:

- The server runs from `D:/clipcut/backend` and uses the working directory-relative `data/` folder under `backend/`.
- Final clips are saved under `backend/data/renders/{video_id}`.

---

## Run the Backend + Frontend

```powershell
cd D:/clipcut
& .venv\Scripts\Activate.ps1

# Optional: set env vars (adjust GPU/DB as needed)
$env:PYTHONPATH = "D:/clipcut/backend"
$env:DATABASE_URL = "sqlite:///D:/clipcut/db/app.db"
$env:WHISPER_DEVICE = "cuda"      # or "cpu"
$env:FFMPEG_HWACCEL = "cuda"      # or "d3d11va"/"dxva2"/"qsv"/""

cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Frontend: open http://127.0.0.1:8000/ (served from `index.html`).
- Health: http://127.0.0.1:8000/health

---

## Web UI

- Progress: live job progress bars with per-stage status and inline clip previews/downloads.
- Controls: GPU/CPU preference toggle (sent as `X-Prefer-GPU`), Stop Pipeline button, and YouTube download kickoff.
- Clip settings card (defaults shown in UI):
  - Min/Max clip duration (s): default 20–60
  - Min engagement score (1–10): default 7; adaptive fallback still applies downstream
  - Output quality: 480p / 720p / 1080p (clamped to 1080p)
  - Output codec: h264 / h265 / av1 / vp9
  - YouTube download quality: 480p / 720p / 1080p (downloads are capped at 1080p)
- Polling: the page auto-polls status every few seconds; paste any `video_id` to resume tracking.

---

## Clip Settings & Quality Caps

- All requested qualities above 1080p are clamped to 1080p for both downloads (yt-dlp) and rendered clips (FFmpeg).
- Defaults: `min_duration=20s`, `max_duration=60s`, `min_engagement_score=7`, `video_quality=1080p`, `video_format=h264`, `download_quality=1080p`.
- Supported qualities: 480p, 720p, 1080p. Supported codecs: h264, h265, av1, vp9 (UI defaults to h264 for compatibility).

---

## API Usage

Base URL: `http://127.0.0.1:8000/api`

- Start full pipeline (YouTube) with clip settings and download quality:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/youtube" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{
    "url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
    "title": "Optional title",
    "download_quality": "1080p",
    "min_duration": 20.0,
    "max_duration": 60.0,
    "min_engagement_score": 7,
    "video_quality": "1080p",
    "video_format": "h264"
  }'
```

- Notes on settings:
  - `download_quality`: 480p / 720p / 1080p; anything higher is clamped to 1080p.
  - `video_quality`: 480p / 720p / 1080p for rendered clips (capped at 1080p).
  - `video_format`: h264 / h265 / av1 / vp9; h264 is the safe default.
  - `min_duration`, `max_duration`, `min_engagement_score`: control clip selection thresholds.

- Upload and process local file:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos" `
  -Method POST `
  -InFile "C:\path\to\video.mp4" -ContentType "video/mp4"
```

- Check video + jobs status:

```powershell
$vid = "<video_id>"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/$vid"
```

- Stop a running pipeline (marks pending/running jobs as failed with a cancellation message):

```powershell
$vid = "<video_id>"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/$vid/stop" -Method POST
```

- List clips for a video:

```powershell
$vid = "<video_id>"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/$vid/clips"
```

- Download a clip:

```powershell
$clipId = "<clip_id>"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/clips/$clipId/download" -OutFile "clip.mp4"
```

---

## Monitoring

Adaptive monitoring script shows stage progress, timings, and clips:

```powershell
python scripts/monitor_pipeline.py <video_id>
```

- Status icons: ✓ SUCCESS, ⏳ RUNNING, ✗ FAILED, ○ PENDING
- Auto-sleeps 10s when running, 30s when idle
- Stops when clips are generated (or fails/timeout)

---

## GPU Acceleration (Optional)

- Whisper (CUDA): Set `$env:WHISPER_DEVICE = "cuda"` (requires CUDA-enabled PyTorch)
- FFmpeg (NVDEC/D3D11VA): Set `$env:FFMPEG_HWACCEL = "cuda"` (NVIDIA) or `"d3d11va"` (Windows universal)

Verify GPU setup:

```powershell
python scripts/check_gpu_setup.py
```

Quick CUDA test:

```powershell
& .venv\Scripts\python.exe scripts/test_cuda.py
```

Recommended configurations:

- NVIDIA: `WHISPER_DEVICE=cuda` + `FFMPEG_HWACCEL=cuda`
- Any Windows GPU: `WHISPER_DEVICE=cuda` (if NVIDIA) + `FFMPEG_HWACCEL=d3d11va`
- CPU-only: `WHISPER_DEVICE=cpu`, leave `FFMPEG_HWACCEL` empty

---

## Outputs

- Clips are saved under:
  - `backend/data/renders/{video_id}/clip_{rank}_{clip_id}.mp4`
- Example:
  - `D:\clipcut\backend\data\renders\30577f2b-1f70-4d62-aef2-e9573fe3f4fa\clip_1_XXXX.mp4`

Open clips folder:

```powershell
ii D:\clipcut\backend\data\renders\<video_id>
```

---

## Troubleshooting

- No clips generated: threshold adapts (7→5→3→1); re-run analysis if needed.
- Stuck stages: check `D:\clipcut\pipeline.log` for errors.
- Paths confusion: always start server from `D:/clipcut/backend` so `data/` resolves correctly.
- GPU issues:
  - Whisper CUDA false: reinstall PyTorch with CUDA 11.8 or 12.1 wheels.
  - FFmpeg fails: switch to `FFMPEG_HWACCEL=d3d11va` on Windows.
- DB location: ensure `D:/clipcut/db/app.db` directory exists.

---

## Project Structure

```
backend/
  app/
    main.py
    api/videos.py
    core/config.py, db.py
    models/db_models.py, schemas.py
    services/
      ingest_service.py
      transcription_service.py
      analysis_service.py
      clip_service.py
  data/
    videos/ audio/ renders/ transcripts/
scripts/
  monitor_pipeline.py
  check_gpu_setup.py
  test_cuda.py
```

---

## Quick Start (GPU)

```powershell
# 1) Activate venv
cd D:\clipcut
& .venv\Scripts\Activate.ps1

# 2) Set env vars
$env:PYTHONPATH = "D:/clipcut/backend"
$env:DATABASE_URL = "sqlite:///D:/clipcut/db/app.db"
$env:WHISPER_DEVICE = "cuda"
$env:FFMPEG_HWACCEL = "cuda"

# 3) Start server
cd D:/clipcut/backend
& ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 4) Kick off a YouTube video with clip settings and quality caps
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/videos/youtube" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"url":"https://www.youtube.com/watch?v=YOUR_VIDEO_ID","download_quality":"1080p","video_quality":"1080p","video_format":"h264","min_duration":20,"max_duration":60,"min_engagement_score":7}'

# 5) Monitor
python ..\scripts\monitor_pipeline.py <video_id>
```

---

## License

Internal project; no license header added.
