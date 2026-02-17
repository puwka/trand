"""
TikTok adapter via TikTokApi (unofficial GitHub library).
Requires create_sessions() before use. MS token from tiktok.com cookies recommended.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.adapters.base_adapter import BaseAdapter
from app.config import ingestion_settings
from app.models.video_model import Video

logger = logging.getLogger(__name__)


def _create_api_with_sessions():
    """Create TikTokApi and call create_sessions. Required before any fetch."""
    from TikTokApi import TikTokApi

    api = TikTokApi()
    return api


async def _ensure_sessions(api) -> None:
    """Call create_sessions if not already created."""
    if not api.sessions:
        ms_token = ingestion_settings.TIKTOK_MS_TOKEN
        if not ms_token:
            logger.warning(
                "[tiktok] TIKTOK_MS_TOKEN not set. Add ms_token from tiktok.com cookies "
                "(DevTools -> Application -> Cookies -> msToken) to .env for reliable parsing."
            )
        browser = ingestion_settings.TIKTOK_BROWSER
        ms_tokens = [ms_token] if ms_token else []
        await api.create_sessions(
            ms_tokens=ms_tokens,
            num_sessions=1,
            sleep_after=3,
            browser=browser,
            headless=True,
        )


class TikTokAdapter(BaseAdapter):
    """TikTok ingestion via TikTokApi."""

    platform = "tiktok"

    async def fetch_trending(self) -> list[Video]:
        """Fetch trending TikTok videos."""
        return await self._safe_fetch(self._fetch_trending_impl)

    async def _fetch_trending_impl(self) -> list[Video]:
        api = _create_api_with_sessions()
        async with api:
            await _ensure_sessions(api)
            videos: list[Video] = []
            async for v in api.trending.videos(count=self.max_results):
                try:
                    vid = self._normalize(v)
                    if vid:
                        videos.append(vid)
                        if len(videos) >= self.max_results:
                            break
                except Exception as e:
                    logger.warning(f"[tiktok] Normalize error: {e}")
        return videos

    async def fetch_by_keywords(self, keywords: list[str]) -> list[Video]:
        """Fetch TikTok videos by hashtag/keyword search."""
        results: list[Video] = []
        for kw in keywords[:5]:
            batch = await self._safe_fetch(self._fetch_by_keyword_impl, kw)
            results.extend(batch)
        return results[: self.max_results * 2]

    async def _fetch_by_keyword_impl(self, keyword: str) -> list[Video]:
        api = _create_api_with_sessions()
        async with api:
            await _ensure_sessions(api)
            videos: list[Video] = []
            async for v in api.search.search_type(
                keyword, "item", count=min(20, self.max_results)
            ):
                try:
                    vid = self._normalize(v)
                    if vid:
                        videos.append(vid)
                except Exception as e:
                    logger.warning(f"[tiktok] Normalize error: {e}")
        return videos

    async def fetch_from_sources(self, channel_list: list[str]) -> list[Video]:
        """Fetch videos from TikTok user profiles."""
        results: list[Video] = []
        for username in channel_list[:10]:
            batch = await self._safe_fetch(
                self._fetch_from_user_impl,
                username.strip().lstrip("@"),
            )
            results.extend(batch)
        return results

    async def _fetch_from_user_impl(self, username: str) -> list[Video]:
        api = _create_api_with_sessions()
        async with api:
            await _ensure_sessions(api)
            videos: list[Video] = []
            user = api.user(username=username)
            async for v in user.videos(count=min(20, self.max_results)):
                try:
                    vid = self._normalize(v)
                    if vid:
                        videos.append(vid)
                except Exception as e:
                    logger.warning(f"[tiktok] Normalize error: {e}")
        return videos

    def _normalize(self, raw: any) -> Optional[Video]:
        """Convert TikTokApi video object to Video model."""
        try:
            d = getattr(raw, "as_dict", raw) if not isinstance(raw, dict) else raw
            if not d or not isinstance(d, dict):
                return None

            author = d.get("author", {}) or {}
            stats = d.get("stats", d.get("statsV2", {})) or {}
            video_info = d.get("video", {}) or {}

            video_id = str(d.get("id", d.get("aweme_id", "")))
            if not video_id:
                return None

            create_time = d.get("create_time", 0)
            publish_time = (
                datetime.fromtimestamp(create_time, tz=timezone.utc)
                if create_time
                else None
            )

            duration = video_info.get("duration", 0) or 0
            if duration > 1000:
                duration = duration // 1000

            desc = d.get("desc", "") or ""
            challenges = d.get("challenges", d.get("hashtags", [])) or []
            hashtags = [
                h.get("title", h.get("name", ""))
                for h in challenges
                if isinstance(h, dict) and (h.get("title") or h.get("name"))
            ]

            music = d.get("music", d.get("sound", {})) or {}
            sound_id = str(music.get("id", music.get("id_str", "")) or "")

            author_id = str(author.get("id", author.get("uid", author.get("user_id", ""))) or "")
            author_name = str(author.get("nickname", author.get("unique_id", "")) or "")
            share_url = d.get("share_url") or f"https://www.tiktok.com/@{author.get('unique_id','')}/video/{video_id}"

            return Video(
                platform=self.platform,
                video_id=video_id,
                url=share_url,
                author_id=author_id,
                author_name=author_name,
                author_followers=int(author.get("follower_count", 0) or 0),
                views=int(stats.get("play_count", stats.get("playCount", 0)) or 0),
                likes=int(stats.get("digg_count", stats.get("diggCount", 0)) or 0),
                comments=int(stats.get("comment_count", stats.get("commentCount", 0)) or 0),
                shares=int(stats.get("share_count", stats.get("shareCount", 0)) or 0),
                publish_time=publish_time,
                duration=duration,
                title=desc[:500],
                description=desc,
                hashtags=hashtags,
                sound_id=sound_id,
                thumbnail_url=str(video_info.get("cover", video_info.get("dynamicCover", "")) or ""),
                raw_payload=d,
            )
        except Exception as e:
            logger.warning(f"[tiktok] _normalize failed: {e}")
            return None
