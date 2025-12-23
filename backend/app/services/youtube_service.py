"""Service for downloading videos from YouTube."""
import subprocess
import sys
from pathlib import Path
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.db_models import Job, JobStatus, Video


def download_youtube_video(url: str, db: Session, title: Optional[str] = None) -> tuple[Video, Job]:
    """
    Download a YouTube video and create a video record with an ingest job.
    
    Args:
        url: YouTube video URL
        db: Database session
        title: Optional title for the video
        
    Returns:
        Tuple of (Video, Job)
    """
    video_id = str(uuid.uuid4())
    output_path = settings.data_dir / "videos" / f"{video_id}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create video and job records
    video = Video(
        id=video_id,
        title=title or "YouTube Video",
        original_path=str(output_path),
        source_url=url,
    )
    job = Job(
        id=str(uuid.uuid4()),
        video_id=video_id,
        job_type="youtube_download",
    )
    
    db.add(video)
    db.add(job)
    db.commit()
    db.refresh(video)
    db.refresh(job)
    
    return video, job


def process_youtube_download_job(job_id: str) -> None:
    """Background task to download YouTube video using yt-dlp."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            return
            
        job.status = JobStatus.RUNNING
        job.step = "downloading"
        job.progress = 0.0
        db.commit()
        
        video = db.query(Video).filter(Video.id == job.video_id).one()
        output_path = Path(video.original_path)
        
        # Use yt-dlp to download the video
        # Call yt-dlp via the active Python interpreter so the venv copy is used (avoids PATH issues on Windows).
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            str(output_path),
            video.source_url,
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        # Monitor download progress
        for line in iter(process.stdout.readline, ""):
            if "[download]" in line and "%" in line:
                try:
                    # Parse progress from yt-dlp output
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            progress_str = part.replace("%", "").strip()
                            progress = float(progress_str) / 100.0
                            job.progress = progress * 0.9  # Reserve 10% for finalization
                            db.commit()
                            break
                except (ValueError, IndexError):
                    pass
        
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError("YouTube download failed")
        
        if not output_path.exists():
            raise RuntimeError(f"Downloaded file not found at {output_path}")
        
        # Get video title from yt-dlp if not provided
        if video.title == "YouTube Video":
            title_cmd = [sys.executable, "-m", "yt_dlp", "--get-title", video.source_url]
            result = subprocess.run(title_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                video.title = result.stdout.strip()
        
        job.status = JobStatus.SUCCESS
        job.progress = 1.0
        db.commit()
        
    except Exception as exc:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()
