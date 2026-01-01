"""Service for analyzing video engagement using AI and audio/visual features."""
import json
import subprocess
from pathlib import Path
from typing import List, Optional
import re
import os
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.db_models import Clip, Job, JobStatus, Video
from app.models.db_models import Clip, Job, JobStatus, Video
from app.services import scoring_service
from app.services.scoring_service import generate_video_title


logger = logging.getLogger(__name__)



def analyze_audio_energy(audio_path: Path, duration: float) -> List[dict]:
    """
    Analyze audio energy levels over 1-second windows using a single ffmpeg pass.

    Implementation notes:
    - Uses astats with reset=1:length=1 to emit per-second stats
    - Parses 'RMS level dB' (or falls back to 'mean_volume') from ffmpeg output
    - Normalizes dB from [-60, 0] to [0, 1]
    - Falls back to the per-second subprocess method if parsing yields no data
    """
    # Single-pass ffmpeg call producing per-second stats
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-v", "info",
        "-nostats",
        "-i", str(audio_path),
        "-af", "astats=metadata=1:reset=1:length=1",
        "-f", "null",
        "-",
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # Parse per-second RMS level dB (preferred) or mean_volume if present
    lines = proc.stdout.splitlines() if proc.stdout else []
    rms_values_db: List[float] = []
    rms_pattern = re.compile(r"RMS level dB:\s*(-?\d+(?:\.\d+)?)")
    mean_vol_pattern = re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB")

    for line in lines:
        m = rms_pattern.search(line)
        if m:
            try:
                rms_values_db.append(float(m.group(1)))
                continue
            except ValueError:
                pass
        m2 = mean_vol_pattern.search(line)
        if m2:
            try:
                rms_values_db.append(float(m2.group(1)))
            except ValueError:
                pass

    segments: List[dict] = []
    num_segments = int(duration)

    def norm_from_db(db_val: float) -> float:
        # Normalize to 0..1 from -60..0 dB range
        normalized = (db_val + 60.0) / 60.0
        return max(0.0, min(1.0, normalized))

    if rms_values_db:
        # Use parsed values up to duration seconds
        for i in range(num_segments):
            start_time = i
            end_time = min(i + 1, duration)
            db_val = rms_values_db[i] if i < len(rms_values_db) else -60.0
            energy = norm_from_db(db_val)
            segments.append({
                "start": start_time,
                "end": end_time,
                "energy": energy,
            })
        return segments

    # Fallback: if parsing failed (e.g., unexpected ffmpeg output),
    # use the previous per-second subprocess approach for correctness.
    for i in range(num_segments):
        start_time = i
        end_time = min(i + 1, duration)
        energy = _calculate_segment_energy(audio_path, start_time, end_time)
        segments.append({
            "start": start_time,
            "end": end_time,
            "energy": energy,
        })
    return segments


