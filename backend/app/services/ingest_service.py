import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.db_models import Job, JobStatus, Video


def register_video_with_job(db: Session, upload_file: UploadFile, title: Optional[str]) -> Tuple[Video, Job]:
    video_id = str(uuid.uuid4())
    suffix = Path(upload_file.filename or "video.mp4").suffix or ".mp4"
    original_path = settings.data_dir / "videos" / f"{video_id}{suffix}"

    video = Video(
        id=video_id,
        title=title,
        original_path=str(original_path),
    )
    job = Job(id=str(uuid.uuid4()), video_id=video_id, job_type="ingest")
    db.add(video)
    db.add(job)
    db.commit()
    db.refresh(video)
    db.refresh(job)
    return video, job


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as f:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def _ffprobe_metadata(video_path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-show_streams",
        "-of",
        "json",
        str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def _extract_fps(streams: list) -> Optional[float]:
    for stream in streams:
        if stream.get("codec_type") == "video":
            avg_frame_rate = stream.get("avg_frame_rate")
            if avg_frame_rate and avg_frame_rate != "0/0":
                num, den = avg_frame_rate.split("/")
                if float(den) != 0:
                    return float(num) / float(den)
    return None


def _extract_audio(video_path: Path, audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extract failed: {proc.stderr.strip()}")


def process_ingest_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            return

        # Idempotency: if audio already extracted and metadata present, mark success.
        video = db.query(Video).filter(Video.id == job.video_id).one()
        if video.audio_path and Path(video.audio_path).exists() and video.duration_seconds and video.fps:
            job.status = JobStatus.SUCCESS
            job.progress = 1.0
            job.step = "ingest"
            db.commit()
            return

        job.status = JobStatus.RUNNING
        job.step = "ingest"
        db.commit()
        db.refresh(job)
        video_path = Path(video.original_path)

        meta = _ffprobe_metadata(video_path)
        duration = float(meta.get("format", {}).get("duration")) if meta.get("format", {}).get("duration") else None
        fps = _extract_fps(meta.get("streams", []))

        audio_path = settings.data_dir / "audio" / f"{video.id}.wav"
        _extract_audio(video_path, audio_path)

        video.duration_seconds = duration
        video.fps = fps
        video.audio_path = str(audio_path)
        video.raw_metadata = meta
        job.status = JobStatus.SUCCESS
        job.progress = 1.0
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()
