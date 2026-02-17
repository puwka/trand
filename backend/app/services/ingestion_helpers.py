"""Helpers to map sources (DB) to collector_service format."""

import re
from typing import List, Tuple


def parse_source_identifier(platform: str, url: str) -> str | None:
    """Extract channel/username from source URL for collector."""
    url = (url or "").strip()
    if not url:
        return None
    platform = (platform or "").lower()
    if platform == "tiktok":
        m = re.search(r"tiktok\.com/@([^/?]+)", url, re.I)
        return m.group(1) if m else url.split("/")[-1].strip("/") or None
    if platform in ("reels", "instagram"):
        m = re.search(r"instagram\.com/([^/?]+)", url, re.I)
        return m.group(1) if m else url.split("/")[-1].strip("/") or None
    if platform == "shorts":
        m = re.search(r"youtube\.com/channel/(UC[\w-]+)", url, re.I)
        if m:
            return m.group(1)
        m = re.search(r"youtube\.com/@([^/?]+)", url, re.I)
        if m:
            return f"@{m.group(1)}"
        m = re.search(r"youtube\.com/c/([^/?]+)", url, re.I)
        if m:
            return m.group(1)
        if url.startswith("UC") and len(url) >= 24:
            return url
        return url
    return url


def platform_to_collector(platform: str) -> str:
    """Map DB platform name to collector platform key."""
    m = {"tiktok": "tiktok", "reels": "reels", "instagram": "reels", "shorts": "youtube"}
    return m.get((platform or "").lower(), platform or "")
