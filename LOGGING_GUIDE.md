# Debugging & Logging Guide

## What Was Added

Comprehensive logging throughout the pipeline to diagnose failures:

### Transcription Service (`backend/app/services/transcription_service.py`)

- **[TRANSCRIPTION]** logs track:
  - Job startup and completion
  - Whisper model loading (device detection)
  - Audio file validation
  - Transcription progress (segments parsed)
  - Any exceptions with full stack trace

### Analysis Service (`backend/app/services/analysis_service.py`)

- **[ANALYSIS]** logs track:
  - Audio energy extraction per segment
  - Scene change detection via FFmpeg (with hwaccel status)
  - Engagement score calculation
  - LLM scoring (if enabled)
  - Clip generation and ranking
  - Database save operations
  - Any exceptions with full stack trace

## How to Monitor

Two log files record all activity:

1. **Pipeline Logs**: `D:/clipcut/pipeline.log`

   - Created by `backend/app/api/videos.py` in `_run_full_pipeline()`
   - Records pipeline orchestration (job transitions, retries)

2. **Server Logs**: `D:/clipcut/server.log`
   - Captures all Uvicorn + application logs
   - Shows [TRANSCRIPTION] and [ANALYSIS] debug messages

## Testing Steps

1. **Open Frontend**: http://127.0.0.1:8001
2. **Submit a Video**:
   - YouTube link (short video 2-5 min is faster), or
   - Upload a local video file
3. **Watch Live**:
   - Frontend shows job status in real-time
   - Open `D:/clipcut/pipeline.log` to see step transitions
   - Open `D:/clipcut/server.log` to see service-level details

## Example Log Flow

### Successful Transcription

```
[TRANSCRIPTION] Starting transcription job: abc123...
[TRANSCRIPTION] Processing video: xyz, title=My Video
[TRANSCRIPTION] No existing transcript, proceeding with transcription
[TRANSCRIPTION] Audio file exists: D:\clipcut\data\audio\xyz.wav, size=15728640 bytes
[TRANSCRIPTION] Calling _transcribe_audio()...
[TRANSCRIPTION] Loading Whisper model...
[TRANSCRIPTION] Loading model 'small' on device='cuda'
[TRANSCRIPTION] Whisper model loaded successfully
[TRANSCRIPTION] Transcribing with device='cuda', fp16=True
[TRANSCRIPTION] Transcription complete: 42 segments
[TRANSCRIPTION] Serializing 42 raw segments
[TRANSCRIPTION] Serialized 42 segments
[TRANSCRIPTION] Job SUCCESS: abc123...
```

### Successful Analysis

```
[ANALYSIS] Starting analysis job: def456...
[ANALYSIS] Processing video: xyz, title=My Video
[ANALYSIS] No existing clips or heatmap, proceeding with analysis
[ANALYSIS] Step 1: Analyzing audio energy...
[ANALYSIS] Extracted 125 audio segments
[ANALYSIS] Step 2: Detecting scene changes...
[ANALYSIS] Using hwaccel: cuda
[ANALYSIS] Detected 8 scene changes
[ANALYSIS] Step 3: Calculating engagement scores...
[ANALYSIS] Step 3 complete: 125 scored segments
[ANALYSIS] Step 4: Finding best clips...
[ANALYSIS] Step 4 complete: 5 best clips found
[ANALYSIS] Saving 5 clips to database...
[ANALYSIS] Job SUCCESS: def456...
```

## Troubleshooting

### If Transcription Hangs

- Check `D:/clipcut/server.log` for [TRANSCRIPTION] messages
- Look for error in `_load_whisper_model()` or `_transcribe_audio()`
- Common issues:
  - Whisper not installed: Install with `pip install openai-whisper`
  - Audio file missing: Check that ingest completed successfully
  - Device error (CUDA): Falls back to CPU automatically

### If Analysis Fails

- Check `D:/clipcut/server.log` for [ANALYSIS] messages
- Common failures at each step:
  1. Audio energy: FFmpeg not installed
  2. Scene detection: Video file missing or corrupted
  3. Scoring: LLM API unavailable (if enabled)
  4. Clip save: Database locked or permission issue

### If Pipeline Restarts

- Check `D:/clipcut/pipeline.log` for retry messages
- Logs will show: "attempt 1/2" → "attempt 2/2" if first attempt failed
- Each retry includes full [TRANSCRIPTION] or [ANALYSIS] logs

## Clear Logs

To clear logs before testing:

```powershell
# PowerShell
Remove-Item "D:\clipcut\pipeline.log" -ErrorAction SilentlyContinue
Remove-Item "D:\clipcut\server.log" -ErrorAction SilentlyContinue
```

Then restart the server to start fresh logs.
