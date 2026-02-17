"""
Age-aware soft filter: thresholds scale with video age.
Ranking, not elimination. Bad videos sink, never return empty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config.viral_config import AGE_AWARE_FILTER
from app.models.video_model import Video

logger = logging.getLogger(__name__)


@dataclass
class AgeAwareFilterResult:
    passed: bool
    penalty: float
    reason: str


def _hours_since(publish_time: Optional[datetime]) -> float:
    if not publish_time:
        return 24.0
    if publish_time.tzinfo is None:
        publish_time = publish_time.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max((now - publish_time).total_seconds() / 3600.0, 0.1)


def _engagement_rate(v: Video) -> float:
    views = max(v.views, 1)
    weighted = v.likes + v.comments * 2 + v.shares * 3
    return weighted / views


def _get_dynamic_thresholds(hours: float) -> tuple[int, int, float, float]:
    """Return (min_views, min_likes, min_vph, min_engagement) for given age."""
    cfg = AGE_AWARE_FILTER
    if hours <= cfg.t1_hours:
        return cfg.t1_views, cfg.t1_likes, cfg.t1_vph, cfg.t1_engagement
    if hours <= cfg.t6_hours:
        return cfg.t6_views, cfg.t6_likes, cfg.t6_vph, cfg.t6_engagement
    if hours <= cfg.t24_hours:
        return cfg.t24_views, cfg.t24_likes, cfg.t24_vph, cfg.t24_engagement
    if hours <= cfg.t72_hours:
        return cfg.t72_views, cfg.t72_likes, cfg.t72_vph, cfg.t72_engagement
    return cfg.else_views, cfg.else_likes, cfg.else_vph, cfg.else_engagement


def age_aware_filter(video: Video, debug: bool = False) -> AgeAwareFilterResult:
    """
    Soft filter with age-aware thresholds.
    Returns (passed, penalty, reason). Penalty is applied to viral_score.
    Reject only if penalty < 0.25.
    """
    cfg = AGE_AWARE_FILTER
    hours = _hours_since(video.publish_time)
    eng = _engagement_rate(video)
    vph = video.views / hours if hours > 0 else 0.0

    penalty = 1.0
    reasons: list[str] = []

    # Step 4: Protect new videos (hours < 2) — always pass to scoring
    if hours < cfg.early_age_hours:
        if video.views >= cfg.early_age_min_views:
            if debug:
                logger.debug(
                    f"[age_filter] {video.video_id}: passed due to early-age protection "
                    f"(views={video.views}, hours={hours:.1f})"
                )
            return AgeAwareFilterResult(True, 1.0, "early-age protection")
        # Still pass, but penalize low views so they rank lower
        penalty *= cfg.penalty_views
        reasons.append("low views (early age)")
        if debug:
            logger.debug(
                f"[age_filter] {video.video_id}: passed (early age) with penalty for low views "
                f"(views={video.views}, penalty={penalty:.2f})"
            )
        return AgeAwareFilterResult(True, penalty, "; ".join(reasons))
    else:
        # Step 2: Dynamic minimums
        min_views, min_likes, min_vph, min_engagement = _get_dynamic_thresholds(hours)

        if video.views < min_views:
            penalty *= cfg.penalty_views
            reasons.append(f"views {video.views} < {min_views} (age {hours:.0f}h)")
        if video.likes < min_likes:
            penalty *= cfg.penalty_likes
            reasons.append(f"likes {video.likes} < {min_likes} (age {hours:.0f}h)")
        if vph < min_vph:
            penalty *= cfg.penalty_vph
            reasons.append(f"vph {vph:.1f} < {min_vph} (age {hours:.0f}h)")
        if eng < min_engagement:
            penalty *= cfg.penalty_engagement
            reasons.append(f"engagement {eng:.4f} < {min_engagement} (age {hours:.0f}h)")

    # Optional penalties (no reject)
    if video.duration > cfg.max_duration_seconds:
        penalty *= cfg.penalty_duration
        reasons.append("long duration")
    if video.comments_disabled:
        penalty *= cfg.penalty_comments_disabled
        reasons.append("comments disabled")

    passed = penalty >= cfg.min_penalty_to_keep
    reason = "; ".join(reasons) if reasons else "ok"

    if debug:
        if passed:
            if penalty < 1.0:
                logger.debug(
                    f"[age_filter] {video.video_id}: passed, penalized for {reason} "
                    f"(penalty={penalty:.2f})"
                )
            else:
                logger.debug(f"[age_filter] {video.video_id}: passed (penalty={penalty:.2f})")
        else:
            logger.debug(
                f"[age_filter] {video.video_id}: rejected due to extremely weak metrics "
                f"(penalty={penalty:.2f}, {reason})"
            )

    return AgeAwareFilterResult(passed=passed, penalty=penalty, reason=reason)


def age_aware_filter_batch(
    videos: list[Video],
    min_keep: int = 40,
    debug: bool = False,
) -> tuple[list[tuple[Video, float]], int]:
    """
    Apply age-aware filter. Returns (candidates, rejected_count).
    Step 5: Always keep at least min_keep videos (safety limit).
    Candidates are (video, penalty) - penalty applied to viral_score later.
    """
    cfg = AGE_AWARE_FILTER
    min_keep = max(min_keep, cfg.min_candidates)

    results: list[tuple[Video, float, bool]] = []
    for v in videos:
        r = age_aware_filter(v, debug=debug)
        results.append((v, r.penalty, r.passed))

    passed = [(v, p) for v, p, ok in results if ok]
    rejected = [(v, p) for v, p, ok in results if not ok]
    originally_rejected = len(rejected)

    # Step 5: Keep at least top min_keep (safety limit)
    total = len(videos)
    if len(passed) < min_keep and total >= min_keep:
        rejected.sort(key=lambda x: x[1], reverse=True)
        needed = min(min_keep - len(passed), len(rejected))
        passed = passed + rejected[:needed]
        if debug:
            logger.debug(
                f"[age_filter] Safety: kept top {min_keep} (added {needed} from rejected)"
            )

    return passed, originally_rejected

