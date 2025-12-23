"""Service for transcribing audio to text using Whisper (local)."""
from pathlib import Path
from typing import Any, Dict, List

from app.core.db import SessionLocal
from app.core.config import settings
from app.models.db_models import Job, JobStatus, Video


def _load_whisper_model():
    try:
        import whisper  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Whisper is not installed. Install with `pip install openai-whisper` (requires ffmpeg)."
        ) from exc

    try:
        device = settings.whisper_device
        return whisper.load_model("small", device=device)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to load Whisper model: {exc}") from exc


def _transcribe_audio(audio_path: Path) -> Dict[str, Any]:
    model = _load_whisper_model()
    # Enable FP16 for CUDA to speed up inference
    fp16 = settings.whisper_device == "cuda"
    return model.transcribe(str(audio_path), verbose=False, fp16=fp16)


def _serialize_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    return segments


def process_transcription_job(job_id: str) -> None:
    """Background task to transcribe the ingested audio file."""
    db = SessionLocal()
    try:
        job: Job | None = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            return

        # Idempotency: if transcript already present, mark success.
        video: Video = db.query(Video).filter(Video.id == job.video_id).one()
        existing_transcript = None
        if video.analysis_data and isinstance(video.analysis_data, dict):
            existing_transcript = video.analysis_data.get("transcript")
        if existing_transcript:
            job.status = JobStatus.SUCCESS
            job.step = "transcribing"
            job.progress = 1.0
            db.commit()
            return

        job.status = JobStatus.RUNNING
        job.step = "transcribing"
        job.progress = 0.0
        db.commit()
        db.refresh(job)
        if not video.audio_path:
            raise RuntimeError("Audio path missing; ingest step must complete first")

        audio_path = Path(video.audio_path)
        if not audio_path.exists():
            raise RuntimeError(f"Audio file not found at {audio_path}")

        result = _transcribe_audio(audio_path)
        segments = _serialize_segments(result.get("segments", []))

        analysis_data = video.analysis_data or {}
        analysis_data["transcript"] = segments
        analysis_data["transcript_language"] = result.get("language")
        video.analysis_data = analysis_data

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
