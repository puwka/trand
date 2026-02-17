"""
Ingestion layer configuration.
All API keys and limits — no hardcoded secrets.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class IngestionSettings:
    """Settings for the multi-platform ingestion engine."""

    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    TIKTOK_ENABLED: bool = os.getenv("TIKTOK_ENABLED", "true").lower() in ("true", "1", "yes")
    TIKTOK_MS_TOKEN: Optional[str] = os.getenv("TIKTOK_MS_TOKEN") or None
    TIKTOK_BROWSER: str = os.getenv("TIKTOK_BROWSER", "chromium")
    YT_COOKIES_FILE: Optional[str] = os.getenv("YT_COOKIES_FILE") or None
    YT_COOKIES_FROM_BROWSER: Optional[str] = os.getenv("YT_COOKIES_FROM_BROWSER") or None
    MAX_RESULTS_PER_PLATFORM: int = int(os.getenv("MAX_RESULTS_PER_PLATFORM", "20"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    RETRY_COUNT: int = int(os.getenv("RETRY_COUNT", "3"))
    RETRY_DELAY_SECONDS: float = float(os.getenv("RETRY_DELAY_SECONDS", "2.0"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Apify (optional data source)
    USE_APIFY: bool = os.getenv("USE_APIFY", "false").lower() in ("true", "1", "yes")
    APIFY_TOKEN: Optional[str] = os.getenv("APIFY_TOKEN") or None
    APIFY_TIMEOUT_SECS: int = int(os.getenv("APIFY_TIMEOUT_SECS", "60"))
    APIFY_TIKTOK_ACTOR: str = os.getenv("APIFY_TIKTOK_ACTOR", "apidojo/tiktok-scraper-api")
    APIFY_REELS_ACTOR: str = os.getenv("APIFY_REELS_ACTOR", "apify/instagram-reel-scraper")
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")


ingestion_settings = IngestionSettings()
