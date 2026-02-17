"""
Базовые метрики для оценки динамики роликов.

Задача этого модуля — аккуратно посчитать то, что можно посчитать
по «сырым» числам с платформ (просмотры, лайки, время публикации и т.п.),
и НИЧЕГО не решать про пороги / ранжирование.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import log10
from typing import Optional


@dataclass
class VideoStats:
    """Минимальный набор сырых статистик по ролику."""

    platform: str
    video_id: str
    author_id: str
    author_followers: Optional[int]

    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    shares: Optional[int]

    duration_seconds: Optional[float]
    published_at: Optional[datetime]

    title: str = ""
    description: str = ""
    hashtags: tuple[str, ...] = ()
    sound_id: Optional[str] = None
    keywords_matched: tuple[str, ...] = ()

    # опциональные флаги
    comments_disabled: bool = False
    curated_source: bool = False


@dataclass
class ComputedMetrics:
    """Промежуточные численные метрики поверх VideoStats."""

    hours_since_publish: float
    engagement_rate: float
    author_power: float
    view_velocity: float
    engagement_velocity: float
    freshness_bonus: float


def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def compute_hours_since_publish(published_at: Optional[datetime]) -> float:
    if not published_at:
        return 24.0  # если не знаем — считаем средневозрастным
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - published_at
    hours = delta.total_seconds() / 3600.0
    # защищаемся от странных дат в будущем
    return max(hours, 0.1)


def compute_engagement_rate(stats: VideoStats) -> float:
    views = float(stats.views or 0)
    likes = float(stats.likes or 0)
    comments = float(stats.comments or 0)
    shares = float(stats.shares or 0)
    # Комментарии и шаринги обычно ценнее простого лайка
    weighted_engagement = likes + comments * 2.0 + shares * 3.0
    return _safe_div(weighted_engagement, views)


def compute_author_power(stats: VideoStats) -> float:
    followers = float(stats.author_followers or 0)
    # логарифмическая шкала: разница между 1k и 10k важнее, чем между 1M и 2M
    return log10(followers + 1.0)


def compute_view_velocity(stats: VideoStats, hours_since_publish: float) -> float:
    views = float(stats.views or 0)
    return _safe_div(views, hours_since_publish)


def compute_engagement_velocity(engagement_rate: float, hours_since_publish: float) -> float:
    return _safe_div(engagement_rate, hours_since_publish)


def compute_freshness_bonus(hours_since_publish: float) -> float:
    if hours_since_publish < 3:
        return 1.5
    if hours_since_publish < 12:
        return 1.2
    if hours_since_publish < 24:
        return 1.0
    if hours_since_publish < 72:
        return 0.7
    return 0.3


def compute_all_metrics(stats: VideoStats) -> ComputedMetrics:
    hours = compute_hours_since_publish(stats.published_at)
    eng_rate = compute_engagement_rate(stats)
    author_pow = compute_author_power(stats)
    v_vel = compute_view_velocity(stats, hours)
    e_vel = compute_engagement_velocity(eng_rate, hours)
    fresh = compute_freshness_bonus(hours)

    return ComputedMetrics(
        hours_since_publish=hours,
        engagement_rate=eng_rate,
        author_power=author_pow,
        view_velocity=v_vel,
        engagement_velocity=e_vel,
        freshness_bonus=fresh,
    )

