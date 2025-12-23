#!/usr/bin/env python3
"""
Real-time log monitor for ClipCut pipeline.
Shows pipeline.log and server.log side-by-side.
"""
import time
import os
import sys
from pathlib import Path
from collections import deque

PIPELINE_LOG = Path("D:/clipcut/pipeline.log")
SERVER_LOG = Path("D:/clipcut/server.log")

# Store last 20 lines from each log
pipeline_lines = deque(maxlen=20)
server_lines = deque(maxlen=20)

def read_new_lines(filepath, last_pos):
    """Read new lines from file since last position."""
    if not filepath.exists():
        return [], 0
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_pos)
            new_lines = f.readlines()
            new_pos = f.tell()
        return new_lines, new_pos
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return [], last_pos

def main():
    print("=" * 80)
    print("ClipCut Pipeline Monitor")
    print("=" * 80)
    print()
    print(f"Monitoring:")
    print(f"  Pipeline: {PIPELINE_LOG}")
    print(f"  Server:   {SERVER_LOG}")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    pipeline_pos = 0
    server_pos = 0
    
    try:
        while True:
            # Read new lines
            pipeline_new, pipeline_pos = read_new_lines(PIPELINE_LOG, pipeline_pos)
            server_new, server_pos = read_new_lines(SERVER_LOG, server_pos)
            
            # Add to deques
            for line in pipeline_new:
                pipeline_lines.append(("PIPELINE", line.rstrip()))
            for line in server_new:
                server_lines.append(("SERVER", line.rstrip()))
            
            # Print new lines with timestamps
            if pipeline_new or server_new:
                timestamp = time.strftime("%H:%M:%S")
                
                for source, line in pipeline_new:
                    print(f"[{timestamp}] [PIPELINE] {line}")
                
                for source, line in server_new:
                    # Only show [TRANSCRIPTION] and [ANALYSIS] logs
                    if "[TRANSCRIPTION]" in line or "[ANALYSIS]" in line:
                        print(f"[{timestamp}] {line}")
            
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
