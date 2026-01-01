import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.youtube_upload_service import get_authenticated_service

def setup_auth():
    print("--- YouTube Upload Setup ---")
    print("This script will help you authenticate with YouTube so the app can upload clips for you.")
    print("\n1. Make sure you have 'client_secrets.json' in the 'backend' folder.")
    
    secrets_path = Path("backend/client_secrets.json")
    if not secrets_path.exists():
        print(f"ERROR: {secrets_path} not found!")
        print("Please download it from Google Cloud Console and place it there.")
        return

    print("\n2. Launching browser for authentication...")
    try:
        service = get_authenticated_service()
        if service:
            print("\nSUCCESS! Authentication complete. 'token.pickle' created.")
            print("The app can now upload videos automatically.")
        else:
            print("\nFAILED. Could not create service.")
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    setup_auth()
