"""
Background Worker: Viral trend detector pipeline.
Fetch -> Hard filter -> Score -> Sort -> AI quality filter (top 30%) -> Save.
"""

import asyncio
import logging
from collections import defaultdict

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import ingestion_settings
from app.database import table
from app.models.video_model import Video
from app.services.collector_service import fetch_from_sources
from app.services.ingestion_helpers import parse_source_identifier, platform_to_collector
from app.adapters.apify.apify_client import ApifyCreditsExhaustedError
from app.services.quality_gate import apply_quality_gate, GateResult
from app.services.viral_pipeline import run_viral_pipeline

logging.basicConfig(level=logging.INFO)

# True when scheduler is running a cycle (auto-parse)
_parsing_in_progress = False


def is_parsing_in_progress() -> bool:
    return _parsing_in_progress


_CREDIT_KEYWORDS = ("credit", "quota", "usage limit", "exceeded", "plan limit", "insufficient", "лимит", "кредит")


def _is_source_credits_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(kw in msg for kw in _CREDIT_KEYWORDS)


logger = logging.getLogger(__name__)


def run_worker_cycle():
    """One iteration: fetch -> viral pipeline -> save top videos."""
    global _parsing_in_progress
    _parsing_in_progress = True
    try:
        return _run_worker_cycle()
    finally:
        _parsing_in_progress = False


def _run_worker_cycle():
    """Inner implementation of worker cycle."""
    stats = {"processed": 0, "viral": 0, "skipped": 0, "errors": 0, "rejected_filter": 0}

    topics = table("topics").select()
    if not topics:
        logger.info("No topics configured, skipping cycle")
        return stats

    topic_keywords = [t.get("keyword", "") for t in topics if t.get("keyword")]
    sources = table("sources").select(order="created_at", desc=True)
    sources = [s for s in sources if s.get("status") == "active"]
    if not sources:
        logger.info("No active sources, skipping cycle")
        return stats

    by_platform: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    for src in sources:
        platform = (src.get("platform") or "").lower()
        url = src.get("url", "")
        ident = parse_source_identifier(platform, url)
        if ident:
            coll_platform = platform_to_collector(platform)
            by_platform[coll_platform].append((src, ident))

    if by_platform:
        logger.info("Worker fetching from platforms: %s", {p: len(v) for p, v in by_platform.items()})

    all_videos: list[tuple[dict, Video]] = []
    for coll_platform, items in by_platform.items():
        channel_list = [ident for _, ident in items]
        try:
            videos = asyncio.run(fetch_from_sources(channel_list, coll_platform))
            for v in videos:
                all_videos.append((items[0][0], v))
        except ApifyCreditsExhaustedError as e:
            logger.exception(f"Fetch failed for {coll_platform}: {e}")
            stats["errors"] += 1
            stats["error_message"] = str(e)
        except Exception as e:
            logger.exception(f"Fetch failed for {coll_platform}: {e}")
            stats["errors"] += 1
            if _is_source_credits_error(e):
                stats["error_message"] = f"Источник {coll_platform}: {e}"

    if not all_videos:
        return stats

    videos = [v for _, v in all_videos]
    video_to_source = {(v.platform, v.video_id): src for src, v in all_videos}

    result = run_viral_pipeline(videos, topic_keywords, debug=True)
    stats["rejected_filter"] = result.rejected_by_filter

    # Quality gate: only strong videos enter DB (after scoring, before save)
    gated: list[GateResult] = apply_quality_gate(result.videos)

    from app.config.viral_config import OUTPUT_CONFIG

    for gate in gated:
        video = gate.video
        breakdown = gate.breakdown
        try:
            external_id = f"{video.platform}:{video.video_id}"
            existing = table("videos").select(columns="id", external_id=external_id)
            if existing:
                stats["skipped"] += 1
                continue

            source = video_to_source.get((video.platform, video.video_id), all_videos[0][0])
            title = (video.title or video.description or "")[:200] or "Video"
            desc = (video.description or "")[:5000]

            viral_score = breakdown.viral_score
            virality_score = min(
                10,
                max(1, int(viral_score * OUTPUT_CONFIG.virality_scale)),
            )
            is_viral = viral_score >= OUTPUT_CONFIG.viral_score_threshold

            record = {
                "source_id": source["id"],
                "external_id": external_id,
                "title": title,
                "description": desc,
                "ai_summary": breakdown.explanation[:2000],
                "virality_score": virality_score,
                "is_viral": is_viral,
                "storage_path": video.url,
                "quality_decision_reason": gate.quality_decision_reason,
            }

            if ingestion_settings.DRY_RUN:
                logger.info(
                    "[DRY_RUN] Would save: %s score=%.2f viral=%s",
                    title[:50],
                    viral_score,
                    is_viral,
                )
                stats["processed"] += 1
                if is_viral:
                    stats["viral"] += 1
                continue

            try:
                table("videos").insert(record)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    stats["skipped"] += 1
                    continue
                raise

            stats["processed"] += 1
            if is_viral:
                stats["viral"] += 1
            logger.info(
                f"Saved {title[:50]}... score={viral_score:.2f} viral={is_viral} "
                f"({breakdown.explanation})"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                stats["skipped"] += 1
            else:
                stats["errors"] += 1
                logger.exception(f"Error saving video {video.video_id}: {e}")
        except Exception as e:
            stats["errors"] += 1
            logger.exception(f"Error saving video {video.video_id}: {e}")

    return stats


def start_worker(interval_minutes: int = 30):
    """Start the background scheduler."""
    from datetime import datetime

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_worker_cycle,
        "interval",
        minutes=interval_minutes,
        id="trend_worker",
        next_run_time=datetime.now(),
    )
    scheduler.start()
    logger.info(f"Worker started, interval={interval_minutes} min")
