"""Video-related Pydantic models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlatformEnum(str, Enum):
    """Supported short-video platforms."""

    TIKTOK = "tiktok"
    REELS = "reels"
    SHORTS = "shorts"


class VideoCandidate(BaseModel):
    """Unified video structure from TikTok, Instagram Reels, or YouTube Shorts."""

    platform: PlatformEnum
    external_id: str = Field(..., description="Platform-native video ID")
    url: str = Field(..., description="Full link to the video")
    description: str = Field(default="", description="Caption/caption text")
    stats: dict[str, int] = Field(
        default_factory=dict,
        description="Normalized stats: views, likes, comments",
    )
    upload_date: datetime = Field(..., description="When the video was published")
    duration: int = Field(default=0, description="Duration in seconds")

    class Config:
        use_enum_values = True
