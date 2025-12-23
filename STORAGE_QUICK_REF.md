# ClipCut Storage: Quick Reference

## 🎯 The Rule

> **All files go to ONE location: `D:\clipcut\data\`**

No exceptions. No scattered directories. Senior-level architecture.

---

## 📁 Storage Map

| **What**                               | **Location**                            | **Why**                |
| -------------------------------------- | --------------------------------------- | ---------------------- |
| Original videos (uploaded or YouTube)  | `data/videos/`                          | Input to pipeline      |
| Extracted audio (from videos)          | `data/audio/`                           | Input to transcription |
| Final rendered clips (9:16 short-form) | `data/renders/{video_id}/`              | Output to users        |
| Transcript metadata                    | Database + optional `data/transcripts/` | Searchable             |
| Engagement heatmap                     | Database + optional `data/heatmap/`     | Analytics              |

---

## 💻 Code Usage

**Always use this:**

```python
from app.core.config import StoragePaths

# Not this
# video_path = "D:\\clipcut\\data\\videos\\..."
# Not this
# video_path = "backend/data/videos/..."

# Do this
video_path = StoragePaths.videos_dir() / "myfile.mp4"
audio_path = StoragePaths.audio_dir() / "myfile.wav"
clip_path = StoragePaths.renders_dir(video_id) / "clip.mp4"
```

---

## 🔍 File Organization by Pipeline Step

```
User submits video
  ↓
Download/Upload → videos/{id}.mp4
  ↓
Ingest         → audio/{id}.wav + metadata in DB
  ↓
Transcription  → transcript in DB (or export to transcripts/)
  ↓
Analysis       → heatmap in DB (or export to heatmap/)
  ↓
Clip Rendering → renders/{id}/clip_1.mp4, clip_2.mp4, ...
  ↓
User downloads clips from renders/ directory
```

---

## ✅ Verification

Check that storage is unified:

```powershell
# Should see 6 directories: videos, audio, renders, transcripts, heatmap, artifacts
Get-ChildItem D:\clipcut\data\ -Directory

# Should NOT exist anymore
Test-Path D:\clipcut\backend\data  # Should return False ✓
```

---

## 🚨 If You See Multiple Locations

```
❌ D:\clipcut\data\
❌ D:\clipcut\backend\data\
❌ C:\temp\renders\
❌ Other random paths
```

**This is wrong.** Run the migration script:

```bash
python D:\clipcut\scripts\migrate_storage.py
```

---

## 📊 Current State (After Migration)

```
D:\clipcut\data\
├── videos/              (9 files) ✓
├── audio/               (19 files) ✓
├── renders/             (23 files across 3 video_ids) ✓
├── transcripts/         (0 files - metadata in DB)
├── heatmap/             (0 files - metadata in DB)
└── artifacts/           (1 file - cleanup safe)

Total: 52 media files, all in one location ✓
```

---

## 🎓 Senior Developer Principles Applied

✅ **DRY** (Don't Repeat Yourself) — One source of truth for paths  
✅ **SOLID** — Single Responsibility (each dir has one purpose)  
✅ **Clarity** — New team members immediately understand where files are  
✅ **Scalability** — Videos organized by ID, supports millions of files  
✅ **Maintainability** — Single location, single migration point

---

## 📚 For More Details

- `STORAGE_ARCHITECTURE.md` — Full design documentation
- `backend/app/core/config.py` — Source code + comments
- `scripts/migrate_storage.py` — Migration tool
