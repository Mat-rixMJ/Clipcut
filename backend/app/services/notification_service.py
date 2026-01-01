import logging
import requests
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_clip_to_telegram(clip_path: Path, caption: str) -> None:
    """
    Send a video clip to Telegram.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("[TELEGRAM] Token or Chat ID not set. Skipping notification.")
        return

    if not clip_path.exists():
        logger.error(f"[TELEGRAM] File not found: {clip_path}")
        return

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    
    logger.info(f"[TELEGRAM] Sending {clip_path.name} to chat {chat_id}...")
    
    try:
        with clip_path.open("rb") as video_file:
            files = {"video": video_file}
            data = {"chat_id": chat_id, "caption": caption}
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                logger.info("[TELEGRAM] Video sent successfully.")
            else:
                logger.error(f"[TELEGRAM] Failed to send video: {response.text}")
    except Exception as e:
        logger.error(f"[TELEGRAM] Error sending video: {e}", exc_info=True)
