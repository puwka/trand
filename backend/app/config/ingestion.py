"""Ingestion layer configuration."""

from __future__ import annotations

import os
# Load .env for local dev (Railway sets env via dashboard)
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv("backend/.env")
except ImportError:
    pass
from functools import lru_cache
from typing import Optional


class IngestionSettings:
    """Settings for the multi-platform ingestion engine."""

    def __init__(self) -> None:
        self.YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
        self.TIKTOK_ENABLED = os.environ.get("TIKTOK_ENABLED", "true").lower() in ("true", "1", "yes")
        self.TIKTOK_MS_TOKEN = os.environ.get("TIKTOK_MS_TOKEN") or None
        self.TIKTOK_BROWSER = os.environ.get("TIKTOK_BROWSER", "chromium")
        self.YT_COOKIES_FILE = os.environ.get("YT_COOKIES_FILE") or None
        self.YT_COOKIES_FROM_BROWSER = os.environ.get("YT_COOKIES_FROM_BROWSER") or None
        self.MAX_RESULTS_PER_PLATFORM = int(os.environ.get("MAX_RESULTS_PER_PLATFORM", "20"))
        self.REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))
        self.RETRY_COUNT = int(os.environ.get("RETRY_COUNT", "3"))
        self.RETRY_DELAY_SECONDS = float(os.environ.get("RETRY_DELAY_SECONDS", "2.0"))
        self.DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

        self.USE_APIFY = os.environ.get("USE_APIFY", "false").lower() in ("true", "1", "yes")
        self.APIFY_TOKEN = os.environ.get("APIFY_TOKEN") or None
        self.APIFY_TIMEOUT_SECS = int(os.environ.get("APIFY_TIMEOUT_SECS", "60"))
        self.APIFY_TIKTOK_ACTOR = os.environ.get("APIFY_TIKTOK_ACTOR", "apidojo/tiktok-scraper-api")
        self.APIFY_REELS_ACTOR = os.environ.get("APIFY_REELS_ACTOR", "apify/instagram-reel-scraper")
        self.DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("true", "1", "yes")


@lru_cache
def get_ingestion_settings() -> IngestionSettings:
    return IngestionSettings()


ingestion_settings = get_ingestion_settings()
