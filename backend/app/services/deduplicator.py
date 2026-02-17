"""
Deduplication logic for videos across platforms.
Removes duplicates by video_id, sound_id, and similar content.
"""

from __future__ import annotations

import logging
from typing import List

from app.models.video_model import Video

logger = logging.getLogger(__name__)


def _cosine_similarity(a: str, b: str) -> float:
    """Simple word-based cosine similarity between two strings."""
    if not a or not b:
        return 0.0
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / (len(wa) * len(wb)) ** 0.5


def deduplicate(videos: List[Video]) -> List[Video]:
    """
    Remove duplicate videos:
    - Same video_id across platforms (keep first)
    - Reposts: same sound_id (TikTok)
    - Highly similar titles (cosine > 0.8)
    - Same duration ± 2 seconds with similar title
    """
    if not videos:
        return []

    seen_ids: set[tuple[str, str]] = set()
    seen_sounds: set[tuple[str, str]] = set()
    result: List[Video] = []

    for v in videos:
        key = (v.platform, v.video_id)
        if key in seen_ids:
            continue
        seen_ids.add(key)

        if v.sound_id and v.platform == "tiktok":
            sound_key = (v.platform, v.sound_id)
            if sound_key in seen_sounds:
                continue
            seen_sounds.add(sound_key)

        is_dupe = False
        for r in result:
            if _is_repost(v, r):
                is_dupe = True
                break
        if is_dupe:
            continue

        result.append(v)

    logger.info(f"Deduplicated: {len(videos)} -> {len(result)} videos")
    return result


def _is_repost(v: Video, existing: Video) -> bool:
    """Check if v is likely a repost of existing."""
    if v.platform == existing.platform and v.video_id == existing.video_id:
        return True
    if v.sound_id and v.sound_id == existing.sound_id and v.platform == "tiktok":
        return True
    sim = _cosine_similarity(v.title or "", existing.title or "")
    if sim >= 0.8:
        return True
    if abs(v.duration - existing.duration) <= 2 and sim >= 0.5:
        return True
    return False
