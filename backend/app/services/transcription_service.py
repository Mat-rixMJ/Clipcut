"""Service for transcribing audio to text using Whisper (local)."""
from pathlib import Path
from typing import Any, Dict, List
import os
import logging

from app.core.db import SessionLocal
from app.core.config import settings
from app.models.db_models import Job, JobStatus, Video

logger = logging.getLogger(__name__)


def _load_whisper_model():
    logger.info(f"[TRANSCRIPTION] Loading Whisper model...")
    try:
        import whisper  # type: ignore
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[TRANSCRIPTION] Whisper not installed: {exc}", exc_info=True)
        raise RuntimeError(
            "Whisper is not installed. Install with `pip install openai-whisper` (requires ffmpeg)."
        ) from exc

    try:
        # Read device from env var first, fallback to settings
        device = os.getenv("WHISPER_DEVICE", settings.whisper_device)
        logger.info(f"[TRANSCRIPTION] Loading model 'small' on device='{device}'")
        model = whisper.load_model("small", device=device)
        logger.info(f"[TRANSCRIPTION] Whisper model loaded successfully")
        return model
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[TRANSCRIPTION] Failed to load Whisper model: {exc}", exc_info=True)
        raise RuntimeError(f"Failed to load Whisper model: {exc}") from exc


def _transcribe_audio(audio_path: Path) -> Dict[str, Any]:
    logger.info(f"[TRANSCRIPTION] Starting transcription of {audio_path}")
    try:
        model = _load_whisper_model()
        # Read device from env var first, fallback to settings
        device = os.getenv("WHISPER_DEVICE", settings.whisper_device)
        # Enable FP16 for CUDA to speed up inference
        fp16 = device == "cuda"
        logger.info(f"[TRANSCRIPTION] Transcribing with device='{device}', fp16={fp16}")
        
        result = model.transcribe(str(audio_path), verbose=False, fp16=fp16)
        logger.info(f"[TRANSCRIPTION] Transcription complete: {len(result.get('segments', []))} segments")
        return result
    except Exception as e:
        logger.error(f"[TRANSCRIPTION] Transcription failed: {e}", exc_info=True)
        raise


def _serialize_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info(f"[TRANSCRIPTION] Serializing {len(raw_segments)} raw segments")
    segments: List[Dict[str, Any]] = []
    for seg in raw_segments:
        segments.append(
            {
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "text": (seg.get("text") or "").strip(),
                "avg_logprob": float(seg.get("avg_logprob") or 0.0),
                "no_speech_prob": float(seg.get("no_speech_prob") or 0.0),
            }
        )
    logger.info(f"[TRANSCRIPTION] Serialized {len(segments)} segments")
    return segments

def process_transcription_job(job_id: str) -> None:
    """Background task to transcribe the ingested audio file."""
    logger.info(f"[TRANSCRIPTION] Starting transcription job: {job_id}")
    db = SessionLocal()
    try:
        job: Job | None = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            logger.error(f"[TRANSCRIPTION] Job not found: {job_id}")
            return

        # Idempotency: if transcript already present, mark success.
        video: Video = db.query(Video).filter(Video.id == job.video_id).one()
        logger.info(f"[TRANSCRIPTION] Processing video: {video.id}, title={video.title}")
        
        existing_transcript = None
        if video.analysis_data and isinstance(video.analysis_data, dict):
            existing_transcript = video.analysis_data.get("transcript")
        if existing_transcript:
            logger.info(f"[TRANSCRIPTION] Transcript already exists ({len(existing_transcript)} segments), skipping")
            job.status = JobStatus.SUCCESS
            job.step = "transcribing"
            job.progress = 1.0
            db.commit()
            return

        logger.info(f"[TRANSCRIPTION] No existing transcript, proceeding with transcription")
        job.status = JobStatus.RUNNING
        job.step = "transcribing"
        job.progress = 0.0
        db.commit()
        db.refresh(job)
        
        if not video.audio_path:
            logger.error(f"[TRANSCRIPTION] Audio path missing for video {video.id}")
            raise RuntimeError("Audio path missing; ingest step must complete first")

        audio_path = Path(video.audio_path)
        if not audio_path.exists():
            logger.error(f"[TRANSCRIPTION] Audio file not found: {audio_path}")
            raise RuntimeError(f"Audio file not found at {audio_path}")

        logger.info(f"[TRANSCRIPTION] Audio file exists: {audio_path}, size={audio_path.stat().st_size} bytes")
        
        logger.info(f"[TRANSCRIPTION] Calling _transcribe_audio()...")
        result = _transcribe_audio(audio_path)
        
        logger.info(f"[TRANSCRIPTION] Transcribe result received, processing segments...")
        segments = _serialize_segments(result.get("segments", []))
        logger.info(f"[TRANSCRIPTION] Parsed {len(segments)} segments from transcription")

        analysis_data = video.analysis_data or {}
        analysis_data["transcript"] = segments
        analysis_data["transcript_language"] = result.get("language")
        video.analysis_data = analysis_data
        
        logger.info(f"[TRANSCRIPTION] Saving to database...")
        job.status = JobStatus.SUCCESS
        job.progress = 1.0
        db.commit()
        logger.info(f"[TRANSCRIPTION] Job SUCCESS: {job_id}")

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[TRANSCRIPTION] Job FAILED with exception: {exc}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()

