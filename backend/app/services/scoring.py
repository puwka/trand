"""
Подсчёт итогового trend_score на основе метрик, кластеризации и фильтров.

Главный принцип: ищем РАННИЕ сигналы роста (ускорение),
а не просто популярные ролики с огромными цифрами.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .metrics import VideoStats, ComputedMetrics
from .trend_config import WEIGHTS


@dataclass
class ScoreBreakdown:
    trend_score: float
    base_score: float
    creator_penalty: float
    cluster_multiplier: float
    keyword_boost_applied: bool
    curated_source_boost_applied: bool
    explanation: str


def _creator_penalty(author_followers: Optional[int]) -> float:
    f = author_followers or 0
    if f > 5_000_000:
        return 0.6
    if f > 1_000_000:
        return 0.75
    if f > 300_000:
        return 0.9
    return 1.0


def _build_explanation(
    metrics: ComputedMetrics,
    final_score: float,
    penalty: float,
    cluster_mult: float,
    keyword_boost: bool,
    curated_boost: bool,
) -> str:
    reasons = []
    if metrics.view_velocity > 0:
        reasons.append("быстрый набор просмотров")
    if metrics.engagement_velocity > 0:
        reasons.append("растущая вовлечённость")
    if metrics.engagement_rate > 0.05:
        reasons.append("высокий engagement_rate")
    if metrics.freshness_bonus >= 1.0:
        reasons.append("очень свежий ролик")
    if penalty < 1.0:
        reasons.append("снижен вес больших авторов")
    if cluster_mult > 1.0:
        reasons.append("обнаружен повторяющийся паттерн (кластер)")
    if keyword_boost:
        reasons.append("совпали ключевые слова пользователя")
    if curated_boost:
        reasons.append("из отобранного источника")

    base = " ; ".join(reasons) if reasons else "умеренные метрики роста"
    return f"{base}. Итоговый trend_score={final_score:.3f}"


def compute_trend_score(
    stats: VideoStats,
    metrics: ComputedMetrics,
    *,
    cluster_multiplier: float = 1.0,
    keyword_matched: bool = False,
    curated_source: Optional[bool] = None,
    debug: bool = False,
) -> ScoreBreakdown:
    """
    Основная формула:

        trend_score =
            view_velocity       * 0.45 +
            engagement_velocity * 0.35 +
            engagement_rate     * 0.15 +
            freshness_bonus     * 0.05

        затем:
            * creator_penalty
            * trend_cluster_multiplier
            * keyword / source boost
    """
    w = WEIGHTS

    base_score = (
        metrics.view_velocity * w.view_velocity
        + metrics.engagement_velocity * w.engagement_velocity
        + metrics.engagement_rate * w.engagement_rate
        + metrics.freshness_bonus * w.freshness_bonus
    )

    penalty = _creator_penalty(stats.author_followers)
    score = base_score * penalty * cluster_multiplier

    keyword_boost_applied = False
    curated_boost_applied = False

    if keyword_matched:
        score *= 1.0 + w.keyword_boost
        keyword_boost_applied = True

    if curated_source or stats.curated_source:
        score *= 1.0 + w.curated_source_boost
        curated_boost_applied = True

    explanation = _build_explanation(
        metrics,
        score,
        penalty,
        cluster_multiplier,
        keyword_boost_applied,
        curated_boost_applied,
    )

    return ScoreBreakdown(
        trend_score=score,
        base_score=base_score,
        creator_penalty=penalty,
        cluster_multiplier=cluster_multiplier,
        keyword_boost_applied=keyword_boost_applied,
        curated_source_boost_applied=curated_boost_applied,
        explanation=explanation,
    )


def rank_videos(
    videos: Dict[str, VideoStats],
    metrics_map: Dict[str, ComputedMetrics],
    cluster_multipliers: Dict[str, float],
    keyword_matches: Dict[str, bool],
    *,
    debug: bool = False,
) -> Dict[str, ScoreBreakdown]:
    """
    Удобный хелпер: получаем на вход уже посчитанные метрики/кластера/совпадения
    и возвращаем подробный скор по каждому видео.
    """
    result: Dict[str, ScoreBreakdown] = {}
    for vid, stats in videos.items():
        metrics = metrics_map[vid]
        cluster_mult = cluster_multipliers.get(vid, 1.0)
        kw = keyword_matches.get(vid, False)
        sb = compute_trend_score(
            stats,
            metrics,
            cluster_multiplier=cluster_mult,
            keyword_matched=kw,
            debug=debug,
        )
        result[vid] = sb
    return result

