from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ClipCut Backend"
    debug: bool = False
    database_url: str = Field(default_factory=lambda: f"sqlite:///{Path('db') / 'app.db'}")
    data_dir: Path = Field(default=Path("data"))
    llm_enabled: bool = Field(default=True, description="Toggle LLM scoring on/off")
    llm_provider: str | None = Field(default=None, description="LLM provider: openai or ollama")
    llm_model: str | None = Field(default=None, description="Model name for LLM scoring")
    openai_api_key: str | None = None
    google_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    yt_cookies_browser: str | None = Field(default=None, description="Browser for yt-dlp --cookies-from-browser (e.g., 'chrome:Default', 'edge:Default', or None to disable)")
    yt_cookies_file: Path | None = Field(default=None, description="Path to a cookies.txt file for yt-dlp --cookies")
    yt_js_runtime: str | None = Field(default=None, description="JavaScript runtime for yt-dlp EJS (e.g., 'node', 'bun', 'deno')")
    
    # GPU Acceleration Settings
    whisper_device: str = Field(default="cpu", description="Whisper device: 'cpu' or 'cuda'")
    whisper_model: str = Field(default="small", description="Whisper model: 'base' or 'small'")
    ffmpeg_hwaccel: str = Field(default="", description="FFmpeg hardware acceleration: '', 'cuda', 'd3d11va', 'dxva2', 'qsv'")

    # Notification Settings
    telegram_bot_token: str | None = Field(default=None, description="Telegram Bot Token")
    telegram_chat_id: str | None = Field(default=None, description="Telegram Chat ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# ============================================================================
# UNIFIED STORAGE STRUCTURE
# ============================================================================
# All media files are stored in a single location: settings.data_dir
# 
# Directory structure:
#   D:\clipcut\data\
#   ├── videos/              # Original downloaded/uploaded videos (input)
#   ├── audio/               # Extracted audio from videos
#   ├── renders/             # Final rendered clips (output, organized by video_id)
#   │   └── {video_id}/      # Clips for specific video
#   │       ├── clip_1_*.mp4
#   │       ├── clip_2_*.mp4
#   │       └── ...
#   ├── transcripts/         # Metadata: transcription results (JSON)
#   ├── heatmap/             # Metadata: engagement heatmap (JSON)
#   └── artifacts/           # Legacy/temporary files (cleanup safe)
#
# IMPORTANT: Do NOT create separate storage under backend/ or other locations.
# Everything uses settings.data_dir = D:\clipcut\data
# ============================================================================

# Ensure all storage directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "videos").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "audio").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "renders").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "transcripts").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "heatmap").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "artifacts").mkdir(parents=True, exist_ok=True)

# Helper properties for easy access to storage subdirectories
class StoragePaths:
    """Centralized storage path management."""
    
    @staticmethod
    def videos_dir() -> Path:
        """Original videos directory."""
        return settings.data_dir / "videos"
    
    @staticmethod
    def audio_dir() -> Path:
        """Extracted audio directory."""
        return settings.data_dir / "audio"
    
    @staticmethod
    def renders_dir(video_id: str | None = None) -> Path:
        """Rendered clips directory. If video_id provided, returns video-specific folder."""
        renders = settings.data_dir / "renders"
        if video_id:
            return renders / str(video_id)
        return renders
    
    @staticmethod
    def transcripts_dir() -> Path:
        """Transcription metadata directory."""
        return settings.data_dir / "transcripts"
    
    @staticmethod
    def heatmap_dir() -> Path:
        """Heatmap metadata directory."""
        return settings.data_dir / "heatmap"
    
    @staticmethod
    def artifacts_dir() -> Path:
        """Legacy/temporary files directory."""
        return settings.data_dir / "artifacts"
    
    @staticmethod
    def all_dirs() -> dict[str, Path]:
        """Returns all storage directories as a dict."""
        return {
            "videos": StoragePaths.videos_dir(),
            "audio": StoragePaths.audio_dir(),
            "renders": StoragePaths.renders_dir(),
            "transcripts": StoragePaths.transcripts_dir(),
            "heatmap": StoragePaths.heatmap_dir(),
            "artifacts": StoragePaths.artifacts_dir(),
        }


# Export for easy import: from app.core.config import StoragePaths
