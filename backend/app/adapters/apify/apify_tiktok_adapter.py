"""
Apify TikTok adapter.
Uses Apify TikTok scraper actor. Same interface as TikTokAdapter.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.adapters.apify.apify_client import run_actor
from app.adapters.base_adapter import BaseAdapter
from app.config import ingestion_settings
from app.models.video_model import Video

logger = logging.getLogger(__name__)


class ApifyTikTokAdapter(BaseAdapter):
    """TikTok ingestion via Apify actor."""

    platform = "tiktok"

    def _normalize(self, raw: Any) -> Optional[Video]:
        """Convert Apify TikTok item to Video model. Supports clockworks/tiktok-scraper output."""
        try:
            d = raw if isinstance(raw, dict) else {}
            if not d:
                return None
            # clockworks: id, authorMeta, webVideoUrl, diggCount, playCount, commentCount, text
            # apidojo: id, channel, video, postPage, views, likes
            video_id = str(d.get("id") or d.get("videoId") or "")
            if not video_id:
                return None
            author_meta = d.get("authorMeta") or {}
            channel = d.get("channel") or author_meta
            video_info = d.get("videoMeta") or d.get("video") or {}
            uploaded = d.get("createTime") or d.get("uploadedAt") or 0
            create_iso = d.get("createTimeISO", "")
            publish_time = None
            if create_iso:
                try:
                    publish_time = datetime.fromisoformat(str(create_iso).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            if not publish_time and uploaded:
                try:
                    ts = int(uploaded) if isinstance(uploaded, (int, float)) else 0
                    if ts:
                        publish_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                except (ValueError, OSError):
                    pass
            duration = int(video_info.get("duration", 0) or 0)
            if duration > 1000:
                duration = duration // 1000
            text_val = d.get("text") or d.get("title") or d.get("desc") or ""
            title = str(text_val)[:500]
            desc = str(text_val)
            hashtags = list(d.get("hashtags", []) or [])
            if hashtags and isinstance(hashtags[0], dict):
                hashtags = [h.get("name", h.get("title", "")) for h in hashtags if isinstance(h, dict)]
            hashtags = [str(h) for h in hashtags if h]
            author_id = str(channel.get("id") or author_meta.get("id") or "")
            author_name = str(channel.get("nickName") or channel.get("name") or author_meta.get("nickName") or "")
            author_user = str(channel.get("name") or author_meta.get("name") or channel.get("username") or "")
            if not author_name:
                author_name = author_user
            url = d.get("webVideoUrl") or d.get("postPage") or d.get("url") or ""
            if not url and author_user:
                url = f"https://www.tiktok.com/@{author_user}/video/{video_id}"
            views = int(d.get("playCount") or d.get("views") or 0)
            likes = int(d.get("diggCount") or d.get("likes") or 0)
            comments = int(d.get("commentCount") or d.get("comments") or 0)
            shares = int(d.get("shareCount") or d.get("shares") or 0)
            cover = (video_info.get("coverUrl") or video_info.get("originalCoverUrl") or
                     video_info.get("cover") or video_info.get("thumbnail") or "")
            return Video(
                platform=self.platform,
                video_id=video_id,
                url=url or f"https://www.tiktok.com/video/{video_id}",
                author_id=author_id,
                author_name=author_name or author_user,
                author_followers=int(channel.get("fans") or channel.get("followers") or 0),
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                publish_time=publish_time,
                duration=duration,
                title=title,
                description=desc,
                hashtags=hashtags,
                sound_id="",
                thumbnail_url=str(cover),
                raw_payload=d,
            )
        except Exception as e:
            logger.warning("[apify_tiktok] _normalize failed: %s", e)
            return None

    async def fetch_trending(self) -> list[Video]:
        """Fetch trending via Apify (hashtag search as fallback)."""
        token = ingestion_settings.APIFY_TOKEN
        if not token:
            return []
        # clockworks/tiktok-scraper: hashtags or search
        run_input = {
            "hashtags": ["viral", "fyp"],
            "resultsPerPage": min(15, self.max_results),
        }
        items = await run_actor(
            ingestion_settings.APIFY_TIKTOK_ACTOR,
            run_input,
            token,
            timeout_secs=ingestion_settings.APIFY_TIMEOUT_SECS,
        )
        videos = []
        for item in items:
            v = self._normalize(item)
            if v:
                videos.append(v)
        return videos[: self.max_results]

    async def fetch_by_keywords(self, keywords: list[str]) -> list[Video]:
        """Fetch by keywords via Apify."""
        token = ingestion_settings.APIFY_TOKEN
        if not token or not keywords:
            return []
        # clockworks: search (string) or hashtags (array)
        run_input = {
            "search": keywords[0].strip() if keywords else "viral",
            "resultsPerPage": min(30, self.max_results * 2),
        }
        items = await run_actor(
            ingestion_settings.APIFY_TIKTOK_ACTOR,
            run_input,
            token,
            timeout_secs=ingestion_settings.APIFY_TIMEOUT_SECS,
        )
        videos = []
        for item in items:
            v = self._normalize(item)
            if v:
                videos.append(v)
        return videos[: self.max_results * 2]

    async def fetch_from_sources(self, channel_list: list[str]) -> list[Video]:
        """Fetch from TikTok profiles via Apify."""
        token = ingestion_settings.APIFY_TOKEN
        if not token or not channel_list:
            return []
        # clockworks/tiktok-scraper uses profiles (usernames), not startUrls
        profiles = []
        for u in channel_list[:10]:
            uname = str(u or "").strip().lstrip("@")
            if uname:
                profiles.append(uname)
        if not profiles:
            return []
        run_input = {
            "profiles": profiles,
            "resultsPerPage": min(20, self.max_results * 2),
            "profileScrapeSections": ["videos"],
        }
        items = await run_actor(
            ingestion_settings.APIFY_TIKTOK_ACTOR,
            run_input,
            token,
            timeout_secs=ingestion_settings.APIFY_TIMEOUT_SECS,
        )
        videos = []
        for item in items:
            v = self._normalize(item)
            if v:
                videos.append(v)
        return videos[: self.max_results * 5]
