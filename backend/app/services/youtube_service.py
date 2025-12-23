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


def download_youtube_video(url: str, db: Session, title: Optional[str] = None, download_quality: Optional[str] = None) -> tuple[Video, Job]:
    """
    Download a YouTube video and create a video record with an ingest job.
    
    Args:
        url: YouTube video URL
        db: Database session
        title: Optional title for the video
        download_quality: Download quality (480p, 720p, 1080p - max is 1080p)
        
    Returns:
        Tuple of (Video, Job)
    """
    video_id = str(uuid.uuid4())
    output_path = settings.data_dir / "videos" / f"{video_id}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Cap quality at 1080p
    if download_quality not in ["480p", "720p", "1080p"]:
        download_quality = "1080p"
    
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


def process_youtube_download_job(job_id: str, download_quality: str = "1080p") -> None:
    """Background task to download YouTube video using yt-dlp with quality limits."""
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
        
        # Map quality to yt-dlp format filter - cap at 1080p
        quality_filters = {
            "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
            "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        }
        
        # Ensure quality is in valid range
        if download_quality not in quality_filters:
            download_quality = "1080p"
        
        format_filter = quality_filters[download_quality]
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            format_filter,
            "--merge-output-format",
            "mp4",
            "-o",
            str(output_path),
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Prefer using a JS runtime if configured (avoids format extraction issues)
            *( ["--js-runtimes", settings.yt_js_runtime] if settings.yt_js_runtime else [] ),
            video.source_url,
        ]

        # Add cookies from browser to avoid bot/age verification issues
        if settings.yt_cookies_browser:
            cmd.extend(["--cookies-from-browser", settings.yt_cookies_browser])

        # If cookies file provided, use it (takes precedence)
        if settings.yt_cookies_file and Path(settings.yt_cookies_file).exists():
            cmd.extend(["--cookies", str(settings.yt_cookies_file)])
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        # Monitor download progress
        output_lines: list[str] = []
        for line in iter(process.stdout.readline, ""):
            output_lines.append(line.rstrip())
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
            tail = "\n".join(output_lines[-60:]) if output_lines else "(no output)"
            # Surface common guidance for bot/cookie issues
            if "Sign in to confirm you’re not a bot" in tail or "not a bot" in tail:
                tail += "\nHint: Provide cookies via --cookies-from-browser (e.g., 'edge:Default') or export cookies.txt and set SETTINGS.yt_cookies_file."
            raise RuntimeError(f"YouTube download failed. Details:\n{tail}")
        
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
