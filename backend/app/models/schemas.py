from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    TIKTOK = "tiktok"
    REELS = "reels"
    SHORTS = "shorts"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SourceCreate(BaseModel):
    platform: Platform
    url: str
    status: SourceStatus = SourceStatus.ACTIVE


class SourceResponse(BaseModel):
    id: str
    platform: Platform
    url: str
    status: SourceStatus
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    keyword: str
    description: Optional[str] = None


class TopicResponse(BaseModel):
    id: str
    keyword: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoResponse(BaseModel):
    id: str
    source_id: str
    external_id: str
    title: str
    description: Optional[str] = None
    ai_summary: Optional[str] = None
    virality_score: int = Field(ge=1, le=10)
    is_viral: bool
    storage_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
