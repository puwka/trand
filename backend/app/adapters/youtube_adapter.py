"""
YouTube Shorts adapter via YouTube Data API v3.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.adapters.base_adapter import BaseAdapter
from app.config import ingestion_settings
from app.models.video_model import Video

logger = logging.getLogger(__name__)


class YouTubeAdapter(BaseAdapter):
    """YouTube Shorts ingestion via YouTube Data API v3."""

    platform = "youtube"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._api_key = ingestion_settings.YOUTUBE_API_KEY
        self._youtube = None

    def _get_client(self):
        """Lazy init Google API client."""
        if self._youtube is None and self._api_key:
            from googleapiclient.discovery import build

            self._youtube = build(
                "youtube", "v3", developerKey=self._api_key, cache_discovery=False
            )
        return self._youtube

    async def fetch_trending(self) -> list[Video]:
        """Fetch trending YouTube Shorts (via search)."""
        return await self._safe_fetch(self._fetch_trending_impl)

    async def _fetch_trending_impl(self) -> list[Video]:
        return await self._search_shorts_impl("shorts")

    async def fetch_by_keywords(self, keywords: list[str]) -> list[Video]:
        """Fetch YouTube Shorts by keywords."""
        results: list[Video] = []
        for kw in keywords[:5]:
            batch = await self._safe_fetch(self._search_shorts_impl, kw)
            results.extend(batch)
        return results[: self.max_results * 2]

    async def _search_shorts_impl(self, query: str) -> list[Video]:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def _search():
            yt = self._get_client()
            if not yt:
                return []
            resp = (
                yt.search()
                .list(
                    part="snippet",
                    q=f"{query} shorts",
                    type="video",
                    videoDuration="short",
                    maxResults=min(25, self.max_results),
                )
                .execute()
            )
            ids = [i["id"]["videoId"] for i in resp.get("items", []) if "videoId" in i.get("id", {})]
            if not ids:
                return []
            videos_resp = (
                yt.videos()
                .list(part="snippet,statistics,contentDetails", id=",".join(ids))
                .execute()
            )
            return list(videos_resp.get("items", []))

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as ex:
            items = await loop.run_in_executor(ex, _search)
        return [v for v in [self._normalize(item) for item in items] if v]

    async def fetch_from_sources(self, channel_list: list[str]) -> list[Video]:
        """Fetch Shorts from YouTube channels (by channel ID or @handle)."""
        results: list[Video] = []
        for channel_id in channel_list[:10]:
            batch = await self._safe_fetch(self._fetch_from_channel_impl, channel_id.strip())
            results.extend(batch)
        return results

    async def _fetch_from_channel_impl(self, channel_id: str) -> list[Video]:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def _fetch():
            yt = self._get_client()
            if not yt:
                return []
            if channel_id.startswith("UC") and len(channel_id) >= 24:
                cid = channel_id
            else:
                search = (
                    yt.search()
                    .list(part="snippet", q=channel_id.lstrip("@"), type="channel")
                    .execute()
                )
                chs = search.get("items", [])
                if not chs:
                    return []
                cid = chs[0]["snippet"]["channelId"]
            search = (
                yt.search()
                .list(
                    part="snippet",
                    channelId=cid,
                    type="video",
                    videoDuration="short",
                    maxResults=min(25, self.max_results),
                    order="date",
                )
                .execute()
            )
            ids = [i["id"]["videoId"] for i in search.get("items", []) if "videoId" in i.get("id", {})]
            if not ids:
                return []
            videos_resp = (
                yt.videos()
                .list(part="snippet,statistics,contentDetails", id=",".join(ids))
                .execute()
            )
            by_id = {v["id"]: v for v in videos_resp.get("items", [])}
            out = [by_id[vid] for s in search.get("items", []) for vid in [s.get("id", {}).get("videoId")] if vid and vid in by_id]
            return out

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as ex:
            items = await loop.run_in_executor(ex, _fetch)
        return [v for v in [self._normalize(item) for item in items] if v]

    def _normalize(self, raw: any) -> Optional[Video]:
        """Convert YouTube API item to Video model."""
        try:
            if isinstance(raw, dict):
                d = raw
            else:
                return None
            vid = d.get("id") if isinstance(d.get("id"), str) else (d.get("id", {}).get("videoId") if isinstance(d.get("id"), dict) else None)
            if not vid:
                return None
            video_id = vid if isinstance(vid, str) else str(vid)
            snippet = d.get("snippet", {}) or {}
            stats = d.get("statistics", {}) or {}
            content = d.get("contentDetails", {}) or {}

            pub = snippet.get("publishedAt", "")
            publish_time = None
            if pub:
                try:
                    publish_time = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                except ValueError:
                    pass

            duration_str = content.get("duration", "PT0S")
            duration = self._parse_iso8601(duration_str)

            # Comments disabled: API omits commentCount when disabled
            comments_disabled = "commentCount" not in stats

            return Video(
                platform=self.platform,
                video_id=video_id,
                url=f"https://www.youtube.com/shorts/{video_id}",
                author_id=snippet.get("channelId", ""),
                author_name=snippet.get("channelTitle", ""),
                author_followers=0,
                views=int(stats.get("viewCount", 0) or 0),
                likes=int(stats.get("likeCount", 0) or 0),
                comments=int(stats.get("commentCount", 0) or 0),
                shares=0,
                publish_time=publish_time,
                duration=duration,
                title=snippet.get("title", "")[:500],
                description=snippet.get("description", "") or "",
                hashtags=[],
                sound_id="",
                thumbnail_url=((snippet.get("thumbnails") or {}).get("high") or {}).get("url", ""),
                comments_disabled=comments_disabled,
                raw_payload=d,
            )
        except Exception as e:
            logger.warning(f"[youtube] _normalize failed: {e}")
            return None

    @staticmethod
    def _parse_iso8601(s: str) -> int:
        import re
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "PT0S")
        if not m:
            return 0
        h, m_, sec = (int(g or 0) for g in m.groups())
        return h * 3600 + m_ * 60 + sec
