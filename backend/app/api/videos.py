from pathlib import Path
import threading

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import schemas
from app.models.db_models import Clip, Job, Video
from app.services.ingest_service import process_ingest_job, register_video_with_job, save_upload_file
from app.services.youtube_service import download_youtube_video, process_youtube_download_job
from app.services.analysis_service import process_analysis_job
from app.services.clip_service import process_clip_generation_job
from app.services.transcription_service import process_transcription_job

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=schemas.VideoCreateResponse)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = None,
    db: Session = Depends(get_db),
):
    video, job = register_video_with_job(db, file, title)
    try:
        save_upload_file(file, destination=Path(video.original_path))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    background_tasks.add_task(process_ingest_job, job.id)
    return schemas.VideoCreateResponse(video_id=video.id, job_id=job.id, status=job.status)


@router.get("/{video_id}", response_model=schemas.VideoWithJobs)
def get_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/youtube", response_model=schemas.ProcessPipelineResponse)
def download_from_youtube(
    request: schemas.YouTubeDownloadRequest,
    db: Session = Depends(get_db),
):
    """Download a video from YouTube and run the full pipeline."""
    video, job = download_youtube_video(request.url, db, request.title)

    # Run pipeline in a separate NON-daemon thread so it persists
    thread = threading.Thread(
        target=_run_full_pipeline,
        args=(video.id, job.id, None),
        daemon=False  # Critical: non-daemon so it completes even if request ends
    )
    thread.start()

    return schemas.ProcessPipelineResponse(
        video_id=video.id,
        initial_job_id=job.id,
        message="YouTube download started; pipeline is running."
    )


@router.post("/process-upload", response_model=schemas.ProcessPipelineResponse)
def process_upload_full_pipeline(
    file: UploadFile = File(...),
    title: str | None = None,
    db: Session = Depends(get_db),
):
    """Upload a local video and run the full pipeline."""
    video, ingest_job = register_video_with_job(db, file, title)
    try:
        save_upload_file(file, destination=Path(video.original_path))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Run pipeline in a separate NON-daemon thread so it persists
    thread = threading.Thread(
        target=_run_full_pipeline,
        args=(video.id, None, ingest_job.id),
        daemon=False  # Critical: non-daemon so it completes even if request ends
    )
    thread.start()

    return schemas.ProcessPipelineResponse(
        video_id=video.id,
        initial_job_id=ingest_job.id,
        message="Upload received; pipeline is running."
    )


