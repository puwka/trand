"""
Viral trend detector configuration.
All thresholds and weights — no magic numbers in pipeline code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgeAwareFilterConfig:
    """Age-aware dynamic minimums. Thresholds scale with video age."""

    # Reject if penalty < this
    min_penalty_to_keep: float = 0.25

    # New video protection (hours < 2): skip engagement, only require views
    early_age_hours: float = 2.0
    early_age_min_views: int = 30

    # Age buckets: (max_hours, min_views, min_likes, min_vph, min_engagement)
    # hours <= 1
    t1_hours: float = 1.0
    t1_views: int = 50
    t1_likes: int = 5
    t1_vph: float = 10.0
    t1_engagement: float = 0.01
    # hours <= 6
    t6_hours: float = 6.0
    t6_views: int = 300
    t6_likes: int = 20
    t6_vph: float = 25.0
    t6_engagement: float = 0.02
    # hours <= 24
    t24_hours: float = 24.0
    t24_views: int = 1000
    t24_likes: int = 60
    t24_vph: float = 40.0
    t24_engagement: float = 0.025
    # hours <= 72
    t72_hours: float = 72.0
    t72_views: int = 4000
    t72_likes: int = 200
    t72_vph: float = 60.0
    t72_engagement: float = 0.03
    # else (older)
    else_views: int = 10000
    else_likes: int = 400
    else_vph: float = 80.0
    else_engagement: float = 0.035

    # Penalty multipliers when below threshold
    penalty_views: float = 0.7
    penalty_likes: float = 0.7
    penalty_vph: float = 0.6
    penalty_engagement: float = 0.6

    # Optional penalties (no reject)
    max_duration_seconds: int = 120
    penalty_duration: float = 0.5
    penalty_comments_disabled: float = 0.5

    # Safety: always keep at least this many before scoring
    min_candidates: int = 40


@dataclass(frozen=True)
class ViralScoreWeights:
    """Stage 5: Component weights in final viral_score."""

    velocity: float = 0.45
    interaction: float = 0.30
    discussion: float = 0.15
    keyword_match: float = 0.10


@dataclass(frozen=True)
class CreatorMultiplierConfig:
    """Stage 3: Small creator boost thresholds (followers)."""

    boost_50k: float = 1.35
    boost_150k: float = 1.20
    boost_500k: float = 1.05
    penalty_2M: float = 0.85
    threshold_50k: int = 50_000
    threshold_150k: int = 150_000
    threshold_500k: int = 500_000
    threshold_2M: int = 2_000_000


@dataclass(frozen=True)
class FreshnessConfig:
    """Stage 4: Freshness weight by hours since publish."""

    w_2h: float = 1.6
    w_6h: float = 1.4
    w_18h: float = 1.2
    w_48h: float = 1.0
    w_older: float = 0.7
    hours_2: float = 2.0
    hours_6: float = 6.0
    hours_18: float = 18.0
    hours_48: float = 48.0


@dataclass(frozen=True)
class AIConfig:
    """Stage 6: AI quality filter."""

    top_fraction_for_llm: float = 0.30  # Call LLM only on top 30%
    min_videos_for_llm: int = 5  # At least this many to run LLM batch


@dataclass(frozen=True)
class OutputConfig:
    """Stage 7: Output mapping."""

    viral_score_threshold: float = 1.5  # is_viral when viral_score >= this
    virality_scale: float = 2.5  # Map viral_score to 1-10: min(10, max(1, viral_score * scale))


@dataclass(frozen=True)
class QualityGateConfig:
    """Stable quality gate: only strong videos enter DB."""

    quality_threshold: float = 7.0  # HIGH_QUALITY: score >= this
    borderline_threshold: float = 6.2  # BORDERLINE: borderline <= score < quality
    min_results: int = 15  # Fill from borderline if accepted < this
    top_fraction_borderline: float = 0.30  # Accept borderline if in top X% of batch
    engagement_threshold: float = 0.08  # Accept borderline if engagement_rate > this


AGE_AWARE_FILTER = AgeAwareFilterConfig()
VIRAL_WEIGHTS = ViralScoreWeights()
CREATOR_MULT = CreatorMultiplierConfig()
FRESHNESS = FreshnessConfig()
AI_CONFIG = AIConfig()
OUTPUT_CONFIG = OutputConfig()
QUALITY_GATE_CONFIG = QualityGateConfig()
