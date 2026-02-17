"""
Collector service: orchestrates adapters, merges results, applies deduplication.
Apify adapters extend (not replace) existing when USE_APIFY=True.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

from app.adapters import ReelsAdapter, TikTokAdapter, YouTubeAdapter
from app.config import ingestion_settings
from app.models.video_model import Video
from app.services.deduplicator import deduplicate
from app.services.normalizer import normalize_videos

logger = logging.getLogger(__name__)


def _get_adapters(
    platforms: Optional[List[str]] = None,
) -> List:
    """Return enabled adapters. When USE_APIFY, skip old tiktok/reels (use Apify only)."""
    use_apify = bool(ingestion_settings.USE_APIFY and ingestion_settings.APIFY_TOKEN)
    all_adapters = {
        "tiktok": TikTokAdapter if ingestion_settings.TIKTOK_ENABLED and not use_apify else None,
        "youtube": YouTubeAdapter if ingestion_settings.YOUTUBE_API_KEY else None,
        "reels": ReelsAdapter if not use_apify else None,
    }
    selected = platforms or list(all_adapters.keys())
    return [
        all_adapters[p]()
        for p in selected
        if all_adapters.get(p) is not None
    ]


def _get_apify_adapters(platforms: Optional[List[str]] = None) -> List:
    """Return Apify adapters when USE_APIFY and token set. Extends, never replaces."""
    if not ingestion_settings.USE_APIFY or not ingestion_settings.APIFY_TOKEN:
        return []
    try:
        from app.adapters.apify import ApifyReelsAdapter, ApifyTikTokAdapter
    except ImportError as e:
        logger.warning("[APIFY] apify adapters import failed: %s", e)
        return []
    selected = platforms or ["tiktok", "reels"]
    adapters = []
    if "tiktok" in selected:
        adapters.append(ApifyTikTokAdapter())
    if "reels" in selected:
        adapters.append(ApifyReelsAdapter())
    return adapters


def _all_adapters(platforms: Optional[List[str]] = None) -> List:
    """Existing + Apify adapters. Apify runs in parallel, results merged."""
    base = _get_adapters(platforms)
    apify = _get_apify_adapters(platforms)
    return base + apify


async def fetch_trending(platforms: Optional[List[str]] = None) -> List[Video]:
    """Fetch trending videos from all platforms in parallel. Apify extends when USE_APIFY."""
    adapters = _all_adapters(platforms)
    if not adapters:
        logger.warning("No adapters enabled")
        return []

    start = time.monotonic()

    async def _fetch(a):
        try:
            return await a.fetch_trending()
        except Exception as e:
            logger.warning("[APIFY] fetch_trending failed for %s: %s", getattr(a, "platform", "?"), e)
            return []

    results = await asyncio.gather(*[_fetch(a) for a in adapters])
    flat = [v for sub in results for v in sub]
    flat = normalize_videos(flat)
    flat = deduplicate(flat)

    if ingestion_settings.DEBUG:
        elapsed = time.monotonic() - start
        per_platform = {a.platform: len(r) for a, r in zip(adapters, results)}
        logger.info(f"fetch_trending: {per_platform} in {elapsed:.2f}s, total={len(flat)}")

    return flat


async def fetch_by_keywords(
    keywords: List[str],
    platforms: Optional[List[str]] = None,
) -> List[Video]:
    """Fetch videos by keywords from all platforms in parallel. Apify extends when USE_APIFY."""
    adapters = _all_adapters(platforms)
    if not adapters:
        return []

    start = time.monotonic()

    async def _fetch(a):
        try:
            return await a.fetch_by_keywords(keywords)
        except Exception as e:
            logger.warning("[APIFY] fetch_by_keywords failed for %s: %s", getattr(a, "platform", "?"), e)
            return []

    results = await asyncio.gather(*[_fetch(a) for a in adapters])
    flat = [v for sub in results for v in sub]
    flat = normalize_videos(flat)
    flat = deduplicate(flat)

    if ingestion_settings.DEBUG:
        elapsed = time.monotonic() - start
        per_platform = {a.platform: len(r) for a, r in zip(adapters, results)}
        logger.info(f"fetch_by_keywords: {per_platform} in {elapsed:.2f}s, total={len(flat)}")

    return flat


async def fetch_from_sources(
    channel_list: List[str],
    platform: str,
) -> List[Video]:
    """
    Fetch videos from a list of channels/sources for a given platform.
    When USE_APIFY, runs both existing and Apify adapters in parallel, merges results.
    channel_list format depends on platform:
    - youtube: @username or UC... or youtube.com/channel/UC...
    - tiktok: @username
    - reels: username
    """
    adapters = _all_adapters([platform])
    if not adapters:
        return []

    start = time.monotonic()

    async def _fetch(a):
        try:
            return await a.fetch_from_sources(channel_list)
        except Exception as e:
            logger.warning("[APIFY] fetch_from_sources failed for %s: %s", getattr(a, "platform", "?"), e)
            return []

    results = await asyncio.gather(*[_fetch(a) for a in adapters])
    flat = [v for sub in results for v in sub]
    videos = normalize_videos(flat)
    videos = deduplicate(videos)
    if ingestion_settings.DEBUG:
        elapsed = time.monotonic() - start
        logger.info(f"fetch_from_sources [{platform}]: {len(videos)} in {elapsed:.2f}s")
    return videos
