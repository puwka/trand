"""
Apify Instagram Reels adapter.
Uses Apify Instagram Reel Scraper actor. Same interface as ReelsAdapter.
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


def _parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse timestamp from Apify (ISO string or unix)."""
    if ts is None:
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        s = str(ts)
        if s.isdigit():
            return datetime.fromtimestamp(int(s), tz=timezone.utc)
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, OSError, TypeError):
        return None


class ApifyReelsAdapter(BaseAdapter):
    """Instagram Reels ingestion via Apify actor."""

    platform = "reels"

    def _normalize(self, raw: Any) -> Optional[Video]:
        """Convert Apify Instagram post/reel to Video. Supports apify/instagram-scraper and instagram-reel-scraper."""
        try:
            d = raw if isinstance(raw, dict) else {}
            if not d:
                return None
            # apify/instagram-scraper returns Image and Video; we only want Video for reels
            item_type = (d.get("type") or "").strip()
            if item_type and item_type.lower() not in ("video", "reel", "clips"):
                return None
            short_code = str(d.get("shortCode", "") or "")
            video_id = short_code or str(d.get("id", "") or "")
            if not video_id:
                return None
            caption = str(d.get("caption", "") or "")
            hashtags = list(d.get("hashtags", []) or [])
            hashtags = [str(h) for h in hashtags if h]
            url = str(d.get("url", "") or "")
            if not url and short_code:
                url = f"https://www.instagram.com/reel/{short_code}/" if short_code else ""
            owner_user = str(d.get("ownerUsername", "") or "")
            owner_name = str(d.get("ownerFullName", "") or owner_user)
            owner_id = str(d.get("ownerId", "") or "")
            views = 0
            for k in ("videoViewCount", "playCount", "viewCount", "video_view_count"):
                if k in d and d[k] is not None:
                    try:
                        views = int(d[k])
                        break
                    except (ValueError, TypeError):
                        pass
            likes = int(d.get("likesCount", d.get("likeCount", 0)) or 0)
            comments = int(d.get("commentsCount", d.get("commentCount", 0)) or 0)
            shares = int(d.get("sharesCount", d.get("shareCount", 0)) or 0)
            duration = int(float(d.get("videoDuration", d.get("duration", 0)) or 0))
            publish_time = _parse_timestamp(d.get("timestamp", d.get("takenAt")))
            video_url = str(d.get("videoUrl", d.get("url", "")) or url)
            thumb = ""
            imgs = d.get("images") or []
            if imgs:
                thumb = str(imgs[0]) if isinstance(imgs[0], str) else ""
            if not thumb:
                thumb = str(d.get("displayUrl", "") or "")
            return Video(
                platform=self.platform,
                video_id=video_id,
                url=url or video_url or f"https://www.instagram.com/reel/{short_code}/",
                author_id=owner_id,
                author_name=owner_name or owner_user,
                author_followers=0,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                publish_time=publish_time,
                duration=duration,
                title=caption[:500],
                description=caption,
                hashtags=hashtags,
                sound_id="",
                thumbnail_url=thumb,
                comments_disabled=bool(d.get("commentsDisabled", False)),
                raw_payload=d,
            )
        except Exception as e:
            logger.warning("[apify_reels] _normalize failed: %s", e)
            return None

    async def fetch_trending(self) -> list[Video]:
        """Reels has no global trending via Apify."""
        return []

    async def fetch_by_keywords(self, keywords: list[str]) -> list[Video]:
        """Fetch by hashtag via apify/instagram-scraper (search + searchType=hashtag)."""
        token = ingestion_settings.APIFY_TOKEN
        if not token or not keywords:
            return []
        tag = (keywords[0] or "").strip().lstrip("#") or "viral"
        run_input = {
            "search": tag,
            "searchType": "hashtag",
            "searchLimit": 3,
            "resultsType": "posts",
            "resultsLimit": min(50, self.max_results * 2),
        }
        items = await run_actor(
            ingestion_settings.APIFY_REELS_ACTOR,
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
        """Fetch from Instagram usernames via Apify."""
        token = ingestion_settings.APIFY_TOKEN
        if not token or not channel_list:
            return []
        urls = []
        for u in channel_list[:10]:
            uname = str(u or "").strip().lstrip("@")
            if uname:
                urls.append(f"https://www.instagram.com/{uname}/")
        if not urls:
            return []
        # apify/instagram-scraper: directUrls, resultsType, resultsLimit
        run_input = {
            "directUrls": urls,
            "resultsType": "posts",
            "resultsLimit": min(100, self.max_results * 5),
        }
        items = await run_actor(
            ingestion_settings.APIFY_REELS_ACTOR,
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
