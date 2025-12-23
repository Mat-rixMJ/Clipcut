"""Adaptive pipeline monitoring script - waits for each stage to complete"""
import sys
import time
import requests
from datetime import datetime

def monitor_pipeline(video_id: str, base_url: str = "http://127.0.0.1:8000"):
    """Monitor pipeline until completion with adaptive waiting"""
    
    print(f"\nMonitoring pipeline for video: {video_id}")
    print("=" * 60)
    
    last_status = {}
    stage_start = {}
    check_count = 0
    max_checks = 60  # Max 30 minutes (60 checks * 30s)
    
    while check_count < max_checks:
        check_count += 1
        
        try:
            resp = requests.get(f"{base_url}/api/videos/{video_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Check #{check_count}")
            
            # Track each job
            all_done = True
            has_running = False
            
            for job in data.get("jobs", []):
                job_type = job.get("job_type")
                status = job.get("status")
                step = job.get("step", "")
                progress = int((job.get("progress") or 0) * 100)
                
                # Check if this job changed status
                job_key = f"{job_type}:{status}"
                if job_key != last_status.get(job_type):
                    # Status changed - log timing
                    if last_status.get(job_type):
                        prev_status = last_status[job_type].split(":")[1]
                        if prev_status == "RUNNING" and status == "SUCCESS":
                            elapsed = time.time() - stage_start.get(job_type, time.time())
                            print(f"  ✓ {job_type} completed in {elapsed:.1f}s")
                    
                    last_status[job_type] = job_key
                    
                    if status == "RUNNING":
                        stage_start[job_type] = time.time()
                
                # Display current status
                status_icon = {
                    "SUCCESS": "✓",
                    "RUNNING": "⏳",
                    "FAILED": "✗",
                    "PENDING": "○"
                }.get(status, "?")
                
                print(f"  {status_icon} {job_type}: {status} - {step} ({progress}%)")
                
                if status == "RUNNING":
                    has_running = True
                    all_done = False
                elif status in ["PENDING", "FAILED"]:
                    all_done = False
            
            # Check for clips
            clips = data.get("clips", [])
            if clips:
                print(f"\n  🎬 {len(clips)} clips generated!")
                for clip in sorted(clips, key=lambda c: c.get("rank", 0)):
                    start = clip.get("start_time", 0)
                    end = clip.get("end_time", 0)
                    score = clip.get("engagement_score", 0)
                    rank = clip.get("rank", 0)
                    print(f"     Clip {rank}: {start:.1f}s-{end:.1f}s (score: {score})")
                break  # Done!
            
            # If all jobs done but no clips, check for errors
            if all_done:
                failed_jobs = [j for j in data.get("jobs", []) if j.get("status") == "FAILED"]
                if failed_jobs:
                    print("\n  ⚠️  Pipeline failed:")
                    for job in failed_jobs:
                        error = job.get("error_message", "Unknown error")
                        print(f"     {job.get('job_type')}: {error}")
                else:
                    print("\n  ⚠️  All jobs complete but no clips generated")
                break
            
            # Adaptive sleep: shorter when actively running, longer when idle
            sleep_time = 10 if has_running else 30
            time.sleep(sleep_time)
            
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  API error: {e}")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            break
    
    if check_count >= max_checks:
        print("\n  ⏱️  Max monitoring time reached (30 min)")
    
    print("\n" + "=" * 60)
    print(f"Monitoring complete for {video_id}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monitor_pipeline.py <video_id>")
        sys.exit(1)
    
    video_id = sys.argv[1]
    monitor_pipeline(video_id)
