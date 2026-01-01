import sys
import os
sys.path.append(os.getcwd())

from app.core.db import SessionLocal
from app.models.db_models import Job, JobStatus
from sqlalchemy import desc

def check_failed_jobs():
    db = SessionLocal()
    try:
        # Get the latest failed job
        failed_job = db.query(Job).filter(Job.status == JobStatus.FAILED).order_by(desc(Job.updated_at)).first()
        
        if failed_job:
            print(f"Failed Job ID: {failed_job.id}")
            print(f"Type: {failed_job.job_type}")
            print(f"Error Message: {failed_job.error_message}")
            print(f"Updated At: {failed_job.updated_at}")
        else:
            print("No failed jobs found.")
            
        # Also check the latest Analysis job to see what happened
        print("\n--- Latest Analysis Job ---")
        analysis_job = db.query(Job).filter(Job.job_type == 'analysis').order_by(desc(Job.created_at)).first()
        if analysis_job:
             print(f"Job ID: {analysis_job.id}")
             print(f"Status: {analysis_job.status}")
             print(f"Error: {analysis_job.error_message}")
             
    except Exception as e:
        with open("debug_output.txt", "w") as f:
            f.write(f"Error querying DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Redirect stdout to file
    with open("debug_output.txt", "w") as f:
        sys.stdout = f
        check_failed_jobs()
