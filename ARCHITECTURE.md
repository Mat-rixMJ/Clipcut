# ClipCut System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ClipCut Pipeline                          │
└─────────────────────────────────────────────────────────────────┘

                         User Input
                             │
                             ▼
                    ┌────────────────┐
                    │  YouTube URL   │
                    └────────┬───────┘
                             │
                ┌────────────▼────────────┐
                │   POST /process-youtube │
                └────────────┬────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌────────┐          ┌────────┐         ┌─────────┐
    │Database│          │ Job    │         │Background│
    │ Video  │◄─────────│ Queue  │────────►│ Workers │
    │ Record │          └────────┘         └─────────┘
    └────────┘                                   │
         │                                       │
         │                                       │
         └───────────────┬───────────────────────┘
                         │
            ┌────────────▼───────────┐
            │  Pipeline Execution    │
            └────────────┬───────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         │               │               │               │
         ▼               ▼               ▼               ▼
    ┌────────┐     ┌─────────┐    ┌──────────┐   ┌──────────┐
    │Download│────►│ Ingest  │───►│ Analyze  │──►│ Generate │
    │  (1)   │     │   (2)   │    │   (3)    │   │   (4)    │
    └────────┘     └─────────┘    └──────────┘   └──────────┘
         │              │               │              │
         ▼              ▼               ▼              ▼
    ┌────────┐     ┌────────┐     ┌────────┐    ┌────────┐
    │ Video  │     │ Audio  │     │ Scores │    │ Clips  │
    │  File  │     │Extract │     │  1-10  │    │ Ready  │
    └────────┘     └────────┘     └────────┘    └────────┘
```

## Detailed Pipeline Stages

### Stage 1: Download (youtube_service.py)

```
Input: YouTube URL
Process:
  - Use yt-dlp to download video
  - Save to data/videos/
  - Extract video title
Output: Video file (.mp4)
```

### Stage 2: Ingest (ingest_service.py)

```
Input: Video file
Process:
  - Extract metadata (duration, FPS)
  - Extract audio to WAV (16kHz, mono)
  - Save to data/audio/
  - Store metadata in database
Output: Audio file + metadata
```

### Stage 3: Analyze (analysis_service.py)

```
Input: Video + Audio files
Process:
  - Analyze audio energy (loudness)
  - Detect scene changes
  - Calculate position scores
  - Combine into engagement scores (1-10)
  - Find best continuous segments (15-60s)
Output: Scored segments + clip candidates
```

### Stage 4: Generate Clips (clip_service.py)

```
Input: Video + clip timecodes
Process:
  - Extract segments using FFmpeg
  - Convert to vertical (9:16)
  - Optimize for social media
  - Save to data/artifacts/
Output: Ready-to-upload MP4 clips
```

## Engagement Scoring Formula

```
Engagement Score = Audio Score + Scene Score + Position Score
                   (0-4 points)   (0-3 points)   (0-3 points)

Total: 1-10 points

Audio Score:
  - Measures loudness/energy
  - Higher = more exciting
  - Normalized: -60dB to 0dB → 0-4 points

Scene Score:
  - Detects visual changes
  - Scene change within 2s = +3 points
  - No scene change = 0 points

Position Score:
  - Beginning/end favor
  - Middle gets lower score
  - Formula: (1 - |mid - duration/2| / (duration/2)) * 3
```

## Database Schema

```sql
-- Videos table
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    title TEXT,
    original_path TEXT NOT NULL,
    audio_path TEXT,
    source_url TEXT,              -- YouTube URL
    duration_seconds REAL,
    fps REAL,
    raw_metadata JSON,
    analysis_data JSON,           -- Engagement analysis
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Jobs table (background tasks)
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    video_id TEXT REFERENCES videos(id),
    job_type TEXT NOT NULL,       -- download, ingest, analysis, generate_clips
    status TEXT NOT NULL,          -- PENDING, RUNNING, SUCCESS, FAILED
    step TEXT,                     -- Current step
    progress REAL,                 -- 0.0 to 1.0
    error_message TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Clips table (generated shorts)
CREATE TABLE clips (
    id TEXT PRIMARY KEY,
    video_id TEXT REFERENCES videos(id),
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL,
    engagement_score REAL NOT NULL, -- 1-10
    rank INTEGER NOT NULL,           -- 1 = best clip
    output_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## API Endpoints

```
POST   /api/videos/process-youtube      - Full pipeline (recommended)
POST   /api/videos/youtube               - Download only
POST   /api/videos/{id}/ingest           - Ingest only
POST   /api/videos/{id}/analyze          - Analyze only
POST   /api/videos/{id}/generate-clips   - Generate only

GET    /api/videos/{id}                  - Get video + jobs + clips
GET    /api/videos/{id}/clips            - List all clips
GET    /api/videos/clips/{id}/download   - Download clip file

GET    /health                           - Health check
GET    /docs                             - API documentation
```

## File Structure

```
clipcut/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app
│   │   ├── api/
│   │   │   └── videos.py                # API endpoints
│   │   ├── core/
│   │   │   ├── config.py                # Configuration
│   │   │   └── db.py                    # Database
│   │   ├── models/
│   │   │   ├── db_models.py             # SQLAlchemy models
│   │   │   └── schemas.py               # Pydantic schemas
│   │   └── services/
│   │       ├── youtube_service.py       # Stage 1: Download
│   │       ├── ingest_service.py        # Stage 2: Ingest
│   │       ├── analysis_service.py      # Stage 3: Analyze
│   │       └── clip_service.py          # Stage 4: Generate
│   ├── data/
│   │   ├── videos/                      # Downloaded videos
│   │   ├── audio/                       # Extracted audio
│   │   └── artifacts/                   # Generated clips
│   ├── db/
│   │   └── app.db                       # SQLite database
│   └── requirements.txt
├── scripts/
│   ├── test_pipeline.py                 # Test script
│   └── check_requirements.py            # System check
├── start_server.bat                     # Windows startup
└── README.md
```

## Technology Stack

- **Web Framework**: FastAPI (async Python)
- **Database**: SQLAlchemy + SQLite
- **Video Download**: yt-dlp
- **Video Processing**: FFmpeg
- **Job Queue**: Background tasks with FastAPI
- **API Docs**: Swagger UI (built-in)

## Future Enhancements

1. **AI Captions**: Speech-to-text with auto-captions
2. **Face Detection**: Smart cropping to keep faces centered
3. **Music Sync**: Cut clips on beat/rhythm
4. **Multi-format**: Support for square (1:1) and horizontal
5. **Batch Processing**: Process multiple videos
6. **Cloud Storage**: S3/Azure integration
7. **Queue System**: Redis + Celery for scaling
8. **ML Models**: Train on successful shorts for better predictions
