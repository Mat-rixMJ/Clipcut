import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.config import settings
from app.services.scoring_service import generate_video_title, generate_short_caption

def test_gemini():
    print(f"LLM Enabled: {settings.llm_enabled}")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Google Key Configured: {bool(settings.google_api_key)}")
    
    if settings.google_api_key:
        print(f"Google Key (first 5 chars): {settings.google_api_key[:5]}...")
    else:
        print("Google Key is MISSING in settings!")

    transcript = "This is a transcript about a cat jumping over a fence. The cat is very agile and lands perfectly on its feet. It's truly an amazing feat of feline athleticism."
    
    print("\n--- Testing Title Generation ---")
    try:
        title = generate_video_title(transcript)
        print(f"Generated Title: '{title}'")
    except Exception as e:
        print(f"Title Generation Failed: {e}")

    print("\n--- Testing Caption Generation ---")
    try:
        caption = generate_short_caption(transcript)
        print(f"Generated Caption: '{caption}'")
    except Exception as e:
        print(f"Caption Generation Failed: {e}")

if __name__ == "__main__":
    test_gemini()
