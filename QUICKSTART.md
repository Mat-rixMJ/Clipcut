# 🎬 ClipCut - Quick Start Guide

## What This Does

**ClipCut automatically turns long YouTube videos into viral-ready short clips!**

1. 📥 Paste a YouTube URL
2. 🤖 AI analyzes the video and finds the most engaging moments
3. ⭐ Scores each part from 1-10 for engagement
4. ✂️ Cuts out the best parts (15-60 seconds)
5. 📱 Formats them vertically for Instagram/TikTok/Shorts
6. ✅ Downloads ready-to-upload MP4 files

## Installation (5 minutes)

### Step 1: Install FFmpeg

- **Windows**: Download from https://ffmpeg.org/download.html, extract, add to PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### Step 2: Install Python Dependencies

```bash
cd clipcut/backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
cd ..
python scripts/check_requirements.py
```

Should show all ✅ checkmarks.

## Usage

### Option 1: Start Server (Recommended)

```bash
# Windows: Just double-click
start_server.bat

# Or manually:
cd backend
uvicorn app.main:app --reload
```

Server runs at: http://localhost:8000

Visit docs: http://localhost:8000/docs

### Option 2: Use Test Script

```bash
python scripts/test_pipeline.py
```

Enter a YouTube URL and watch it process!

### Option 3: Use API Directly

**Process a video (complete pipeline):**

```bash
curl -X POST http://localhost:8000/api/videos/process-youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

**Check status:**

```bash
curl http://localhost:8000/api/videos/{video_id}
```

**Download clips:**

```bash
curl http://localhost:8000/api/videos/clips/{clip_id}/download -o clip.mp4
```

## How It Works

```
YouTube URL → Download → Extract Audio → Analyze Engagement → Generate Clips
                ↓            ↓               ↓                    ↓
            video.mp4    audio.wav      scores 1-10         clip_1.mp4
                                                            clip_2.mp4
                                                            clip_3.mp4
```

### Engagement Analysis

The system scores segments based on:

- **Audio Energy**: Loud/dynamic audio = exciting content
- **Scene Changes**: Visual transitions = interesting moments
- **Position**: Start/end of videos tend to be engaging

Segments scoring **7+ out of 10** are extracted as clips.

## File Locations

```
backend/data/
├── videos/      ← Downloaded YouTube videos
├── audio/       ← Extracted audio files
└── artifacts/   ← 🎉 YOUR READY-TO-UPLOAD CLIPS!
```

## Example Workflow

1. Start server: `start_server.bat`
2. Visit: http://localhost:8000/docs
3. Try endpoint: `POST /api/videos/process-youtube`
4. Body: `{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}`
5. Get video_id from response
6. Check progress: `GET /api/videos/{video_id}`
7. When complete, see clips: `GET /api/videos/{video_id}/clips`
8. Download best clip: `GET /api/videos/clips/{clip_id}/download`
9. Upload to Instagram/TikTok/YouTube Shorts! 🚀

## Troubleshooting

**"FFmpeg not found"**

- Make sure FFmpeg is installed and in your PATH
- Test: `ffmpeg -version`

**"yt-dlp download failed"**

- Update yt-dlp: `pip install --upgrade yt-dlp`
- Some videos may be restricted by YouTube

**"No clips generated"**

- Video might be too short (< 30 seconds)
- Try lowering the engagement threshold in `analysis_service.py`

**Jobs stuck in RUNNING**

- Restart the server
- Check logs for errors

## API Endpoints Summary

| Endpoint                          | Method | Description                        |
| --------------------------------- | ------ | ---------------------------------- |
| `/api/videos/process-youtube`     | POST   | 🔥 Main endpoint - does everything |
| `/api/videos/{id}`                | GET    | Check status & get clips           |
| `/api/videos/{id}/clips`          | GET    | List all clips                     |
| `/api/videos/clips/{id}/download` | GET    | Download MP4 file                  |
| `/health`                         | GET    | Health check                       |
| `/docs`                           | GET    | Interactive API docs               |

## Tips for Best Results

✨ **Choose videos with**:

- Dynamic content (not static talking)
- Music or sound effects
- Visual variety (scene changes)
- 5-30 minutes long (sweet spot)

❌ **Avoid**:

- Very quiet videos
- Static camera shots
- Extremely long videos (>1 hour)

## What's Next?

After generating clips:

1. Review them in `backend/data/artifacts/`
2. Pick the best ones (usually clip_1 is top-ranked)
3. Optional: Edit titles/captions
4. Upload to your social media platforms!

## Advanced Configuration

Edit `backend/app/core/config.py`:

```python
DATA_DIR = "data"           # Where files are stored
DATABASE_URL = "sqlite://..." # Database location
```

Edit engagement detection in `backend/app/services/analysis_service.py`:

```python
target_score = 7            # Minimum score (lower = more clips)
min_duration = 15.0         # Minimum clip length
max_duration = 60.0         # Maximum clip length
```

## Need Help?

1. Check `/docs` endpoint for API documentation
2. Run `python scripts/check_requirements.py` to verify setup
3. Check server logs for error messages
4. Make sure FFmpeg is installed: `ffmpeg -version`

---

**Made with ❤️ for content creators!**

_Turn hours of content into dozens of shorts in minutes_ 🚀
