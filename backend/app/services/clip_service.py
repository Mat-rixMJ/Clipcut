"""Service for extracting and creating short clips from analyzed videos."""
import subprocess
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.db_models import Clip, Job, JobStatus


def extract_clip(
    video_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
    target_aspect_ratio: str = "9:16",  # Vertical for shorts/reels/tiktok
    normalize_audio: bool = True,
) -> None:
    """
    Extract a clip from video and format it for short-form content.
    
    Args:
        video_path: Source video path
        start_time: Start time in seconds
        end_time: End time in seconds
        output_path: Where to save the clip
        target_aspect_ratio: Target aspect ratio (9:16 for vertical, 1:1 for square)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    duration = end_time - start_time
    
    # Build ffmpeg command with smart cropping for vertical format
    if target_aspect_ratio == "9:16":
        # Vertical video (1080x1920)
        vf_filter = (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"setsar=1"
        )
    elif target_aspect_ratio == "1:1":
        # Square video (1080x1080)
        vf_filter = (
            f"scale=1080:1080:force_original_aspect_ratio=increase,"
            f"crop=1080:1080,"
            f"setsar=1"
        )
    else:
        # Keep original aspect ratio
        vf_filter = "scale=1080:-2"
    
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-i", str(video_path),
        "-t", str(duration),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
    ]

    if normalize_audio:
        cmd.extend(["-af", "loudnorm"])

    cmd.append(str(output_path))
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg clip extraction failed: {result.stderr}")


def add_captions_to_clip(
    clip_path: Path,
    output_path: Path,
    subtitle_text: Optional[str] = None
) -> None:
    """
    Add captions/subtitles to a clip (optional enhancement).
    
    This can be extended to use AI for auto-captioning.
    """
    if not subtitle_text:
        # If no subtitles, just copy the file
        output_path.write_bytes(clip_path.read_bytes())
        return
    
    # Create a simple subtitle file
    srt_path = clip_path.parent / f"{clip_path.stem}.srt"
    srt_path.write_text(subtitle_text, encoding="utf-8")
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(clip_path),
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        str(output_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg subtitle addition failed: {result.stderr}")


def process_clip_generation_job(job_id: str) -> None:
    """Background task to generate clips from analyzed video."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            return

        # Idempotency: if all clips already generated with existing files, mark success.
        existing = db.query(Clip).filter(Clip.video_id == job.video_id, Clip.output_path != None).all()
        if existing and all(Path(c.output_path).exists() for c in existing if c.output_path):
            job.status = JobStatus.SUCCESS
            job.step = "generating_clips"
            job.progress = 1.0
            db.commit()
            return
        
        job.status = JobStatus.RUNNING
        job.step = "generating_clips"
        job.progress = 0.0
        db.commit()
        
        # Get all clips for this video (including those with paths that don't exist)
        clips = db.query(Clip).filter(
            Clip.video_id == job.video_id
        ).order_by(Clip.rank).all()
        
        if not clips:
            raise RuntimeError("No clips found to generate")
        
        video = clips[0].video
        video_path = Path(video.original_path)
        
        total_clips = len(clips)
        for idx, clip in enumerate(clips):
            job.step = f"generating_clip_{idx + 1}_of_{total_clips}"
            job.progress = idx / total_clips
            db.commit()
            
            # Generate output path in video-specific subfolder
            video_folder = settings.data_dir / "renders" / str(video.id)
            video_folder.mkdir(parents=True, exist_ok=True)
            output_path = video_folder / f"clip_{clip.rank}_{clip.id}.mp4"
            
            # Skip if file already exists
            if output_path.exists():
                clip.output_path = str(output_path)
                clip.duration = clip.end_time - clip.start_time
                db.commit()
                continue
            
            # Extract the clip
            extract_clip(
                video_path=video_path,
                start_time=clip.start_time,
                end_time=clip.end_time,
                output_path=output_path,
                target_aspect_ratio="9:16",
                normalize_audio=True,
            )
            
            # Update clip record
            clip.output_path = str(output_path)
            clip.duration = clip.end_time - clip.start_time
            db.commit()
        
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


def regenerate_clip_with_settings(
    clip_id: str,
    aspect_ratio: str = "9:16",
    add_captions: bool = False
) -> Path:
    """
    Regenerate a specific clip with custom settings.
    
    Args:
        clip_id: ID of the clip to regenerate
        aspect_ratio: Target aspect ratio
        add_captions: Whether to add auto-captions
        
    Returns:
        Path to the generated clip
    """
    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).one()
        video = clip.video
        
        video_path = Path(video.original_path)
        output_path = settings.data_dir / "renders" / f"{clip.id}_{aspect_ratio.replace(':', 'x')}.mp4"
        
        extract_clip(
            video_path=video_path,
            start_time=clip.start_time,
            end_time=clip.end_time,
            output_path=output_path,
            target_aspect_ratio=aspect_ratio,
            normalize_audio=True,
        )
        
        if add_captions:
            captioned_path = output_path.parent / f"{output_path.stem}_captioned.mp4"
            add_captions_to_clip(output_path, captioned_path)
            output_path = captioned_path
        
        return output_path
        
    finally:
        db.close()
