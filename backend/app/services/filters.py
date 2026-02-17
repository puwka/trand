"""
Фильтры для отсечения «плохих» кандидатов до ранжирования.

Все жёсткие условия из спецификации (dead viral, слишком длинные,
слишком старые и т.п.) живут здесь.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .metrics import VideoStats, ComputedMetrics
from .trend_config import FILTERS


@dataclass
class FilterResult:
    passed: bool
    reason: Optional[str] = None


def _days_since(published_at: Optional[datetime]) -> float:
    if not published_at:
        return 0.0
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max((now - published_at).total_seconds() / 86400.0, 0.0)


def apply_basic_filters(stats: VideoStats, metrics: ComputedMetrics) -> FilterResult:
    """
    Реализация шага «FILTER BAD VIRAL» из спецификации.
    Возвращает, можно ли пускать ролик дальше в скоринг.
    """

    # 1) Dead viral: очень много просмотров, но почти нет вовлечения
    if (stats.views or 0) > FILTERS.big_views_threshold and metrics.engagement_rate < FILTERS.min_engagement_for_big_views:
        return FilterResult(False, "низкий engagement_rate при больших просмотрах (dead viral)")

    # 2) Комментарии отключены
    if stats.comments_disabled:
        return FilterResult(False, "комментарии отключены")

    # 3) Слишком длинный ролик
    if (stats.duration_seconds or 0) > FILTERS.max_duration_seconds:
        return FilterResult(False, f"длительность > {FILTERS.max_duration_seconds} секунд")

    # 4) Слишком старый
    if _days_since(stats.published_at) > FILTERS.max_age_days:
        return FilterResult(False, f"старше {FILTERS.max_age_days} дней")

    return FilterResult(True, None)

