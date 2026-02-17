"""
Instagram Reels adapter via yt-dlp.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

import yt_dlp

from app.adapters.base_adapter import BaseAdapter
from app.config import ingestion_settings
from app.models.video_model import Video

logger = logging.getLogger(__name__)


class ReelsAdapter(BaseAdapter):
    """Instagram Reels ingestion via yt-dlp."""

    platform = "reels"

    def _get_ydl_opts(self, extract_flat: bool = True) -> dict:
        """Build yt-dlp options. Cookies required for Instagram."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": extract_flat,
            "skip_download": True,
        }
        yt_cookies = ingestion_settings.YT_COOKIES_FILE
        yt_browser = ingestion_settings.YT_COOKIES_FROM_BROWSER
        if yt_cookies:
            opts["cookiefile"] = yt_cookies
        elif yt_browser:
            opts["cookiesfrombrowser"] = (yt_browser.strip().split(",")[0].strip().lower(),)
        else:
            logger.warning(
                "[reels] No cookies. Set YT_COOKIES_FILE or YT_COOKIES_FROM_BROWSER in .env. "
                "Instagram requires login for profile/reels."
            )
        return opts

    async def fetch_trending(self) -> list[Video]:
        """Reels has no global trending; return empty or explore."""
        return []

    async def fetch_by_keywords(self, keywords: list[str]) -> list[Video]:
        """Search Instagram for reels by keyword."""
        results: list[Video] = []
        for kw in keywords[:3]:
            batch = await self._safe_fetch(self._search_impl, kw)
            results.extend(batch)
        return results[: self.max_results * 2]

    async def _search_impl(self, query: str) -> list[Video]:
        def _run():
            opts = self._get_ydl_opts(extract_flat=True)
            opts["default_search"] = "ytsearch"
            urls = [f"instagram:{query}"]
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(urls[0], download=False, process=False)
            entries = info.get("entries", []) if info else []
            return [e for e in entries if e and isinstance(e, dict)]

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as ex:
            entries = await loop.run_in_executor(ex, _run)
        return [v for v in [self._normalize_from_flat(e) for e in entries[: self.max_results]] if v]

    async def fetch_from_sources(self, channel_list: list[str]) -> list[Video]:
        """Fetch reels from Instagram user profiles."""
        results: list[Video] = []
        for username in channel_list[:10]:
            uname = username.strip().lstrip("@")
            batch = await self._safe_fetch(self._fetch_user_impl, uname)
            results.extend(batch)
        return results

    async def _fetch_user_impl(self, username: str) -> list[Video]:
        """Fetch videos from Instagram profile. Uses profile URL (not /reels/) — yt-dlp timeline."""
        def _run():
            opts = self._get_ydl_opts(extract_flat=True)
            # instagram.com/username/ matches instagram:user; /reels/ path is not supported
            url = f"https://www.instagram.com/{username}/"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False, process=True)
            except Exception as e:
                logger.warning(f"[reels] extract_info failed for {username}: {e}")
                return []
            if not info:
                return []
            entries = info.get("entries") or []
            entries = [e for e in entries if e and isinstance(e, dict)]
            if not entries and ingestion_settings.DEBUG:
                logger.info(f"[reels] No entries for {username}. Instagram may require cookies.")
            return entries[: self.max_results]

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as ex:
            entries = await loop.run_in_executor(ex, _run)
        return [v for v in [self._normalize_from_flat(e) for e in entries] if v]

    def _normalize_from_flat(self, entry: dict) -> Optional[Video]:
        """Normalize flat/extract_flat entry to Video."""
        try:
            video_id = str(entry.get("id", ""))
            if not video_id:
                return None
            url = entry.get("url", entry.get("webpage_url", f"https://www.instagram.com/reel/{video_id}/"))
            uploader = entry.get("uploader", "")
            return Video(
                platform=self.platform,
                video_id=video_id,
                url=url,
                author_id=entry.get("uploader_id", ""),
                author_name=uploader,
                author_followers=0,
                views=int(entry.get("view_count", 0) or 0),
                likes=int(entry.get("like_count", 0) or 0),
                comments=int(entry.get("comment_count", 0) or 0),
                shares=0,
                publish_time=self._parse_timestamp(entry.get("timestamp")),
                duration=int(entry.get("duration", 0) or 0),
                title=entry.get("title", "")[:500],
                description=entry.get("description", "") or "",
                hashtags=entry.get("tags", []) or [],
                sound_id="",
                thumbnail_url=entry.get("thumbnail", ""),
                raw_payload=entry,
            )
        except Exception as e:
            logger.warning(f"[reels] _normalize_from_flat failed: {e}")
            return None

    def _normalize(self, raw: any) -> Optional[Video]:
        """Convert yt-dlp extracted info to Video model."""
        return self._normalize_from_flat(raw) if isinstance(raw, dict) else None

    @staticmethod
    def _parse_timestamp(ts: Optional[float]) -> Optional[datetime]:
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError):
            return None
