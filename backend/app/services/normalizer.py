"""
Normalizer service for Video model consistency.
Adapters already normalize; this provides additional enrichment if needed.
"""

from __future__ import annotations

import logging
from typing import List

from app.models.video_model import Video

logger = logging.getLogger(__name__)


def normalize_videos(videos: List[Video]) -> List[Video]:
    """
    Apply any post-normalization to videos.
    Currently a pass-through; extensible for future enrichment.
    """
    return list(videos)
