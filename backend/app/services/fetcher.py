"""
Fetcher for video URLs на основе yt-dlp.

Для каждого источника (канала/профиля) пытается найти самый
перспективный ролик за последнюю неделю и вернуть его URL.

Важно: yt-dlp должен уметь обрабатывать переданный URL (YouTube,
TikTok, и т.п.). Для локальной разработки проще всего использовать
YouTube‑каналы или плейлисты.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import yt_dlp

from app.config import settings
from app.services.yt_utils import yt_dlp_cookie_opts


def _sorted_recent_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Возвращает список кандидатов (лучшие сначала):
    - приоритет: за последнюю неделю;
    - если нет — за последние 30 дней;
    - если и там нет — из всех доступных.
    Критерий «лучший» — максимальное количество просмотров.
    """
    if not entries:
        return []

    now = datetime.now(timezone.utc).date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    recent_7: list[dict[str, Any]] = []
    recent_30: list[dict[str, Any]] = []
    for e in entries:
        upload_date = e.get("upload_date")  # YYYYMMDD
        if not upload_date:
            continue
        try:
            dt = datetime.strptime(upload_date, "%Y%m%d").date()
        except Exception:
            continue
        if dt >= week_ago:
            recent_7.append(e)
        elif dt >= month_ago:
            recent_30.append(e)

    # Сначала пытаемся за неделю, потом за 30 дней, потом вообще из всех.
    if recent_7:
        candidates: list[dict[str, Any]] = recent_7
    elif recent_30:
        candidates = recent_30
    else:
        candidates = entries

    # шортсы обычно короткие — даём лёгкий приоритет коротким роликам
    def sort_key(e: dict[str, Any]) -> tuple[int, int]:
        vc = e.get("view_count") or 0
        duration = e.get("duration") or 0
        short_bonus = 1 if duration and duration <= 90 else 0  # Shorts приоритетнее
        return (short_bonus, vc)

    candidates.sort(key=sort_key, reverse=True)
    return candidates


def _entry_to_url(entry: dict[str, Any]) -> Optional[str]:
    """Аккуратно достаём URL ролика из записи yt-dlp."""
    url = (
        entry.get("webpage_url")
        or entry.get("original_url")
        or entry.get("url")
    )
    if not url:
        return None
    return str(url)


def _is_video_playable(video_url: str) -> bool:
    """
    Пытаемся ещё раз дернуть yt-dlp по конкретному видео.
    Если ролик удалён, требует логин / cookies или недоступен — будет исключение.
    Такие варианты считаем «непроигрываемыми» и пропускаем.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }
    ydl_opts.update(yt_dlp_cookie_opts())
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=False)
        return True
    except Exception:
        return False


def fetch_latest_video_url(channel_url: str) -> str | None:
    """
    Возвращает URL самого перспективного ролика за неделю для данного источника.

    Логика:
    - дергаем yt-dlp по URL источника (канал, плейлист, страница пользователя);
    - берём список роликов (entries);
    - фильтруем по дате (последние 7 дней);
    - выбираем ролик с максимальным количеством просмотров;
    - возвращаем его URL.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,  # не скачиваем, только список
        "skip_download": True,
    }
    ydl_opts.update(yt_dlp_cookie_opts())

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
    except Exception:
        # Если источник не поддерживается yt-dlp или что‑то пошло не так – пропускаем.
        return None

    entries = info.get("entries") or []
    # Некоторые типы ответов (одиночный ролик) не имеют entries.
    if not entries and info.get("url"):
        entries = [info]

    candidates = _sorted_recent_candidates(entries)
    for entry in candidates:
        video_url = _entry_to_url(entry)
        if not video_url:
            continue
        # Берём первое реально доступное видео (yt-dlp не падает на нём)
        if _is_video_playable(video_url):
            return video_url

    # Ничего живого не нашли
    return None

