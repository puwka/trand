"""
Export videos to Google Sheets.
Requires: GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON (path to service account JSON).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_credentials_path() -> Optional[str]:
    """Path to service account JSON. Env: GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS."""
    path = os.getenv("GOOGLE_CREDENTIALS_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    return path if path and os.path.isfile(path) else None


def _get_service_account_email() -> str:
    """Read client_email from credentials JSON for error messages."""
    path = _get_credentials_path()
    if not path:
        return ""
    try:
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("client_email", "")
    except Exception:
        return ""


def _get_service():
    """Create Google Sheets API service with service account."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as e:
        logger.warning("[google_sheets] Missing deps: %s", e)
        return None

    creds_path = _get_credentials_path()
    if not creds_path:
        logger.warning("[google_sheets] GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS not set or file not found")
        return None

    try:
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        return build("sheets", "v4", credentials=creds)
    except Exception as e:
        logger.warning("[google_sheets] Failed to create service: %s", e)
        return None


def _format_date(dt: Any) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    if isinstance(dt, str):
        return dt[:19] if len(dt) >= 19 else dt
    return str(dt)


def export_videos_to_sheet(
    videos: list[dict],
    sheet_id: str,
    sheet_name: str = "Sheet1",
) -> dict[str, Any]:
    """
    Export videos to Google Sheet. Overwrites the sheet with fresh data.
    Returns dict with success, message, rows_added.
    """
    service = _get_service()
    if not service:
        return {"ok": False, "message": "Google Sheets не настроен. Добавьте GOOGLE_CREDENTIALS_JSON и GOOGLE_SHEET_ID в .env", "rows_added": 0}

    headers = ["Ссылка", "Название", "Описание", "AI Summary", "Оценка", "Вирусное", "Дата"]
    rows = [headers]

    for v in videos:
        ext_id = v.get("external_id") or ""
        platform, vid = ("", ext_id) if ":" not in ext_id else ext_id.split(":", 1)
        url = _video_url(platform, vid, v.get("storage_path"))
        title = str(v.get("title") or "")[:500]
        desc = str(v.get("description") or "")[:2000]
        summary = str(v.get("ai_summary") or "")[:1000]
        score = v.get("virality_score") or 0
        viral = "Да" if v.get("is_viral") else "Нет"
        created = _format_date(v.get("created_at"))
        rows.append([url, title, desc, summary, score, viral, created])

    if not videos:
        return {"ok": True, "message": "Нет видео для выгрузки", "rows_added": 0}

    try:
        body = {"values": rows}
        # Use A1 without sheet name — targets first sheet regardless of locale (Sheet1/Лист1)
        range_ = "A1"
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        return {
            "ok": True,
            "message": f"Выгружено {len(rows) - 1} видео в Google Таблицу",
            "rows_added": len(rows) - 1,
        }
    except Exception as e:
        logger.exception("[google_sheets] Export failed: %s", e)
        err_msg = str(e)
        if "404" in err_msg or "not found" in err_msg.lower():
            return {"ok": False, "message": "Таблица не найдена. Убедитесь, что GOOGLE_SHEET_ID верный и таблица расшарена с service account email.", "rows_added": 0}
        if "quotaExceeded" in err_msg.lower():
            return {"ok": False, "message": "Превышена квота Google Sheets API. Подождите несколько минут и попробуйте снова.", "rows_added": 0}
        if "403" in err_msg or "permission" in err_msg.lower():
            email = _get_service_account_email()
            hint = f" Добавьте этот email в «Поделиться» таблицы с правом Редактор: {email}" if email else ""
            return {"ok": False, "message": f"Нет доступа к таблице (403).{hint}", "rows_added": 0}
        return {"ok": False, "message": f"Ошибка: {err_msg[:200]}", "rows_added": 0}


def _video_url(platform: str, vid: str, storage_path: Optional[str]) -> str:
    if storage_path and (storage_path.startswith("http://") or storage_path.startswith("https://")):
        return storage_path
    platform = (platform or "").lower()
    if platform == "youtube" and len(vid) == 11:
        return f"https://www.youtube.com/watch?v={vid}"
    if platform == "tiktok":
        return f"https://www.tiktok.com/@_/video/{vid}"
    if platform == "reels":
        return f"https://www.instagram.com/reel/{vid}/" if vid else ""
    return storage_path or ""
