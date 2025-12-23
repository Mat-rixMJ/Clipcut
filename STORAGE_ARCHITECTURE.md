# ClipCut Unified Storage Architecture

## 📁 Single Source of Truth: `D:\clipcut\data\`

All media files, metadata, and temporary storage is **centralized in one location** to eliminate confusion and simplify maintenance.

---

## Directory Structure

```
D:\clipcut\data\
├── videos/               # ✅ INPUT: Original videos (uploaded or downloaded)
│   ├── abc123.mp4       # YouTube download
│   ├── def456.mp4       # User upload
│   └── ...
│
├── audio/               # ✅ INTERMEDIATE: Extracted audio from videos
│   ├── abc123.wav       # Audio from video abc123
│   ├── def456.wav       # Audio from video def456
│   └── ...
│
├── renders/             # ✅ OUTPUT: Final rendered clips (organized by video)
│   ├── abc123/          # Clips from video abc123
│   │   ├── clip_1_[id].mp4
│   │   ├── clip_2_[id].mp4
│   │   └── clip_5_[id].mp4
│   ├── def456/          # Clips from video def456
│   │   ├── clip_1_[id].mp4
│   │   └── ...
│   └── ...
│
├── transcripts/         # 📝 METADATA: Transcription results
│   ├── abc123.json      # Transcript segments for video abc123
│   ├── def456.json
│   └── ...
│
├── heatmap/             # 📊 METADATA: Engagement scores
│   ├── abc123.json      # Engagement heatmap for video abc123
│   ├── def456.json
│   └── ...
│
└── artifacts/           # 🗑️ TEMPORARY: Legacy/cleanup-safe files
    ├── old_render_*.mp4
    └── ...
```

---

## Path Resolution: Where Each Step Stores Data

### 1. **YouTube Download / File Upload** → `videos/`

- **When**: User submits YouTube URL or uploads file
- **Code**: `youtube_service.py` + `ingest_service.py`
- **Path**: `D:\clipcut\data\videos\{video_id}.mp4`
- **Status**: Ready for processing

### 2. **Audio Extraction** → `audio/`

- **When**: Ingest job runs (extracts audio from video for transcription)
- **Code**: `ingest_service.py::_extract_audio()`
- **Path**: `D:\clipcut\data\audio\{video_id}.wav`
- **Status**: Ready for transcription

### 3. **Transcription** → Database (metadata in `transcripts/` if exported)

- **When**: Transcription job runs (Whisper processes audio)
- **Code**: `transcription_service.py::process_transcription_job()`
- **Path**: Stored in DB `video.analysis_data["transcript"]`
- **Optional Export**: `D:\clipcut\data\transcripts\{video_id}.json`

### 4. **Analysis (Scene Detection, Engagement Scoring)** → Database

- **When**: Analysis job runs (FFmpeg + audio energy analysis)
- **Code**: `analysis_service.py::process_analysis_job()`
- **Path**: Stored in DB `video.analysis_data["heatmap"]`
- **Optional Export**: `D:\clipcut\data\heatmap\{video_id}.json`

### 5. **Clip Rendering** → `renders/{video_id}/`

- **When**: Clip job runs (FFmpeg renders 9:16 vertical clips)
- **Code**: `clip_service.py::process_clip_job()`
- **Path**: `D:\clipcut\data\renders\{video_id}\clip_{rank}_{clip_id}.mp4`
- **Status**: Ready for download/playback

---

## Usage in Code

### ✅ **Correct Way (Use StoragePaths)**

```python
from app.core.config import StoragePaths

# Get videos directory
video_dir = StoragePaths.videos_dir()  # D:\clipcut\data\videos

# Get clips directory for specific video
clips_dir = StoragePaths.renders_dir(video_id="abc123")  # D:\clipcut\data\renders\abc123

# Get all directories
all_dirs = StoragePaths.all_dirs()  # dict of all storage paths
```

### ❌ **Wrong Way (Hardcoded or scattered)**

```python
# BAD: Hardcoded paths that might be inconsistent
video_path = "D:\clipcut\backend\data\videos\..."
render_path = "C:\temp\renders\..."
audio_path = "D:\clipcut\videos\audio\..."

# Creates confusion and maintenance nightmare
```

---

## Database Storage

Metadata (transcripts, heatmaps, engagement scores) are stored primarily in the **database**:

- `video.analysis_data` (JSON field)
  - Contains: `transcript`, `transcript_language`, `segments`, `scene_changes`, `best_clips`, `heatmap`

The `transcripts/` and `heatmap/` directories are **optional** for exports/backups.

---

## Storage Paths: Quick Reference

| **Use Case**                 | **Location**                          | **Via Code**                         |
| ---------------------------- | ------------------------------------- | ------------------------------------ |
| Original videos (YT, upload) | `D:\clipcut\data\videos\`             | `StoragePaths.videos_dir()`          |
| Extracted audio              | `D:\clipcut\data\audio\`              | `StoragePaths.audio_dir()`           |
| Rendered clips               | `D:\clipcut\data\renders\{video_id}\` | `StoragePaths.renders_dir(video_id)` |
| Transcripts (export)         | `D:\clipcut\data\transcripts\`        | `StoragePaths.transcripts_dir()`     |
| Heatmap (export)             | `D:\clipcut\data\heatmap\`            | `StoragePaths.heatmap_dir()`         |
| Temporary files              | `D:\clipcut\data\artifacts\`          | `StoragePaths.artifacts_dir()`       |

---

## Migration Checklist

If you have files scattered in different locations:

1. **Consolidate videos**: Move all `.mp4` files → `D:\clipcut\data\videos\`
2. **Consolidate audio**: Move all `.wav` files → `D:\clipcut\data\audio\`
3. **Consolidate clips**: Move all rendered clips → `D:\clipcut\data\renders\{video_id}\`
4. **Update database**: Re-run ingest for new videos or manually update paths in `clip.output_path`
5. **Delete backend/data** (if it exists): No longer needed

Command to migrate (PowerShell):

```powershell
# Move any videos from other locations to unified storage
Move-Item -Path "backend\data\videos\*" -Destination "data\videos\" -ErrorAction SilentlyContinue
Move-Item -Path "backend\data\audio\*" -Destination "data\audio\" -ErrorAction SilentlyContinue
Move-Item -Path "backend\data\renders\*" -Destination "data\renders\" -ErrorAction SilentlyContinue

# Clean up empty directories
Remove-Item -Path "backend\data" -Recurse -ErrorAction SilentlyContinue
```

---

## Benefits of Unified Storage

✅ **Single location** = no confusion about where files are  
✅ **Easy backups** = backup one folder (`D:\clipcut\data\`)  
✅ **Clear organization** = subdirectories by purpose (input/intermediate/output/metadata)  
✅ **Scalable** = videos organized by `{video_id}` for easy pagination  
✅ **Maintainable** = `StoragePaths` helper prevents hardcoded paths  
✅ **Database-aligned** = metadata stored in DB, raw files in `data/`

---

## Environment Setup

In your shell before running the server, ensure `data_dir` is pointing to the right location:

```bash
# .env file (optional)
DATA_DIR=D:\clipcut\data

# Or hardcoded in code (already default)
settings.data_dir = Path("D:\clipcut\data")
```

**Current Default**: `D:\clipcut\data` ✅
