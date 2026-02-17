"""
Base adapter for platform-specific video ingestion.
All adapters must inherit from this and implement the abstract methods.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.config import ingestion_settings
from app.models.video_model import Video

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Abstract base class for platform adapters."""

    platform: str = ""

    def __init__(
        self,
        max_results: Optional[int] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None,
    ) -> None:
        self.max_results = max_results or ingestion_settings.MAX_RESULTS_PER_PLATFORM
        self.timeout = timeout or ingestion_settings.REQUEST_TIMEOUT
        self.retry_count = retry_count or ingestion_settings.RETRY_COUNT

    async def _retry(self, fn, *args: Any, **kwargs: Any) -> Any:
        """Execute with retries on failure."""
        last_error: Optional[Exception] = None
        for attempt in range(self.retry_count):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    delay = ingestion_settings.RETRY_DELAY_SECONDS * (attempt + 1)
                    logger.warning(
                        f"[{self.platform}] Attempt {attempt + 1} failed: {e}. Retry in {delay}s"
                    )
                    await asyncio.sleep(delay)
        raise last_error

    async def fetch_trending(self) -> list[Video]:
        """Fetch trending videos. Override in subclass."""
        return []

    async def fetch_by_keywords(self, keywords: list[str]) -> list[Video]:
        """Fetch videos by keywords. Override in subclass."""
        return []

    async def fetch_from_sources(self, channel_list: list[str]) -> list[Video]:
        """Fetch videos from channels/sources. Override in subclass."""
        return []

    @abstractmethod
    def _normalize(self, raw: Any) -> Optional[Video]:
        """Convert platform-specific data to Video model. Must implement."""

    async def _safe_fetch(
        self, fetcher, *args: Any, **kwargs: Any
    ) -> list[Video]:
        """Execute fetcher with error resilience and optional debug logging."""
        start = time.monotonic()
        try:
            videos = await self._retry(fetcher, *args, **kwargs)
            if ingestion_settings.DEBUG:
                elapsed = time.monotonic() - start
                logger.info(
                    f"[{self.platform}] Fetched {len(videos)} videos in {elapsed:.2f}s"
                )
            return videos
        except Exception as e:
            logger.exception(f"[{self.platform}] Fetch failed: {e}")
            return []
