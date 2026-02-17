import json
import re
from typing import Any

import httpx
import yt_dlp
from openai import OpenAI

from app.config import settings
from app.services.yt_utils import yt_dlp_cookie_opts


def extract_metadata(video_url: str) -> dict[str, Any]:
    """Extract video metadata using yt-dlp without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }
    ydl_opts.update(yt_dlp_cookie_opts())
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        if not info:
            raise ValueError(f"Could not extract info from {video_url}")
        return {
            "title": info.get("title", ""),
            "description": info.get("description", "") or "",
            "id": info.get("id", ""),
        }


def analyze_video(
    title: str, description: str, topics: list[dict[str, str]]
) -> dict[str, Any]:
    """
    Send metadata + topics to ChatGPT (NeuroAPI).
    Returns: {is_viral: bool, score: int 1-10, summary: str}
    """
    topics_str = ", ".join(
        f"{t['keyword']}: {t.get('description', '')}" for t in topics
    )
    prompt = f"""Analyze if this video fits the topics: {topics_str}

Video:
Title: {title}
Description: {description[:1000]}

Return ONLY valid JSON in this exact format, no other text:
{{"is_viral": true/false, "score": 1-10, "summary": "brief summary"}}
"""

    verify_ssl = settings.openai_ssl_verify.lower() != "false"
    http_client = httpx.Client(verify=verify_ssl, timeout=60)
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.neuroapi_base_url,
        http_client=http_client,
    )
    response = client.chat.completions.create(
        model=settings.neuroapi_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    content = response.choices[0].message.content.strip()

    # Try to parse JSON from response (handle markdown code blocks)
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        content = match.group(0)
    data = json.loads(content)

    return {
        "is_viral": bool(data.get("is_viral", False)),
        "score": min(10, max(1, int(data.get("score", 5)))),
        "summary": str(data.get("summary", ""))[:2000],
    }
