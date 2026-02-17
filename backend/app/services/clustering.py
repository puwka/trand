"""
Кластеризация видео по признакам «общего тренда».

Основная идея: если разные авторы делают похожий контент
одновременно (один звук, похожие хэштеги/ключевые слова),
это усиливает сигнал тренда (trend_cluster_multiplier).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple

from .metrics import VideoStats
from .trend_config import WEIGHTS


def _normalize_hashtag(tag: str) -> str:
    return tag.strip().lstrip("#").lower()


def _cluster_key(stats: VideoStats) -> Tuple[str, Tuple[str, ...]]:
    """
    Грубый ключ кластера: (sound_id, отсортированный набор хэштегов/ключевых слов).
    Чем проще ключ, тем устойчивее к шуму.
    """
    sound = stats.sound_id or ""
    tags = tuple(sorted({_normalize_hashtag(h) for h in stats.hashtags if h}))
    if not tags and stats.keywords_matched:
        tags = tuple(sorted({k.lower() for k in stats.keywords_matched}))
    return sound, tags


def _within_24h(a: datetime, b: datetime) -> bool:
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return abs((a - b).total_seconds()) <= 24 * 3600


@dataclass
class ClusterInfo:
    unique_authors: int
    multiplier: float


def compute_cluster_multipliers(videos: Iterable[VideoStats]) -> Dict[str, ClusterInfo]:
    """
    Возвращает словарь: video_id -> ClusterInfo.

    Для каждого кластера считаем количество уникальных авторов,
    появившихся в окне +-24 часа, и превращаем его в множитель:

        trend_cluster_multiplier = 1 + (unique_authors_count * 0.15)
    """
    videos_list: List[VideoStats] = [v for v in videos if v.published_at]
    if not videos_list:
        return {}

    # группируем по куче (sound_id + хэштеги/ключевые слова)
    buckets: Dict[Tuple[str, Tuple[str, ...]], List[VideoStats]] = defaultdict(list)
    for v in videos_list:
        buckets[_cluster_key(v)].append(v)

    result: Dict[str, ClusterInfo] = {}

    for bucket_videos in buckets.values():
        if len(bucket_videos) < 2:
            # одиночный ролик — кластера по сути нет
            for v in bucket_videos:
                result[v.video_id] = ClusterInfo(unique_authors=1, multiplier=1.0)
            continue

        # сортируем по времени, чтобы проще было смотреть соседей в окне 24h
        bucket_videos.sort(key=lambda v: v.published_at or timezone.utc.localize(datetime.min))

        for i, v in enumerate(bucket_videos):
            authors: set[str] = set()
            ts = v.published_at or timezone.utc.localize(datetime.min)

            # смотрим всех в том же бакете, кто в окне +-24 часа
            for other in bucket_videos:
                ots = other.published_at or timezone.utc.localize(datetime.min)
                if _within_24h(ts, ots):
                    authors.add(other.author_id)

            unique_authors = len(authors)
            multiplier = 1.0 + unique_authors * WEIGHTS.cluster_author_multiplier_step

            result[v.video_id] = ClusterInfo(
                unique_authors=unique_authors,
                multiplier=multiplier,
            )

    return result

