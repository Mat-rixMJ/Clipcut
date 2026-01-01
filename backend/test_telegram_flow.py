import sys
import os
from pathlib import Path
import logging

# Setup path so 'app' module can be imported
sys.path.append(os.getcwd())

from app.core.db import SessionLocal
from app.services.youtube_service import download_youtube_video
from app.api.videos import _run_full_pipeline

# Configure basic logging to see output in console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

URL = "https://www.youtube.com/watch?v=KrLj6nc516A"

def run_test():
    print(f"--- Starting Pipeline Test for {URL} ---")
    db = SessionLocal()
    try:
        # 1. Start Download
        print("1. Initiating YouTube Download...")
        video, job = download_youtube_video(URL, db, title="Test Run for Telegram")
        print(f"   Video ID: {video.id}")
        print(f"   Job ID: {job.id}")
        
        # 2. Run Pipeline
        print("2. Running Full Pipeline (this may take a few minutes)...")
        _run_full_pipeline(
            video_id=video.id,
            download_job_id=job.id,
            ingest_job_id=None,
            prefer_gpu=False,
            clip_settings={
                "min_duration": 10.0,
                "max_duration": 45.0,
                "min_engagement_score": 3, # Low score to ensure we get clips
                "download_quality": "720p", # Faster download for test
            }
        )
        print("--- Pipeline Execution Completed ---")
        print("Check your Telegram for the video!")
        
    except Exception as e:
        print(f"!!! Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
