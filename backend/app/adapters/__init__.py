"""Platform adapters for video ingestion."""

from .base_adapter import BaseAdapter
from .reels_adapter import ReelsAdapter
from .tiktok_adapter import TikTokAdapter
from .youtube_adapter import YouTubeAdapter

__all__ = [
    "BaseAdapter",
    "TikTokAdapter",
    "YouTubeAdapter",
    "ReelsAdapter",
]
