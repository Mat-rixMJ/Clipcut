from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from app.models.db_models import JobStatus


class YouTubeDownloadRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    title: Optional[str] = Field(None, description="Optional custom title")


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

    class Config:
        orm_mode = True

        # For Pydantic v1 compatibility; pydantic v2 uses model_config.from_attributes
        from_attributes = True  # type: ignore[attr-defined]


class JobInfo(BaseModel):
    id: str
    status: JobStatus
    job_type: str
    step: Optional[str]
    progress: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ClipDetail(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    duration: Optional[float]
    engagement_score: float
    rank: int
    output_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class VideoWithJobs(VideoDetail):
    jobs: List[JobInfo] = Field(default_factory=list)
    clips: List[ClipDetail] = Field(default_factory=list)
