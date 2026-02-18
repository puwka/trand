from fastapi import APIRouter, Body, HTTPException

from app.database import table
from app.models import (
    SourceCreate,
    SourceResponse,
    TopicCreate,
    TopicResponse,
    VideoResponse,
)

router = APIRouter()


def _sources():
    return table("sources")


def _topics():
    return table("topics")


def _videos():
    return table("videos")


# --- Sources ---
@router.get("/sources", response_model=list[SourceResponse])
def list_sources():
    return _sources().select(order="created_at", desc=True)


@router.post("/sources", response_model=SourceResponse)
def create_source(source: SourceCreate):
    r = _sources().insert(source.dict())
    if not r:
        raise HTTPException(status_code=500, detail="Failed to create source")
    return r[0]


@router.delete("/sources/{source_id}")
def delete_source(source_id: str):
    _sources().delete(id=source_id)
    return {"ok": True}


@router.patch("/sources/{source_id}", response_model=SourceResponse)
def update_source(source_id: str, body: dict = Body(...)):
    """Update source. Body: {platform?, url?, status?}."""
    allowed = {"platform", "url", "status"}
    payload = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    r = _sources().update(payload, id=source_id)
    if not r:
        raise HTTPException(status_code=404, detail="Source not found")
    return r[0]


# --- Topics ---
@router.get("/topics", response_model=list[TopicResponse])
def list_topics():
    return _topics().select(order="created_at", desc=True)


@router.post("/topics", response_model=TopicResponse)
def create_topic(topic: TopicCreate):
    r = _topics().insert(topic.dict())
    if not r:
        raise HTTPException(status_code=500, detail="Failed to create topic")
    return r[0]


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: str):
    _topics().delete(id=topic_id)
    return {"ok": True}


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
def update_topic(topic_id: str, body: dict = Body(...)):
    """Update topic. Body: {keyword?, description?}."""
    allowed = {"keyword", "description"}
    payload = {k: v for k, v in body.items() if k in allowed}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    r = _topics().update(payload, id=topic_id)
    if not r:
        raise HTTPException(status_code=404, detail="Topic not found")
    return r[0]


# --- Videos ---
@router.get("/videos", response_model=list[VideoResponse])
def list_videos():
    return _videos().select(order="created_at", desc=True, is_viral="true")


@router.get("/videos/all", response_model=list[VideoResponse])
def list_all_videos():
    return _videos().select(order="created_at", desc=True)


@router.delete("/videos/{video_id}")
def delete_video(video_id: str):
    rows = _videos().select(columns="id", id=video_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Video not found")
    _videos().delete(id=video_id)
    return {"ok": True}


@router.get("/parse-now/status")
def parse_now_status():
    """Проверка: идёт ли парсинг (авто или вручную)."""
    from app.worker import is_parsing_in_progress

    return {"running": is_parsing_in_progress()}


@router.post("/parse-now")
async def parse_now():
    """Запустить парсинг вручную."""
    from app.worker import run_worker_cycle

    stats = await run_worker_cycle()
    if stats.get("error_message"):
        return {"ok": False, "message": stats["error_message"], **stats}
    sources = _sources().select()
    sources_active = [s for s in sources if s.get("status") == "active"]
    topics = _topics().select()

    if not topics:
        return {"ok": True, "message": "Добавьте хотя бы одну тему в Настройках", **stats}
    if not sources_active:
        return {"ok": True, "message": "Добавьте хотя бы один источник (канал) в Настройках", **stats}
    if stats["processed"] == 0 and stats["skipped"] == 0 and stats["errors"] == 0:
        return {
            "ok": True,
            "message": "Видео не найдено за последние 30 дней. Проверьте формат URL (для YouTube: youtube.com/@username или youtube.com/channel/UC...) и что канал публикует Shorts.",
            **stats,
        }

    msg = f"Обработано: {stats['processed']}, вирусных: {stats['viral']}"
    if stats.get("rejected_filter", 0):
        msg += f", отфильтровано: {stats['rejected_filter']}"
    if stats["skipped"]:
        msg += f", пропущено (уже есть): {stats['skipped']}"
    if stats["errors"]:
        msg += f", ошибок: {stats['errors']}"
    return {"ok": True, "message": msg, **stats}


def _normalize_sheet_id(value: str) -> str:
    """Extract spreadsheet ID from URL or raw ID."""
    if not value or not value.strip():
        return ""
    s = value.strip().strip('"\'')
    # URL: .../d/ID/edit or .../d/ID?...
    if "/d/" in s:
        s = s.split("/d/")[-1].split("/")[0].split("?")[0].split("#")[0]
    # Raw ID with trailing path
    elif "/" in s or "?" in s:
        s = s.split("/")[0].split("?")[0].split("#")[0]
    return s.strip()


# --- Export to Google Sheets ---
@router.post("/export/google-sheets")
def export_to_google_sheets():
    """Выгрузить видео в Google Таблицу."""
    import os
    from app.config import settings
    from app.services.google_sheets_export import export_videos_to_sheet

    raw = settings.google_sheet_id or os.getenv("GOOGLE_SHEET_ID", "")
    sheet_id = _normalize_sheet_id(raw)
    if not sheet_id:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_SHEET_ID не настроен. Добавьте в .env ID таблицы из URL: docs.google.com/spreadsheets/d/ID/edit",
        )

    videos = _videos().select(order="created_at", desc=True)
    result = export_videos_to_sheet(videos, sheet_id=sheet_id)
    if not result["ok"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# --- Config status (для настроек, без секретов) ---
@router.get("/config/status")
def config_status():
    """Текущий статус интеграций (без секретов)."""
    from app.config import settings, ingestion_settings

    return {
        "youtube": bool(ingestion_settings.YOUTUBE_API_KEY),
        "apify": bool(ingestion_settings.USE_APIFY and ingestion_settings.APIFY_TOKEN),
        "google_sheets": bool(getattr(settings, "google_sheet_id", "") or ""),
        "dry_run": ingestion_settings.DRY_RUN,
        "debug": ingestion_settings.DEBUG,
    }


@router.get("/config/parser")
def config_parser():
    """Параметры парсера (из .env)."""
    from app.config import ingestion_settings

    return {
        "max_results_per_platform": ingestion_settings.MAX_RESULTS_PER_PLATFORM,
        "request_timeout": ingestion_settings.REQUEST_TIMEOUT,
        "retry_count": ingestion_settings.RETRY_COUNT,
        "apify_timeout_secs": ingestion_settings.APIFY_TIMEOUT_SECS,
    }
