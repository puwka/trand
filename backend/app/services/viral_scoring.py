"""
Stages 2–5: Early viral detection, creator boost, freshness, final score.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config.viral_config import (
    CREATOR_MULT,
    FRESHNESS,
    VIRAL_WEIGHTS,
)
from app.models.video_model import Video

logger = logging.getLogger(__name__)


def _hours_since(publish_time: Optional[datetime]) -> float:
    if not publish_time:
        return 48.0
    if publish_time.tzinfo is None:
        publish_time = publish_time.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max((now - publish_time).total_seconds() / 3600.0, 0.1)


def _engagement_rate(v: Video) -> float:
    views = max(v.views, 1)
    return (v.likes + v.comments * 2 + v.shares * 3) / views


def _views_per_hour(v: Video) -> float:
    return v.views / _hours_since(v.publish_time)


def _discussion_score(v: Video) -> float:
    likes = max(v.likes, 1)
    return v.comments / likes


@dataclass
class ViralScoreBreakdown:
    viral_score: float
    velocity_norm: float
    interaction_norm: float
    discussion_norm: float
    keyword_match: float
    creator_multiplier: float
    freshness: float
    explanation: str


def _keyword_match(video: Video, topic_keywords: list[str]) -> float:
    """Returns 0..1 based on keyword presence in title, description, hashtags."""
    if not topic_keywords:
        return 0.0
    text = " ".join(
        [
            (video.title or "").lower(),
            (video.description or "").lower(),
            " ".join((video.hashtags or [])).lower(),
        ]
    )
    for kw in topic_keywords:
        if kw.lower() in text:
            return 1.0
    return 0.0


def _creator_multiplier(followers: int) -> float:
    cfg = CREATOR_MULT
    if followers < cfg.threshold_50k:
        return cfg.boost_50k
    if followers < cfg.threshold_150k:
        return cfg.boost_150k
    if followers < cfg.threshold_500k:
        return cfg.boost_500k
    if followers > cfg.threshold_2M:
        return cfg.penalty_2M
    return 1.0


def _freshness_weight(hours: float) -> float:
    cfg = FRESHNESS
    if hours <= cfg.hours_2:
        return cfg.w_2h
    if hours <= cfg.hours_6:
        return cfg.w_6h
    if hours <= cfg.hours_18:
        return cfg.w_18h
    if hours <= cfg.hours_48:
        return cfg.w_48h
    return cfg.w_older


def compute_viral_score(
    video: Video,
    topic_keywords: list[str],
    debug: bool = False,
) -> ViralScoreBreakdown:
    """
    Stages 2–5: Compute viral_score.
    """
    w = VIRAL_WEIGHTS
    hours = _hours_since(video.publish_time)

    # Stage 2: Raw scores
    velocity_raw = _views_per_hour(video)
    interaction_raw = _engagement_rate(video)
    discussion_raw = _discussion_score(video)

    # Stage 2: Log normalization
    velocity_norm = math.log(velocity_raw + 1)
    interaction_norm = math.log(interaction_raw * 100 + 1)
    discussion_norm = math.log(discussion_raw * 10 + 1)

    # Stage 3: Creator multiplier
    creator_mult = _creator_multiplier(video.author_followers or 0)

    # Stage 4: Freshness
    freshness = _freshness_weight(hours)

    # Stage 5: Keyword match
    kw_match = _keyword_match(video, topic_keywords)

    # Stage 5: Final viral_score
    base = (
        velocity_norm * w.velocity
        + interaction_norm * w.interaction
        + discussion_norm * w.discussion
        + kw_match * w.keyword_match
    )
    viral_score = base * creator_mult * freshness

    # Build explanation
    parts = []
    if velocity_raw > 50:
        parts.append("high velocity")
    if interaction_raw > 0.05:
        parts.append("strong engagement")
    if freshness >= 1.2:
        parts.append("fresh")
    if (video.author_followers or 0) < 150_000:
        parts.append("small creator")
    if kw_match > 0:
        parts.append("keyword match")
    explanation = " + ".join(parts) if parts else "moderate metrics"

    if debug:
        logger.debug(
            f"[viral_score] {video.video_id}: score={viral_score:.3f} "
            f"v_norm={velocity_norm:.3f} i_norm={interaction_norm:.3f} "
            f"d_norm={discussion_norm:.3f} kw={kw_match} "
            f"creator_mult={creator_mult} freshness={freshness} => {explanation}"
        )

    return ViralScoreBreakdown(
        viral_score=viral_score,
        velocity_norm=velocity_norm,
        interaction_norm=interaction_norm,
        discussion_norm=discussion_norm,
        keyword_match=kw_match,
        creator_multiplier=creator_mult,
        freshness=freshness,
        explanation=explanation,
    )
