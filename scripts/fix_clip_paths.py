"""Fix missing clip paths and reorganize clips into per-video folders"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.db import SessionLocal
from app.models.db_models import Clip, Video
from app.core.config import settings


def fix_clip_paths(video_id: str):
    """Move clips to per-video folders and update DB paths"""
    db = SessionLocal()
    try:
        # Get all clips for this video
        clips = db.query(Clip).filter(Clip.video_id == video_id).order_by(Clip.rank).all()
        video = db.query(Video).filter(Video.id == video_id).one()
        
        print(f"Processing {len(clips)} clips for video: {video.title or video.id}")
        
        # Create video-specific folder
        video_folder = settings.data_dir / "renders" / video_id
        video_folder.mkdir(parents=True, exist_ok=True)
        print(f"Video folder: {video_folder}")
        
        for clip in clips:
            old_path = None
            if clip.output_path:
                old_path = Path(clip.output_path)
            else:
                # Try to find file by clip ID in main renders folder
                possible_path = settings.data_dir / "renders" / f"{clip.id}.mp4"
                if possible_path.exists():
                    old_path = possible_path
            
            # New path in video subfolder
            new_path = video_folder / f"clip_{clip.rank}_{clip.id}.mp4"
            
            if old_path and old_path.exists():
                print(f"  Clip {clip.rank}: Moving {old_path.name} -> {new_path.name}")
                # Move file to new location
                import shutil
                shutil.move(str(old_path), str(new_path))
            else:
                print(f"  Clip {clip.rank}: No existing file found, will be generated to {new_path}")
            
            # Update DB path
            clip.output_path = str(new_path)
            db.commit()
        
        print(f"\n✓ All clip paths updated in database")
        print(f"Folder: {video_folder}")
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_clip_paths.py <video_id>")
        sys.exit(1)
    
    video_id = sys.argv[1]
    fix_clip_paths(video_id)
