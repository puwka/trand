"""
Unified Video model for multi-platform trend ingestion.
Every adapter converts platform-specific data into this model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Video:
    """Unified video representation across TikTok, YouTube, Instagram."""

    platform: str
    video_id: str
    url: str
    author_id: str = ""
    author_name: str = ""
    author_followers: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    publish_time: Optional[datetime] = None
    duration: int = 0  # seconds
    title: str = ""
    description: str = ""
    hashtags: list[str] = field(default_factory=list)
    sound_id: str = ""
    thumbnail_url: str = ""
    comments_disabled: bool = False
    raw_payload: Optional[dict[str, Any]] = None

    def __hash__(self) -> int:
        return hash((self.platform, self.video_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Video):
            return False
        return self.platform == other.platform and self.video_id == other.video_id
