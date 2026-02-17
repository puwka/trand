"""
Stage 6 — AI quality filter.
LLM classifies: spam, repost, low-effort template, real trend format.
Returns boolean: keep / discard. Does NOT rank.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx
from openai import OpenAI

from app.config import settings
from app.models.video_model import Video

logger = logging.getLogger(__name__)


def ai_quality_filter(video: Video) -> bool:
    """
    Call LLM to classify quality. Return True=keep, False=discard.
    Classify as: spam | repost | low-effort template | real trend format
    """
    title = (video.title or "")[:500]
    desc = (video.description or "")[:1500]
    hashtags = " ".join((video.hashtags or [])[:20])

    prompt = f"""Classify this video content. Categories:
- spam: promotional, unrelated, clickbait with no substance
- repost: likely reupload/duplicate of existing viral content
- low-effort template: generic template, low originality
- real trend format: original or creative take on a trend, worth keeping

Video:
Title: {title}
Description: {desc[:800]}
Hashtags: {hashtags}

Return ONLY valid JSON: {{"keep": true}} or {{"keep": false}}
Do not rank. Only filter quality: keep real trend format, discard spam/repost/low-effort.
"""

    try:
        verify_ssl = settings.openai_ssl_verify.lower() != "false"
        http_client = httpx.Client(verify=verify_ssl, timeout=30)
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.neuroapi_base_url,
            http_client=http_client,
        )
        response = client.chat.completions.create(
            model=settings.neuroapi_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content.strip()

        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            content = match.group(0)
        data = json.loads(content)
        keep = bool(data.get("keep", False))
        return keep
    except Exception as e:
        logger.warning(f"[ai_quality_filter] Error for {video.video_id}: {e}, defaulting to keep")
        return True  # On error, keep to avoid losing good content


def ai_quality_filter_batch(videos: list[Video], debug: bool = False) -> list[Video]:
    """Filter list, return only videos that pass."""
    passed = []
    for v in videos:
        if ai_quality_filter(v):
            passed.append(v)
        else:
            if debug:
                logger.debug(f"[ai_quality_filter] DISCARD {v.video_id}")
    return passed
