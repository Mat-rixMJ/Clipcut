"""Service for extracting and creating short clips from analyzed videos."""
import subprocess
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.db_models import Clip, Job, JobStatus
from app.services.notification_service import send_clip_to_telegram
from app.services.scoring_service import generate_short_caption
from app.services.youtube_upload_service import upload_video


def extract_clip(
    video_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
    target_aspect_ratio: str = "9:16",  # Vertical for shorts/reels/tiktok
    normalize_audio: bool = True,
    video_quality: str = "1080p",
    video_format: str = "h264",
) -> None:
    """
    Extract a clip from video and format it for short-form content.
    
    Args:
        video_path: Source video path
        start_time: Start time in seconds
        end_time: End time in seconds
        output_path: Where to save the clip
        target_aspect_ratio: Target aspect ratio (9:16 for vertical, 1:1 for square)
        video_quality: Quality level (480p, 720p, 1080p - max is 1080p)
        video_format: Video codec (h264, h265, av1, vp9)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    duration = end_time - start_time
    
    # Enforce max 1080P, map quality levels
    quality_map = {
        "480p": "848:480",    # Maintain 16:9 aspect
        "720p": "1280:720",   # Maintain 16:9 aspect
        "1080p": "1920:1080", # Maintain 16:9 aspect (max)
    }
    # Cap at 1080p if higher specified
    if video_quality not in quality_map:
        video_quality = "1080p"
    
    # Build ffmpeg command with smart cropping for vertical format
    if target_aspect_ratio == "9:16":
        # Vertical video - scale to quality, then crop to 9:16 (1080x1920 for 1080p)
        base_width, base_height = map(int, quality_map[video_quality].split(":"))
        # For 9:16: width=1080 at 1080p, scale proportionally for other qualities
        scale_factor = base_width / 1920  # e.g., 848/1920 for 480p
        vert_width = int(1080 * scale_factor)
        vert_height = int(1920 * scale_factor)
        
        vf_filter = (
            f"scale={vert_width}:{vert_height}:force_original_aspect_ratio=increase,"
            f"crop={vert_width}:{vert_height},"
            f"setsar=1"
        )
    elif target_aspect_ratio == "1:1":
        # Square video - scale to quality, then crop to square
        base_width, base_height = map(int, quality_map[video_quality].split(":"))
        scale_factor = base_width / 1920
        sq_size = int(1080 * scale_factor)
        
        vf_filter = (
            f"scale={sq_size}:{sq_size}:force_original_aspect_ratio=increase,"
            f"crop={sq_size}:{sq_size},"
            f"setsar=1"
        )
    else:
        # Keep original aspect ratio but cap at quality
        base_width, base_height = map(int, quality_map[video_quality].split(":"))
        vf_filter = f"scale={base_width}:{base_height}:force_original_aspect_ratio=decrease"
    
    # Select codec based on video_format
    if video_format == "h265":
        codec_args = ["-c:v", "libx265", "-preset", "medium", "-crf", "23"]
    elif video_format == "av1":
        codec_args = ["-c:v", "libaom-av1", "-b:v", "2M", "-cpu-used", "4"]
    elif video_format == "vp9":
        codec_args = ["-c:v", "libvpx-vp9", "-b:v", "2M", "-deadline", "good"]
    else:  # h264 (default)
        codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]
    
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-i", str(video_path),
        "-t", str(duration),
        "-vf", vf_filter,
    ]
    
    cmd.extend(codec_args)
    cmd.extend([
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
    ])

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



def generate_srt_from_transcript(transcript: list[dict], clip_start: float, clip_end: float, output_path: Path) -> None:
    """Generate an SRT file for the clip timeframe from the full transcript."""
    relevant_segments = []
    for seg in transcript:
        # Check if segment overlaps with clip
        seg_start = seg["start"]
        seg_end = seg["end"]
        if seg_end > clip_start and seg_start < clip_end:
            # Adjust timings relative to clip start
            rel_start = max(0.0, seg_start - clip_start)
            rel_end = min(clip_end - clip_start, seg_end - clip_start)
            relevant_segments.append({
                "start": rel_start,
                "end": rel_end,
                "text": seg["text"].strip()
            })
    
    def format_time(seconds: float) -> str:
        ms = int((seconds % 1) * 1000)
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with output_path.open("w", encoding="utf-8") as f:
        for i, seg in enumerate(relevant_segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")


def extract_hashtags(text: str, max_tags: int = 5) -> str:
    """Extract simple frequency-based hashtags from text."""
    if not text:
        return ""
    
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "this", "that", "it", "you", "i", "we", "they", "he", "she"}
    words = [w.lower() for w in text.split() if w.isalpha() and len(w) > 3]
    words = [w for w in words if w not in stop_words]
    
    from collections import Counter
    counts = Counter(words)
    top_words = counts.most_common(max_tags)
    
    return " ".join([f"#{word}" for word, count in top_words])


def process_clip_generation_job(job_id: str, clip_settings: dict | None = None) -> None:
    """Background task to generate clips from analyzed video with custom settings."""
    if clip_settings is None:
        clip_settings = {
            "min_duration": 20.0,
            "max_duration": 60.0,
            "min_engagement_score": 7,
            "video_quality": "1080p",
            "video_format": "h264",
        }
    
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
        
        # Get full transcript for captions/hashtags
        full_transcript = []
        if video.analysis_data and isinstance(video.analysis_data, dict):
            full_transcript = video.analysis_data.get("transcript", [])

        total_clips = len(clips)
        for idx, clip in enumerate(clips):
            # Check for cancellation before starting next clip
            check_db = SessionLocal()
            try:
                current_job = check_db.query(Job).filter(Job.id == job_id).one_or_none()
                if current_job and current_job.status == JobStatus.FAILED:
                    raise RuntimeError("Job cancelled by user")
            finally:
                check_db.close()

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
            
            # Prepare subtitles and hashtags if transcript exists
            srt_path = None
            hashtags = ""
            if full_transcript:
                # 1. Generate SRT
                srt_path = video_folder / f"clip_{clip.rank}_{clip.id}.srt"
                generate_srt_from_transcript(full_transcript, clip.start_time, clip.end_time, srt_path)
                
                # 2. Extract Hashtags (from clip text)
                clip_text = " ".join([
                    seg["text"] for seg in full_transcript 
                    if seg["end"] > clip.start_time and seg["start"] < clip.end_time
                ])
                hashtags = extract_hashtags(clip_text)

                # 3. Generate LLM Caption
                llm_caption = generate_short_caption(clip_text)
                if llm_caption:
                    print(f"Generated LLM caption: {llm_caption}")

            # Extract the clip
            extract_clip(
                video_path=video_path,
                start_time=clip.start_time,
                end_time=clip.end_time,
                output_path=output_path,
                target_aspect_ratio="9:16",
                normalize_audio=True,
                video_quality=clip_settings.get("video_quality", "1080p"),
                video_format=clip_settings.get("video_format", "h264"),
            )
            
            # Burn captions if SRT generated
            if srt_path and srt_path.exists():
                try:
                    captioned_path = video_folder / f"clip_{clip.rank}_{clip.id}_captioned.mp4"
                    # Use simple ffmpeg command to burn subtitles
                    # Note: complex filter string escaping for windows path is tricky, 
                    # closest is replacing \ with / and using subtitles='path'
                    escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
                    
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", str(output_path),
                        "-vf", f"subtitles='{escaped_srt}':force_style='Fontsize=16,MarginV=25,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=3',drawtext=text='{clip.video.title}':x=(w-text_w)/2:y=30:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5",
                        "-c:a", "copy",
                        str(captioned_path)
                    ]
                    subprocess.run(cmd, check=True)
                    
                    # Replace original with captioned
                    if captioned_path.exists():
                        output_path.unlink()
                        captioned_path.rename(output_path)
                except Exception as e:
                    print(f"Failed to burn captions: {e}")

            # Update clip record
            clip.output_path = str(output_path)
            clip.duration = clip.end_time - clip.start_time
            clip.hashtags = hashtags
            db.commit()

            # Send to Telegram
            try:
                # Use LLM caption if available, else fallback
                if locals().get("llm_caption"):
                    caption = f"{llm_caption}\n\n{hashtags}\n\n#ClipCut"
                else:
                    caption = f"🎬 Clip {clip.rank} (Score: {clip.engagement_score})\n\n{hashtags}\n\n#ClipCut"
                # Use captioned path if it was created above
                final_path = output_path
                send_clip_to_telegram(final_path, caption)
                
            except Exception as e:
                logger.error(f"[TELEGRAM] Failed to send clip: {e}", exc_info=True)

            # Auto-Upload to YouTube
            try:
                # Construct description
                original_url = clip.video.source_url or ""
                description = (
                    f"{llm_caption or 'Interesting moment'}\n\n"
                    f"Original Video: {original_url}\n\n"
                    f"#Shorts {hashtags}"
                )
                
                # Use title from video or generate one
                upload_title = f"{clip.video.title} - Clip {clip.rank} #Shorts"
                if len(upload_title) > 100:
                    upload_title = upload_title[:97] + "..."

                upload_video(
                    file_path=final_path,
                    title=upload_title,
                    description=description,
                    tags=[t.strip("#") for t in hashtags.split() if t.strip()] + ["Shorts", "ClipCut"],
                    privacy_status="private" # Default to private for safety
                )
            except Exception as e:
                logger.error(f"[YOUTUBE UPLOAD] Failed to upload: {e}", exc_info=True)

        job.status = JobStatus.SUCCESS
        job.progress = 1.0
        db.commit()
        
    except Exception as exc:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job:
            # If it was already marked as FAILED by the stop command, we don't need to overwrite the error message
            if job.status != JobStatus.FAILED:
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
            # We would need the transcript to regenerate SRTs here if they don't exist
            # For now, simplistic reuse if exists could be dangerous if time changed
            # Ideally re-fetch transcript from video.analysis_data
            pass
        
        return output_path
        
    finally:
        db.close()
