"""
Stable quality gate: only strong videos enter the database.
Filtering happens after scoring, before DB write.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from app.config.viral_config import OUTPUT_CONFIG, QUALITY_GATE_CONFIG
from app.models.video_model import Video
from app.services.viral_scoring import ViralScoreBreakdown

logger = logging.getLogger(__name__)

DecisionReason = Literal[
    "accepted_high_quality",
    "accepted_borderline_high_viral",
    "accepted_borderline_engagement",
    "fallback_fill",
    "rejected_low_quality",
]


@dataclass
class GateResult:
    """Single video with quality gate decision."""

    video: Video
    breakdown: ViralScoreBreakdown
    quality_decision_reason: DecisionReason


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _engagement_rate(video: Video) -> float:
    views = max(video.views, 1)
    return (video.likes + video.comments + video.shares) / views


def apply_quality_gate(
    items: list[tuple[Video, ViralScoreBreakdown]],
) -> list[GateResult]:
    """
    Apply stable quality gate. Returns only accepted videos with reason.
    Never returns empty if batch has any borderline+ videos.
    """
    cfg = QUALITY_GATE_CONFIG
    scale = OUTPUT_CONFIG.virality_scale

    # Step 1: Normalize scores and classify
    classified: list[tuple[Video, ViralScoreBreakdown, float, str]] = []
    for video, breakdown in items:
        quality_score = _clamp(breakdown.viral_score * scale, 0.0, 10.0)
        if quality_score >= cfg.quality_threshold:
            zone = "HIGH_QUALITY"
        elif quality_score >= cfg.borderline_threshold:
            zone = "BORDERLINE"
        else:
            zone = "LOW"
        classified.append((video, breakdown, quality_score, zone))

    # Top 30% of batch by viral_score (for borderline acceptance)
    all_viral = [(classified[i][1].viral_score, i) for i in range(len(classified))]
    all_viral.sort(reverse=True, key=lambda x: x[0])
    n_total = len(all_viral)
    top_count = max(1, int(n_total * cfg.top_fraction_borderline))
    top_30_indices = {all_viral[i][1] for i in range(top_count)}

    accepted: list[GateResult] = []
    borderline_pool: list[tuple[Video, ViralScoreBreakdown]] = []

    for i, (video, breakdown, quality_score, zone) in enumerate(classified):
        if zone == "HIGH_QUALITY":
            accepted.append(GateResult(video, breakdown, "accepted_high_quality"))
        elif zone == "BORDERLINE":
            eng = _engagement_rate(video)
            if i in top_30_indices:
                accepted.append(GateResult(video, breakdown, "accepted_borderline_high_viral"))
            elif eng > cfg.engagement_threshold:
                accepted.append(GateResult(video, breakdown, "accepted_borderline_engagement"))
            else:
                borderline_pool.append((video, breakdown))
        else:
            pass  # rejected_low_quality

    # Sort borderline pool by viral_score desc for fallback
    borderline_pool.sort(key=lambda x: x[1].viral_score, reverse=True)

    # Step 4: Never empty result
    if len(accepted) < cfg.min_results and borderline_pool:
        needed = cfg.min_results - len(accepted)
        for video, breakdown in borderline_pool[:needed]:
            accepted.append(GateResult(video, breakdown, "fallback_fill"))

    logger.info(
        "[quality_gate] accepted=%d high=%d borderline=%d fallback=%d borderline_pool=%d",
        len(accepted),
        sum(1 for r in accepted if r.quality_decision_reason == "accepted_high_quality"),
        sum(1 for r in accepted if r.quality_decision_reason.startswith("accepted_borderline")),
        sum(1 for r in accepted if r.quality_decision_reason == "fallback_fill"),
        len(borderline_pool),
    )
    return accepted
