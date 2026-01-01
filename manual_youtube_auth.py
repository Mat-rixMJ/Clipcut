import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BACKEND_DIR = Path("backend")
CLIENT_SECRETS_FILE = BACKEND_DIR / "client_secrets.json"
TOKEN_PICKLE_FILE = BACKEND_DIR / "token.pickle"

def manual_auth():
    print("=" * 60)
    print("YouTube API - Manual Authentication")
    print("=" * 60)
    
    if not CLIENT_SECRETS_FILE.exists():
        print(f"\nERROR: {CLIENT_SECRETS_FILE} not found!")
        return
    
    credentials = None
    
    # Check for existing token
    if TOKEN_PICKLE_FILE.exists():
        with open(TOKEN_PICKLE_FILE, "rb") as token:
            credentials = pickle.load(token)
    
    # If no valid credentials, do manual flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("\nRefreshing expired credentials...")
            credentials.refresh(Request())
        else:
            print("\nStarting manual OAuth flow...")
            print("\nSTEP 1: Copy this URL and open it in your browser:")
            print("-" * 60)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), 
                SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # Manual copy/paste mode
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(auth_url)
            print("-" * 60)
            
            print("\nSTEP 2: After authorizing, Google will show you a code.")
            print("Copy that code and paste it here:")
            code = input("\nEnter authorization code: ").strip()
            
            print("\nExchanging code for credentials...")
            flow.fetch_token(code=code)
            credentials = flow.credentials
        
        # Save credentials
        print("\nSaving credentials...")
        with open(TOKEN_PICKLE_FILE, "wb") as token:
            pickle.dump(credentials, token)
        
        print("\n" + "=" * 60)
        print("SUCCESS! Authentication complete.")
        print(f"Token saved to: {TOKEN_PICKLE_FILE}")
        print("=" * 60)
    else:
        print("\nAlready authenticated! Token is valid.")

if __name__ == "__main__":
    manual_auth()