@router.post("/{video_id}/ingest", response_model=schemas.JobResponse)
def start_ingest(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start ingesting a video (extract metadata and audio)."""
    video = db.query(Video).filter(Video.id == video_id).one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    from app.models.db_models import JobStatus
    import uuid
    
    job = Job(
        id=str(uuid.uuid4()),
        video_id=video_id,
        job_type="ingest",
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(process_ingest_job, job.id)
    
    return schemas.JobResponse(job_id=job.id, status=job.status)


@router.post("/{video_id}/analyze", response_model=schemas.JobResponse)
def start_analysis(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start analyzing a video for engagement detection."""
    video = db.query(Video).filter(Video.id == video_id).one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.audio_path or not video.duration_seconds:
        raise HTTPException(
            status_code=400,
            detail="Video must be ingested before analysis"
        )
    
    from app.models.db_models import JobStatus
    import uuid
    
    job = Job(
        id=str(uuid.uuid4()),
        video_id=video_id,
        job_type="analysis",
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(process_analysis_job, job.id)
    
    return schemas.JobResponse(job_id=job.id, status=job.status)


@router.post("/{video_id}/generate-clips", response_model=schemas.JobResponse)
def generate_clips(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate short clips from analyzed video."""
    video = db.query(Video).filter(Video.id == video_id).one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if there are clips to generate
    clips_count = db.query(Clip).filter(Clip.video_id == video_id).count()
    if clips_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Video must be analyzed before generating clips"
        )
    
    from app.models.db_models import JobStatus
    import uuid
    
    job = Job(
        id=str(uuid.uuid4()),
        video_id=video_id,
        job_type="generate_clips",
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(process_clip_generation_job, job.id)
    
    return schemas.JobResponse(job_id=job.id, status=job.status)


@router.get("/{video_id}/clips", response_model=list[schemas.ClipDetail])
def get_clips(video_id: str, db: Session = Depends(get_db)):
    """Get all clips for a video."""
    video = db.query(Video).filter(Video.id == video_id).one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    clips = db.query(Clip).filter(Clip.video_id == video_id).order_by(Clip.rank).all()
    return clips


@router.get("/clips/{clip_id}/download")
def download_clip(clip_id: str, db: Session = Depends(get_db)):
    """Download a generated clip."""
    clip = db.query(Clip).filter(Clip.id == clip_id).one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    if not clip.output_path:
        raise HTTPException(status_code=404, detail="Clip not yet generated")
    
    clip_path = Path(clip.output_path)
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip file not found")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"clip_{clip.rank}_{clip.engagement_score:.1f}.mp4"
    )


@router.post("/{video_id}/reprocess", response_model=schemas.ProcessPipelineResponse)
def reprocess_existing_video(
    video_id: str,
    db: Session = Depends(get_db),
):
    """
    Reprocess an existing video through the pipeline.
    Useful for testing - will skip already-completed stages via idempotency.
    """
    video = db.query(Video).filter(Video.id == video_id).one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Run pipeline from ingest onwards (no download job)
    thread = threading.Thread(
        target=_run_full_pipeline,
        args=(video.id, None, None),
        daemon=False
    )
    thread.start()

    return schemas.ProcessPipelineResponse(
        video_id=video.id,
        initial_job_id=None,
        message="Reprocessing started. Check job status for progress."
    )


@router.post("/process-youtube", response_model=schemas.ProcessPipelineResponse)
def process_youtube_full_pipeline(
    request: schemas.YouTubeDownloadRequest,
    db: Session = Depends(get_db),
):
    """
    Complete pipeline: Download YouTube video -> Ingest -> Transcribe -> Analyze/Score -> Generate Clips
    """
    video, download_job = download_youtube_video(request.url, db, request.title)

    # Run pipeline in a separate NON-daemon thread so it persists
    thread = threading.Thread(
        target=_run_full_pipeline,
        args=(video.id, download_job.id, None),
        daemon=False  # Critical: non-daemon so it completes even if request ends
    )
    thread.start()

    return schemas.ProcessPipelineResponse(
        video_id=video.id,
        initial_job_id=download_job.id,
        message="Processing started. Check job status for progress."
    )


def _run_full_pipeline(video_id: str, download_job_id: str | None, ingest_job_id: str | None):
    """Run the complete processing pipeline sequentially."""
    from app.core.db import SessionLocal
    from app.models.db_models import JobStatus
    import uuid
    import logging
    from pathlib import Path
    import time

    logger = logging.getLogger(__name__)
    log_file = Path("D:/clipcut/pipeline.log")
    
    def log_msg(msg: str):
        """Write to both logger and file for visibility"""
        logger.info(msg)
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass  # Don't let logging errors break the pipeline

    log_msg(f"[PIPELINE START] video_id={video_id}, download_job_id={download_job_id}, ingest_job_id={ingest_job_id}")

    db = SessionLocal()

    try:
        def run_with_retry(fn, job_id: str, job_name: str, attempts: int = 2) -> bool:
            """Run a job function and check its result with a fresh database session."""
            for attempt in range(attempts):
                try:
                    log_msg(f"Running {job_name} (attempt {attempt + 1}/{attempts}), job_id={job_id}")
                    fn(job_id)
                    
                    # Critical: Use a fresh session to check status
                    # Each service function creates its own session, so we need a fresh one to see their updates
                    check_db = SessionLocal()
                    try:
                        job_obj = check_db.query(Job).filter(Job.id == job_id).one()
                        status = job_obj.status
                        error = job_obj.error_message
                    finally:
                        check_db.close()
                    
                    log_msg(f"  {job_name} status: {status}")
                    if status == JobStatus.SUCCESS:
                        log_msg(f"{job_name} COMPLETED SUCCESSFULLY")
                        return True
                    log_msg(f"WARNING: {job_name} failed with status {status}: {error}")
                except Exception as e:
                    log_msg(f"ERROR in {job_name} attempt {attempt + 1}: {str(e)[:200]}")
                    import traceback
                    log_msg(f"Traceback: {traceback.format_exc()[:500]}")
            return False

        # Step 0: Download if requested (YouTube path)
        if download_job_id:
            log_msg("Step 0: YouTube Download")
            if not run_with_retry(process_youtube_download_job, download_job_id, "YouTube Download"):
                log_msg("PIPELINE STOPPED: YouTube download failed")
                return

        # Step 1: Ingest
        log_msg("Step 1: Ingest")
        if not ingest_job_id:
            ingest_job = Job(
                id=str(uuid.uuid4()),
                video_id=video_id,
                job_type="ingest",
                status=JobStatus.PENDING,
            )
            db.add(ingest_job)
            db.commit()
            db.refresh(ingest_job)
            ingest_job_id = ingest_job.id
            log_msg(f"  Created ingest job: {ingest_job_id}")

        if not run_with_retry(process_ingest_job, ingest_job_id, "Ingest"):
            log_msg("PIPELINE STOPPED: Ingest failed")
            return

        log_msg("Ingest completed successfully, proceeding to transcription")

        # Step 2: Transcription
        log_msg("Step 2: Creating transcription job")
        transcription_job = Job(
            id=str(uuid.uuid4()),
            video_id=video_id,
            job_type="transcription",
            status=JobStatus.PENDING,
        )
        db.add(transcription_job)
        db.commit()
        db.refresh(transcription_job)
        log_msg(f"  Created transcription job: {transcription_job.id}")

        if not run_with_retry(process_transcription_job, transcription_job.id, "Transcription"):
            log_msg("PIPELINE STOPPED: Transcription failed")
            return

        log_msg("Transcription completed successfully, proceeding to analysis")

        # Step 3: Heatmap scoring + clip detection
        log_msg("Step 3: Creating analysis job")
        analysis_job = Job(
            id=str(uuid.uuid4()),
            video_id=video_id,
            job_type="analysis",
            status=JobStatus.PENDING,
        )
        db.add(analysis_job)
        db.commit()
        db.refresh(analysis_job)
        log_msg(f"  Created analysis job: {analysis_job.id}")

        if not run_with_retry(process_analysis_job, analysis_job.id, "Analysis"):
            log_msg("PIPELINE STOPPED: Analysis failed")
            return

        log_msg("Analysis completed successfully, proceeding to clip generation")

        # Step 4: Clip rendering
        log_msg("Step 4: Creating clip generation job")
        generate_job = Job(
            id=str(uuid.uuid4()),
            video_id=video_id,
            job_type="generate_clips",
            status=JobStatus.PENDING,
        )
        db.add(generate_job)
        db.commit()
        db.refresh(generate_job)
        log_msg(f"  Created clip generation job: {generate_job.id}")

        run_with_retry(process_clip_generation_job, generate_job.id, "Clip Generation")
        log_msg(f"[PIPELINE COMPLETE] video_id={video_id}")

    except Exception as e:
        log_msg(f"[PIPELINE ERROR] {str(e)[:500]}")
        import traceback
        log_msg(f"Full traceback:\n{traceback.format_exc()}")
    finally:
        try:
            db.close()
        except Exception:
            pass  # Session may already be closed
