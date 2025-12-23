"""Test new YouTube video with manual pipeline"""
import sys
sys.path.insert(0, 'D:/clipcut/backend')

from app.services.youtube_service import download_youtube_video
from app.services.ingest_service import process_ingest_job
from app.services.transcription_service import process_transcription_job
from app.services.analysis_service import process_analysis_job
from app.services.clip_service import process_clip_generation_job
from app.core.db import SessionLocal
from app.models.db_models import Job, JobStatus
import uuid

# YouTube URL
url = "https://www.youtube.com/watch?v=yeWzP5VfUNM"

db = SessionLocal()

try:
    # Step 1: Download YouTube video
    print(f"Downloading video from: {url}")
    video, download_job = download_youtube_video(url, db, title="Test Video")
    print(f"Video ID: {video.id}")
    print(f"Download Job ID: {download_job.id}")
    
    # Wait for download to complete
    print("\nProcessing download job...")
    from app.services.youtube_service import process_youtube_download_job
    process_youtube_download_job(download_job.id)
    
    db.refresh(download_job)
    print(f"Download status: {download_job.status}")
    if download_job.status != JobStatus.SUCCESS:
        print(f"Download failed: {download_job.error_message}")
        sys.exit(1)
    
    # Step 2: Ingest
    print("\nCreating ingest job...")
    ingest_job = Job(
        id=str(uuid.uuid4()),
        video_id=video.id,
        job_type="ingest",
        status=JobStatus.PENDING,
    )
    db.add(ingest_job)
    db.commit()
    db.refresh(ingest_job)
    
    print(f"Running ingest job {ingest_job.id}...")
    process_ingest_job(ingest_job.id)
    
    db.refresh(ingest_job)
    print(f"Ingest status: {ingest_job.status}")
    if ingest_job.status != JobStatus.SUCCESS:
        print(f"Ingest failed: {ingest_job.error_message}")
        sys.exit(1)
    
    # Step 3: Transcription
    print("\nCreating transcription job...")
    trans_job = Job(
        id=str(uuid.uuid4()),
        video_id=video.id,
        job_type="transcription",
        status=JobStatus.PENDING,
    )
    db.add(trans_job)
    db.commit()
    db.refresh(trans_job)
    
    print(f"Running transcription job {trans_job.id}...")
    process_transcription_job(trans_job.id)
    
    db.refresh(trans_job)
    print(f"Transcription status: {trans_job.status}")
    if trans_job.status != JobStatus.SUCCESS:
        print(f"Transcription failed: {trans_job.error_message}")
        sys.exit(1)
    
    # Step 4: Analysis
    print("\nCreating analysis job...")
    analysis_job = Job(
        id=str(uuid.uuid4()),
        video_id=video.id,
        job_type="analysis",
        status=JobStatus.PENDING,
    )
    db.add(analysis_job)
    db.commit()
    db.refresh(analysis_job)
    
    print(f"Running analysis job {analysis_job.id}...")
    process_analysis_job(analysis_job.id)
    
    db.refresh(analysis_job)
    print(f"Analysis status: {analysis_job.status}")
    if analysis_job.status != JobStatus.SUCCESS:
        print(f"Analysis failed: {analysis_job.error_message}")
        sys.exit(1)
    
    # Step 5: Clip Generation
    print("\nCreating clip generation job...")
    gen_job = Job(
        id=str(uuid.uuid4()),
        video_id=video.id,
        job_type="generate_clips",
        status=JobStatus.PENDING,
    )
    db.add(gen_job)
    db.commit()
    db.refresh(gen_job)
    
    print(f"Running clip generation job {gen_job.id}...")
    process_clip_generation_job(gen_job.id)
    
    db.refresh(gen_job)
    print(f"Clip generation status: {gen_job.status}")
    if gen_job.status != JobStatus.SUCCESS:
        print(f"Clip generation failed: {gen_job.error_message}")
        sys.exit(1)
    
    # Show results
    print("\n" + "="*50)
    print("PIPELINE COMPLETE!")
    print("="*50)
    print(f"Video ID: {video.id}")
    
    from app.models.db_models import Clip
    clips = db.query(Clip).filter(Clip.video_id == video.id).order_by(Clip.rank).all()
    print(f"\nGenerated {len(clips)} clips:")
    for clip in clips:
        print(f"  Clip {clip.rank}: {clip.start_time:.1f}s-{clip.end_time:.1f}s, score={clip.engagement_score}, path={clip.output_path}")

finally:
    db.close()
