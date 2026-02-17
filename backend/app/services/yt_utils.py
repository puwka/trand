"""Общие опции для yt-dlp (cookies). Нужны только для downloader при скачивании."""

from __future__ import annotations

from typing import Any

from app.config import settings


def yt_dlp_cookie_opts() -> dict[str, Any]:
    """
    Возвращает опции авторизации для yt-dlp.
    Приоритет: cookiefile > cookiesfrombrowser.
    Парсинг идёт через EnsembleData API, cookies используются только при скачивании.
    """
    opts: dict[str, Any] = {}
    if settings.yt_cookies_file:
        opts["cookiefile"] = settings.yt_cookies_file
    elif settings.yt_cookies_from_browser:
        opts["cookiesfrombrowser"] = (settings.yt_cookies_from_browser.strip().lower(),)
    return opts
