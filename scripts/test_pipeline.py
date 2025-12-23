"""
Example script to test the ClipCut API

This demonstrates how to:
1. Process a YouTube video
2. Monitor job progress
3. Download generated clips
"""
import time
import requests

BASE_URL = "http://localhost:8000/api"

def process_youtube_video(youtube_url: str):
    """Process a YouTube video through the complete pipeline."""
    print(f"🎬 Starting to process: {youtube_url}")
    
    # Start the full pipeline
    response = requests.post(
        f"{BASE_URL}/videos/process-youtube",
        json={"url": youtube_url}
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.json()}")
        return None
    
    data = response.json()
    video_id = data["video_id"]
    print(f"✅ Processing started! Video ID: {video_id}")
    
    return video_id


def check_status(video_id: str):
    """Check processing status."""
    response = requests.get(f"{BASE_URL}/videos/{video_id}")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.json()}")
        return None
    
    return response.json()


def monitor_progress(video_id: str, check_interval: int = 5):
    """Monitor processing progress until complete."""
    print("\n📊 Monitoring progress...")
    
    while True:
        status = check_status(video_id)
        if not status:
            break
        
        jobs = status.get("jobs", [])
        
        # Display job status
        print("\n" + "="*60)
        print(f"Video: {status.get('title', 'Unknown')}")
        print(f"Duration: {status.get('duration_seconds', 0):.1f}s")
        print("-"*60)
        
        all_complete = True
        for job in jobs:
            status_icon = {
                "SUCCESS": "✅",
                "RUNNING": "⏳",
                "FAILED": "❌",
                "PENDING": "⏸️"
            }.get(job["status"], "❓")
            
            progress = job.get("progress", 0) or 0
            step = job.get("step", "")
            
            print(f"{status_icon} {job['job_type']:15} | {job['status']:8} | {progress*100:5.1f}% | {step}")
            
            if job["status"] in ["PENDING", "RUNNING"]:
                all_complete = False
            elif job["status"] == "FAILED":
                print(f"   Error: {job.get('error_message', 'Unknown error')}")
        
        print("="*60)
        
        if all_complete:
            print("\n🎉 All processing complete!")
            break
        
        time.sleep(check_interval)
    
    return status


def download_clips(video_id: str, output_dir: str = "."):
    """Download all generated clips."""
    print(f"\n📥 Downloading clips...")
    
    # Get clips
    response = requests.get(f"{BASE_URL}/videos/{video_id}/clips")
    
    if response.status_code != 200:
        print(f"❌ Error fetching clips: {response.json()}")
        return
    
    clips = response.json()
    
    if not clips:
        print("ℹ️  No clips generated yet")
        return
    
    print(f"\nFound {len(clips)} clips:")
    
    for clip in clips:
        if not clip.get("output_path"):
            print(f"⏳ Clip #{clip['rank']} - Not generated yet")
            continue
        
        # Download clip
        clip_response = requests.get(f"{BASE_URL}/videos/clips/{clip['id']}/download")
        
        if clip_response.status_code == 200:
            filename = f"{output_dir}/clip_{clip['rank']}_score_{clip['engagement_score']:.1f}.mp4"
            
            with open(filename, "wb") as f:
                f.write(clip_response.content)
            
            print(f"✅ Clip #{clip['rank']} - Score: {clip['engagement_score']:.1f}/10 - "
                  f"{clip['start_time']:.1f}s to {clip['end_time']:.1f}s - Saved: {filename}")
        else:
            print(f"❌ Failed to download clip #{clip['rank']}")


def main():
    """Main example workflow."""
    print("=" * 60)
    print("   ClipCut - YouTube to Shorts Pipeline Test")
    print("=" * 60)
    
    # Example YouTube URL (replace with your own)
    youtube_url = input("\nEnter YouTube URL: ").strip()
    
    if not youtube_url:
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Example
        print(f"Using example URL: {youtube_url}")
    
    # Start processing
    video_id = process_youtube_video(youtube_url)
    
    if not video_id:
        return
    
    # Monitor progress
    final_status = monitor_progress(video_id, check_interval=10)
    
    if final_status:
        # Download clips
        download_clips(video_id)
        
        print("\n" + "=" * 60)
        print("✨ Complete! Your short clips are ready for upload!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
