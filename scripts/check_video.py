"""Check video status"""
import sys
sys.path.insert(0, 'D:/clipcut/backend')

from app.core.db import SessionLocal
from app.models.db_models import Video, Job, Clip

video_id = "37298f10-c89b-4858-9ea3-779551147106"

db = SessionLocal()
try:
    video = db.query(Video).filter(Video.id == video_id).one()
    jobs = db.query(Job).filter(Job.video_id == video_id).all()
    clips = db.query(Clip).filter(Clip.video_id == video_id).all()
    
    print(f"Video: {video.title or 'No title'}")
    print(f"Duration: {video.duration_seconds}s")
    print(f"\nJobs ({len(jobs)}):")
    for j in jobs:
        print(f"  - {j.job_type}: {j.status}")
    
    print(f"\nClips ({len(clips)}):")
    for c in clips:
        print(f"  - Clip {c.rank}: {c.start_time}s-{c.end_time}s, score={c.engagement_score}")
finally:
    db.close()
