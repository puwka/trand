"""
Minimal Supabase client via REST API. No supabase-py (avoids gotrue/httpx conflicts).
Uses only httpx.
"""

from typing import Any

import httpx

from app.config import settings


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest(path: str) -> str:
    base = settings.supabase_url.rstrip("/")
    return f"{base}/rest/v1/{path.lstrip('/')}"


def table(name: str) -> "TableClient":
    return TableClient(name)


class TableClient:
    def __init__(self, name: str):
        self.name = name
        self.url = _rest(self.name)

    def select(self, columns: str = "*", order: str | None = None, desc: bool = False, **filters) -> list[dict]:
        params: dict[str, Any] = {"select": columns}
        if order:
            params["order"] = f"{order}.{'desc' if desc else 'asc'}"
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        with httpx.Client(timeout=25) as client:
            r = client.get(self.url, headers=_headers(), params=params)
            r.raise_for_status()
            return r.json() or []

    def insert(self, data: dict | list[dict]) -> list[dict]:
        with httpx.Client(timeout=25) as client:
            r = client.post(self.url, headers=_headers(), json=data)
            r.raise_for_status()
            return r.json() or []

    def update(self, data: dict, **filters) -> list[dict]:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        with httpx.Client(timeout=25) as client:
            r = client.patch(self.url, headers=_headers(), params=params, json=data)
            r.raise_for_status()
            return r.json() or []

    def delete(self, **filters) -> None:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        with httpx.Client(timeout=25) as client:
            r = client.delete(self.url, headers=_headers(), params=params)
            r.raise_for_status()


def storage_upload(bucket: str, path: str, data: bytes, content_type: str) -> str:
    """Upload file to Supabase Storage. Returns public URL."""
    base = settings.supabase_url.rstrip("/")
    url = f"{base}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": content_type,
    }
    with httpx.Client(timeout=25) as client:
        r = client.post(url, headers=headers, content=data)
        r.raise_for_status()
    return f"{base}/storage/v1/object/public/{bucket}/{path}"
