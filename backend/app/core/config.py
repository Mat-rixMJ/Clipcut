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
    ollama_base_url: str = "http://localhost:11434"
    
    # GPU Acceleration Settings
    whisper_device: str = Field(default="cpu", description="Whisper device: 'cpu' or 'cuda'")
    ffmpeg_hwaccel: str = Field(default="", description="FFmpeg hardware acceleration: '', 'cuda', 'd3d11va', 'dxva2', 'qsv'")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure storage directories exist early so other modules can rely on them
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "videos").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "audio").mkdir(parents=True, exist_ok=True)
# Legacy artifacts directory
(settings.data_dir / "artifacts").mkdir(parents=True, exist_ok=True)

# New structured pipeline directories
(settings.data_dir / "transcripts").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "heatmap").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "renders").mkdir(parents=True, exist_ok=True)
