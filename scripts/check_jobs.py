import sqlite3
import sys

video_id = sys.argv[1] if len(sys.argv) > 1 else None

conn = sqlite3.connect('D:/clipcut/db/app.db')
cursor = conn.cursor()

if video_id:
    cursor.execute('SELECT id, video_id, job_type, status, step, error_message FROM jobs WHERE video_id = ? ORDER BY created_at', (video_id,))
else:
    cursor.execute('SELECT id, video_id, job_type, status, step, error_message FROM jobs ORDER BY created_at DESC LIMIT 10')

rows = cursor.fetchall()
print(f'Jobs for video {video_id if video_id else "latest"}:')
for row in rows:
    error = row[5] if row[5] else "None"
    print(f'  {row[2]}: {row[3]} [{row[4]}] - Error: {error[:100] if error != "None" else error}')

conn.close()
