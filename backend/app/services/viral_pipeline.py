"""
Viral trend detector pipeline.
Age-aware soft filter -> Score -> Apply penalty -> Sort -> AI quality filter (top 30%).
Always output candidates. Never return empty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config.viral_config import AI_CONFIG, AGE_AWARE_FILTER
from app.models.video_model import Video
from app.services.viral_filters import age_aware_filter_batch
from app.services.viral_quality_filter import ai_quality_filter_batch
from app.services.viral_scoring import ViralScoreBreakdown, compute_viral_score

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    videos: list[tuple[Video, ViralScoreBreakdown]]
    total_input: int
    after_filter: int
    after_ai_filter: int
    rejected_by_filter: int


def run_viral_pipeline(
    videos: list[Video],
    topic_keywords: list[str],
    debug: bool = False,
) -> PipelineResult:
    """
    Full pipeline:
    1. Age-aware soft filter (thresholds scale with video age)
    2. Safety: keep at least top 40 candidates
    3. Score all candidates
    4. Apply penalty to viral_score
    5. Sort by penalized viral_score desc
    6. Take top 30% for LLM
    7. AI quality filter
    8. Return (video, score_breakdown) — never empty if input not empty
    """
    total = len(videos)

    if not videos:
        return PipelineResult(
            videos=[],
            total_input=0,
            after_filter=0,
            after_ai_filter=0,
            rejected_by_filter=0,
        )

    # Stage 1: Age-aware soft filter + safety (keep at least 40)
    candidates, rejected = age_aware_filter_batch(
        videos,
        min_keep=AGE_AWARE_FILTER.min_candidates,
        debug=debug,
    )
    after_filter = len(candidates)
    logger.info(f"[pipeline] Age-aware filter: {total} -> {after_filter} candidates (rejected {rejected})")

    # Stages 2-5: Score all, apply penalty
    scored: list[tuple[Video, ViralScoreBreakdown]] = []
    for video, penalty in candidates:
        breakdown = compute_viral_score(video, topic_keywords, debug=debug)
        penalized_score = breakdown.viral_score * penalty
        penalized_breakdown = ViralScoreBreakdown(
            viral_score=penalized_score,
            velocity_norm=breakdown.velocity_norm,
            interaction_norm=breakdown.interaction_norm,
            discussion_norm=breakdown.discussion_norm,
            keyword_match=breakdown.keyword_match,
            creator_multiplier=breakdown.creator_multiplier,
            freshness=breakdown.freshness,
            explanation=breakdown.explanation,
        )
        scored.append((video, penalized_breakdown))

    # Sort by penalized viral_score descending
    scored.sort(key=lambda x: x[1].viral_score, reverse=True)

    # Stage 6: AI filter only on top 30%
    cfg = AI_CONFIG
    n_for_llm = max(
        cfg.min_videos_for_llm,
        int(len(scored) * cfg.top_fraction_for_llm),
    )
    candidates_for_llm = scored[:n_for_llm]
    rest = scored[n_for_llm:]

    if candidates_for_llm:
        videos_to_check = [v for v, _ in candidates_for_llm]
        passed_ids = set(v.video_id for v in ai_quality_filter_batch(videos_to_check, debug=debug))
        passed_scored = [(v, b) for v, b in candidates_for_llm if v.video_id in passed_ids]
        failed_count = len(candidates_for_llm) - len(passed_scored)
        logger.info(f"[pipeline] AI filter (top {n_for_llm}): {len(passed_scored)} kept, {failed_count} discarded")
    else:
        passed_scored = []

    # Stage 7: Output = passed from AI + rest
    result = passed_scored + rest
    result.sort(key=lambda x: x[1].viral_score, reverse=True)

    return PipelineResult(
        videos=result,
        total_input=total,
        after_filter=after_filter,
        after_ai_filter=len(passed_scored),
        rejected_by_filter=rejected,
    )
