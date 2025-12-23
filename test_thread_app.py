"""Test if threading works in the FastAPI context"""
import threading
import time
from pathlib import Path

def test_thread_worker(video_id):
    """Simple worker that writes to a file"""
    log_file = Path(f"D:/clipcut/thread_test_{video_id}.txt")
    log_file.write_text(f"Thread started at {time.time()}\n")
    time.sleep(2)
    with log_file.open("a") as f:
        f.write(f"Thread still running at {time.time()}\n")
    time.sleep(2)
    with log_file.open("a") as f:
        f.write(f"Thread completed at {time.time()}\n")

from fastapi import FastAPI

app = FastAPI()

@app.get("/test-thread/{video_id}")
def test_thread(video_id: str):
    thread = threading.Thread(target=test_thread_worker, args=(video_id,), daemon=True)
    thread.start()
    return {"status": "thread started", "video_id": video_id}

@app.get("/health")
def health():
    return {"status": "ok"}
