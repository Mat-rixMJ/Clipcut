import sys
import os
import sqlite3
from pathlib import Path

# Adjust path to DB file based on .env or default
DB_PATH = Path("d:/clipcut/backend/db/app.db")

def inspect_schema():
    if not DB_PATH.exists():
        print(f"DB file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for t in tables:
        print(f"- {t[0]}")
        
    print("\n--- Columns in 'clips' ---")
    try:
        cursor.execute("PRAGMA table_info(clips);")
        columns = cursor.fetchall()
        for c in columns:
            print(c)
    except Exception as e:
        print(f"Error checking clips: {e}")
        
    print("\n--- Columns in 'videos' ---")
    try:
        cursor.execute("PRAGMA table_info(videos);")
        columns = cursor.fetchall()
        for c in columns:
            print(c)
    except Exception as e:
        print(f"Error checking videos: {e}")

    conn.close()

if __name__ == "__main__":
    with open("schema_output.txt", "w") as f:
        sys.stdout = f
        inspect_schema()
