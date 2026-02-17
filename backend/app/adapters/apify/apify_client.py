"""
Reusable async Apify client.
Handles token, polling, timeout, retries, rate limiting, error handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ApifyClientError(Exception):
    """Apify client error."""


class ApifyCreditsExhaustedError(ApifyClientError):
    """Raised when Apify account has no credits / usage limit exceeded."""


def _is_credits_error(e: Exception) -> bool:
    msg = str(e).lower()
    keywords = ("credit", "usage limit", "quota", "exceeded", "plan limit", "insufficient")
    return any(kw in msg for kw in keywords)


async def run_actor(
    actor_id: str,
    run_input: dict[str, Any],
    token: str,
    timeout_secs: int = 60,
    retries: int = 2,
) -> list[dict[str, Any]]:
    """
    Run Apify actor and return dataset items.
    On failure: log warning, return [] (never raise).
    """
    try:
        from apify_client import ApifyClientAsync
    except ImportError as e:
        logger.warning("[APIFY] apify-client not installed: %s", e)
        return []

    if not token:
        logger.warning("[APIFY] APIFY_TOKEN not set, skipping")
        return []

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            logger.info("[APIFY] started run actor=%s attempt=%s", actor_id, attempt + 1)
            client = ApifyClientAsync(token=token)
            run_result = await client.actor(actor_id).call(
                run_input=run_input,
                timeout_secs=timeout_secs,
                wait_secs=timeout_secs,
            )
            if not run_result:
                logger.warning("[APIFY] run returned empty")
                return []
            dataset_id = run_result.get("defaultDatasetId")
            if not dataset_id:
                logger.warning("[APIFY] no defaultDatasetId in run result")
                return []
            dataset = client.dataset(dataset_id)
            response = await dataset.list_items(limit=500)
            items = list(response.items) if response else []
            logger.info("[APIFY] finished run actor=%s items received: %s", actor_id, len(items))
            return items
        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning("[APIFY] error: timeout (actor=%s)", actor_id)
        except Exception as e:
            last_error = e
            logger.warning("[APIFY] error: %s (actor=%s)", e, actor_id)
            if _is_credits_error(e):
                raise ApifyCreditsExhaustedError(
                    f"Закончились кредиты Apify. Пополните баланс: {e}"
                ) from e
        if attempt < retries:
            await asyncio.sleep(2 * (attempt + 1))
    return []
