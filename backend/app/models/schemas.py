from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.db_models import JobStatus


from enum import Enum

class VideoQuality(str, Enum):
    q480p = "480p"
    q720p = "720p"
    q1080p = "1080p"

class VideoFormat(str, Enum):
    h264 = "h264"
    h265 = "h265"
    av1 = "av1"
    vp9 = "vp9"

class TranscriptionModel(str, Enum):
    base = "base"
    small = "small"

class YouTubeDownloadRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    title: Optional[str] = Field(None, description="Optional custom title")
    download_quality: Optional[VideoQuality] = Field(VideoQuality.q1080p, description="Download quality: 480p, 720p, 1080p")
    min_duration: Optional[float] = Field(20.0, description="Minimum clip duration in seconds")
    max_duration: Optional[float] = Field(60.0, description="Maximum clip duration in seconds")
    min_engagement_score: Optional[int] = Field(7, description="Minimum engagement score threshold (1-10)")
    video_quality: Optional[VideoQuality] = Field(VideoQuality.q1080p, description="Video quality: 480p, 720p, 1080p")
    video_format: Optional[VideoFormat] = Field(VideoFormat.h264, description="Video codec: h264, h265, av1, vp9")
    transcription_model: Optional[TranscriptionModel] = Field(TranscriptionModel.small, description="Transcription model: base, small")


class VideoCreateResponse(BaseModel):
    video_id: str
    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus


class ProcessPipelineResponse(BaseModel):
    video_id: str
    initial_job_id: str
    message: str


class VideoDetail(BaseModel):
    id: str
    title: Optional[str]
    source_url: Optional[str]
    duration_seconds: Optional[float]
    fps: Optional[float]
    created_at: datetime
    updated_at: datetime
    raw_metadata: Optional[Any]
    analysis_data: Optional[Any]

    model_config = ConfigDict(from_attributes=True)


class JobInfo(BaseModel):
    id: str
    status: JobStatus
    job_type: str
    step: Optional[str]
    progress: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClipDetail(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    duration: Optional[float]
    engagement_score: float
    rank: int
    hashtags: Optional[str] = None
    output_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoWithJobs(VideoDetail):
    jobs: List[JobInfo] = Field(default_factory=list)
    clips: List[ClipDetail] = Field(default_factory=list)
