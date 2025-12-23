"""Manual pipeline test script"""
import sys
sys.path.insert(0, 'D:/clipcut/backend')

from app.services.transcription_service import process_transcription_job
from app.services.analysis_service import process_analysis_job
from app.services.clip_service import process_clip_generation_job
from app.core.db import SessionLocal
from app.models.db_models import Job, JobStatus
import uuid

video_id = "37298f10-c89b-4858-9ea3-779551147106"

db = SessionLocal()

# Create and run transcription job
print("Creating transcription job...")
trans_job = Job(
    id=str(uuid.uuid4()),
    video_id=video_id,
    job_type="transcription",
    status=JobStatus.PENDING,
)
db.add(trans_job)
db.commit()
db.refresh(trans_job)

print(f"Running transcription job {trans_job.id}...")
process_transcription_job(trans_job.id)

# Check result
db.refresh(trans_job)
print(f"Transcription status: {trans_job.status}")
if trans_job.error_message:
    print(f"Error: {trans_job.error_message}")

if trans_job.status == JobStatus.SUCCESS:
    # Create and run analysis job
    print("\nCreating analysis job...")
    analysis_job = Job(
        id=str(uuid.uuid4()),
        video_id=video_id,
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
    if analysis_job.error_message:
        print(f"Error: {analysis_job.error_message}")

    if analysis_job.status == JobStatus.SUCCESS:
        # Create and run clip generation job
        print("\nCreating clip generation job...")
        gen_job = Job(
            id=str(uuid.uuid4()),
            video_id=video_id,
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
        if gen_job.error_message:
            print(f"Error: {gen_job.error_message}")

db.close()
print("\nDone!")
