import os
import pickle
import logging
from pathlib import Path
from typing import List, Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import settings

logger = logging.getLogger(__name__)

# Scopes required for uploading
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = Path("client_secrets.json")
TOKEN_PICKLE_FILE = Path("token.pickle")

def get_authenticated_service():
    """
    Authenticate and return the YouTube service object.
    Requires client_secrets.json to be present in the backend directory for first run.
    """
    credentials = None
    
    # Check for existing token
    if TOKEN_PICKLE_FILE.exists():
        with open(TOKEN_PICKLE_FILE, "rb") as token:
            credentials = pickle.load(token)

    # Refresh or create credentials
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not CLIENT_SECRETS_FILE.exists():
                logger.warning(f"[YOUTUBE UPLOAD] {CLIENT_SECRETS_FILE} not found. functionality disabled.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES
            )
            credentials = flow.run_local_server(port=0)
            
        # Save credentials
        with open(TOKEN_PICKLE_FILE, "wb") as token:
            pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)

def upload_video(
    file_path: Path,
    title: str,
    description: str,
    tags: List[str] = [],
    privacy_status: str = "private"
) -> Optional[str]:
    """
    Upload a video to YouTube.
    Returns the Video ID if successful, None otherwise.
    """
    if not file_path.exists():
        logger.error(f"[YOUTUBE UPLOAD] File not found: {file_path}")
        return None

    try:
        youtube = get_authenticated_service()
        if not youtube:
            logger.warning("[YOUTUBE UPLOAD] Authentication failed or configured. Skipping upload.")
            return None

        body = {
            "snippet": {
                "title": title[:100],  # Max 100 chars
                "description": description[:5000], # Max 5000 chars
                "tags": tags,
                "categoryId": "22",  # People & Blogs
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            }
        }

        logger.info(f"[YOUTUBE UPLOAD] Uploading {file_path.name} as '{title}'...")
        
        # Resumable upload
        media = MediaFileUpload(
            str(file_path),
            chunksize=-1, 
            resumable=True,
            mimetype="video/mp4" # Assuming mp4
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"[YOUTUBE UPLOAD] Uploaded {int(status.progress() * 100)}%")

        logger.info(f"[YOUTUBE UPLOAD] Upload Complete! Video ID: {response['id']}")
        return response['id']

    except Exception as e:
        logger.error(f"[YOUTUBE UPLOAD] Error uploading video: {e}", exc_info=True)
        return None