def _calculate_segment_energy(audio_path: Path, start: float, end: float) -> float:
    """Calculate RMS energy for a specific audio segment."""
    cmd = [
        "ffmpeg",
        "-i", str(audio_path),
        "-ss", str(start),
        "-t", str(end - start),
        "-af", "volumedetect",
        "-f", "null",
        "-"
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Parse mean volume from output
    for line in result.stdout.split('\n'):
        if "mean_volume:" in line:
            try:
                # Extract dB value (higher is louder)
                volume_str = line.split("mean_volume:")[1].split("dB")[0].strip()
                volume_db = float(volume_str)
                # Normalize to 0-1 scale (assuming -60dB to 0dB range)
                normalized = (volume_db + 60) / 60
                return max(0, min(1, normalized))
            except (ValueError, IndexError):
                pass
    
    return 0.5  # Default mid-range value


def detect_scene_changes(video_path: Path) -> List[float]:
    """Detect scene changes in the video (potential engagement points)."""
    # Read env var first, fallback to settings
    hwaccel = os.getenv("FFMPEG_HWACCEL", settings.ffmpeg_hwaccel)
    # If not explicitly set, follow Whisper device: if CUDA, prefer GPU decoding
    if not hwaccel:
        whisper_dev = os.getenv("WHISPER_DEVICE", settings.whisper_device)
        if whisper_dev and whisper_dev.lower() == "cuda":
            hwaccel = "cuda"
    
    # Build ffmpeg command with optional hardware acceleration
    cmd = ["ffmpeg"]
    
    # Add hardware acceleration if configured
    if hwaccel:
        if hwaccel == "cuda":
            # NVIDIA CUDA acceleration with NVDEC
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        elif hwaccel in ["d3d11va", "dxva2", "qsv"]:
            # Windows Direct3D / Intel Quick Sync
            cmd.extend(["-hwaccel", hwaccel])
    
    cmd.extend([
        "-i", str(video_path),
        "-vf", "select='gt(scene,0.3)',showinfo",
        "-f", "null",
        "-"
    ])
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    scene_times = []
    for line in result.stdout.split('\n'):
        if "pts_time:" in line:
            try:
                time_str = line.split("pts_time:")[1].split()[0]
                scene_times.append(float(time_str))
            except (ValueError, IndexError):
                pass
    
    return scene_times


def calculate_engagement_score(
    segments: List[dict],
    scene_changes: List[float],
    duration: float
) -> List[dict]:
    """
    Calculate engagement scores (1-10) for video segments.
    
    Combines:
    - Audio energy (loudness variations indicate excitement)
    - Scene changes (visual dynamics)
    - Position in video (beginning and end often more engaging)
    """
    scored_segments = []
    
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        mid = (start + end) / 2
        
        # Audio energy score (0-4 points)
        audio_score = segment["energy"] * 4
        
        # Scene change score (0-3 points) - check if scene change nearby
        scene_score = 0
        for scene_time in scene_changes:
            if abs(scene_time - mid) < 2.0:  # Within 2 seconds
                scene_score = 3
                break
        
        # Position score (0-3 points) - favor beginning/end
        position_factor = 1 - abs(mid - duration/2) / (duration/2)
        position_score = position_factor * 3
        
        # Combine scores (max 10)
        total_score = audio_score + scene_score + position_score
        engagement_score = min(10, max(1, round(total_score)))
        
        scored_segments.append({
            "start": start,
            "end": end,
            "engagement_score": engagement_score,
            "audio_score": round(audio_score, 2),
            "scene_score": scene_score,
            "position_score": round(position_score, 2),
        })
    
    return scored_segments


def find_best_clips(
    scored_segments: List[dict],
    min_duration: float = 30.0,
    max_duration: float = 60.0,
    target_score: int = 7
) -> List[dict]:
    """
    Find the best continuous segments for short-form content.
    
    Args:
        scored_segments: Segments with engagement scores
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        target_score: Minimum average score to consider
        
    Returns:
        List of clip candidates with start, end, and average score
    """
    clips = []
    
    # Sliding window approach to find high-engagement continuous segments
    for window_size in range(int(min_duration), int(max_duration) + 1, 5):
        for i in range(len(scored_segments) - window_size + 1):
            window = scored_segments[i:i + window_size]

            # Prefer llm_score when present; fallback to engagement_score
            avg_score = sum(
                (s.get("llm_score") or s.get("engagement_score", 0)) for s in window
            ) / len(window)

            if avg_score >= target_score:
                clips.append({
                    "start": window[0]["start"],
                    "end": window[-1]["end"],
                    "duration": window_size,
                    "avg_engagement_score": round(avg_score, 2),
                })
    
    # Sort by average score (descending)
    clips.sort(key=lambda x: x["avg_engagement_score"], reverse=True)
    
    # Remove overlapping clips, keep the best ones
    final_clips = []
    for clip in clips:
        overlaps = False
        for existing in final_clips:
            if not (clip["end"] <= existing["start"] or clip["start"] >= existing["end"]):
                overlaps = True
                break
        
        if not overlaps:
            final_clips.append(clip)
        
        if len(final_clips) >= 5:  # Limit to top 5 clips
            break
    
    # Fallback: if no clips meet threshold, lower it and try again
    if len(final_clips) == 0 and target_score > 1:
        # Recursively try with lower threshold
        return find_best_clips(scored_segments, min_duration, max_duration, target_score=max(1, target_score - 2))
    
    return final_clips


def process_analysis_job(job_id: str) -> None:
    """Background task to analyze video engagement."""
    logger.info(f"[ANALYSIS] Starting analysis job: {job_id}")
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            logger.error(f"[ANALYSIS] Job not found: {job_id}")
            return

        video = db.query(Video).filter(Video.id == job.video_id).one()
        logger.info(f"[ANALYSIS] Processing video: {video.id}, title={video.title}")

        # Idempotency: if clips already exist and heatmap present, short-circuit.
        existing_clips = db.query(Clip).filter(Clip.video_id == video.id).count()
        has_heatmap = bool(video.analysis_data and isinstance(video.analysis_data, dict) and video.analysis_data.get("heatmap"))
        if existing_clips > 0 and has_heatmap:
            logger.info(f"[ANALYSIS] Clips already exist ({existing_clips} clips) with heatmap, skipping analysis")
            job.status = JobStatus.SUCCESS
            job.step = "analyzing"
            job.progress = 1.0
            db.commit()
            return
        
        logger.info(f"[ANALYSIS] No existing clips or heatmap, proceeding with analysis")
        job.status = JobStatus.RUNNING
        job.step = "analyzing"
        job.progress = 0.0
        db.commit()
        
        if not video.audio_path or not video.duration_seconds:
            logger.error(f"[ANALYSIS] Video not properly ingested: audio_path={video.audio_path}, duration={video.duration_seconds}")
            raise RuntimeError("Video must be ingested before analysis")
        
        video_path = Path(video.original_path)
        audio_path = Path(video.audio_path)
        logger.info(f"[ANALYSIS] Video path: {video_path}, Audio path: {audio_path}")

        # Check for transcript for auto-title and scoring
        transcript_segments = None
        if video.analysis_data and isinstance(video.analysis_data, dict):
            transcript_segments = video.analysis_data.get("transcript")
        
        # Auto-Title: If title is generic and we have transcript, generate a new one
        if transcript_segments and (
            not video.title or 
            video.title in ["YouTube Video", "video.mp4"] or 
            video.title.startswith("video-") or
            "download" in video.title.lower()
        ):
            logger.info("[ANALYSIS] Generic title detected. Generating auto-title...")
            # Combine first 2 mins of text for title generation
            transcript_text = " ".join([
                t.get("text", "") for t in transcript_segments 
                if t.get("end", 0) < 120
            ])
            new_title = generate_video_title(transcript_text)
            if new_title:
                logger.info(f"[ANALYSIS] New title generated: {new_title}")
                video.title = new_title
                db.commit()
        
        # Step 1: Analyze audio energy
        logger.info(f"[ANALYSIS] Step 1: Analyzing audio energy...")
        job.step = "analyzing_audio"
        job.progress = 0.2
        db.commit()
        
        segments = analyze_audio_energy(audio_path, video.duration_seconds)
        logger.info(f"[ANALYSIS] Step 1 complete: {len(segments)} audio segments")
        
        # Step 2: Detect scene changes
        logger.info(f"[ANALYSIS] Step 2: Detecting scene changes...")
        job.step = "detecting_scenes"
        job.progress = 0.5
        db.commit()
        
        scene_changes = detect_scene_changes(video_path)
        logger.info(f"[ANALYSIS] Step 2 complete: {len(scene_changes)} scene changes detected")
        
        # Step 3: Calculate engagement scores
        logger.info(f"[ANALYSIS] Step 3: Calculating engagement scores...")
        job.step = "scoring_engagement"
        job.progress = 0.7
        db.commit()
        
        scored_segments = calculate_engagement_score(
            segments, scene_changes, video.duration_seconds
        )
        logger.info(f"[ANALYSIS] Step 3 complete: {len(scored_segments)} scored segments")

        # Optional LLM scoring to refine heatmap using transcript
        logger.info(f"[ANALYSIS] Step 3b: Applying LLM scoring (if enabled)...")
        transcript_segments = None
        if video.analysis_data and isinstance(video.analysis_data, dict):
            transcript_segments = video.analysis_data.get("transcript")
            logger.info(f"[ANALYSIS] Found {len(transcript_segments) if transcript_segments else 0} transcript segments")

        scored_segments = scoring_service.apply_llm_scoring(
            scored_segments, transcript_segments
        )
        logger.info(f"[ANALYSIS] LLM scoring applied")
        
        # Step 4: Find best clips
        logger.info(f"[ANALYSIS] Step 4: Finding best clips...")
        job.step = "finding_clips"
        job.progress = 0.9
        db.commit()
        
        best_clips = find_best_clips(scored_segments)
        logger.info(f"[ANALYSIS] Step 4 complete: {len(best_clips)} best clips found")
        
        # Save clips to database
        logger.info(f"[ANALYSIS] Saving {len(best_clips)} clips to database...")
        for idx, clip_data in enumerate(best_clips):
            clip = Clip(
                video_id=video.id,
                start_time=clip_data["start"],
                end_time=clip_data["end"],
                engagement_score=clip_data["avg_engagement_score"],
                rank=idx + 1,
            )
            db.add(clip)
            logger.debug(f"[ANALYSIS] Added clip {idx+1}: {clip_data['start']:.1f}s - {clip_data['end']:.1f}s, score={clip_data['avg_engagement_score']}")
        
        # Store analysis results (preserve previously stored data like transcript)
        logger.info(f"[ANALYSIS] Storing analysis metadata...")
        analysis_data = video.analysis_data or {}
        analysis_data.update(
            {
                "segments": scored_segments[:100],  # Store first 100 segments
                "scene_changes": scene_changes[:50],
                "best_clips": best_clips,
                "heatmap": scored_segments,
            }
        )
        video.analysis_data = analysis_data
        
        job.status = JobStatus.SUCCESS
        job.progress = 1.0
        db.commit()
        logger.info(f"[ANALYSIS] Job SUCCESS: {job_id}")
        
    except Exception as exc:
        logger.error(f"[ANALYSIS] Job FAILED with exception: {exc}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()

