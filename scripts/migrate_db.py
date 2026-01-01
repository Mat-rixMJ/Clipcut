import sqlite3
from pathlib import Path

DB_PATH = Path("d:/clipcut/backend/db/app.db")

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Attempting to add 'hashtags' column to 'clips' table...")
        cursor.execute("ALTER TABLE clips ADD COLUMN hashtags TEXT")
        conn.commit()
        print("Success: 'hashtags' column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column 'hashtags' already exists. Skipping.")
        else:
            print(f"Error migrating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
