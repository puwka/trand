"""
Конфигурация весов и порогов для движка обнаружения трендов.

Все «магические числа» сведены сюда, чтобы логику
можно было настраивать без правки кода.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendWeights:
    # Вклады компонент в итоговый trend_score
    view_velocity: float = 0.45
    engagement_velocity: float = 0.35
    engagement_rate: float = 0.15
    freshness_bonus: float = 0.05

    # Порог, после которого считаем видео «вирусным»
    viral_threshold: float = 1.0

    # Бусты
    keyword_boost: float = 0.20   # +20% при совпадении ключевых слов
    curated_source_boost: float = 0.10  # +10% для отобранных каналов

    # Кластеризация трендов (повторяемость паттерна)
    cluster_author_multiplier_step: float = 0.15  # +15% за каждого уникального автора в кластере


@dataclass(frozen=True)
class TrendFilters:
    # Минимальный engagement_rate для больших просмотров,
    # ниже считаем «мертвым вирусом».
    min_engagement_for_big_views: float = 0.02
    big_views_threshold: int = 200_000

    # Ограничения по длительности и возрасту ролика
    max_duration_seconds: int = 120
    max_age_days: int = 5


WEIGHTS = TrendWeights()
FILTERS = TrendFilters()

