"""
Railway entrypoint. FastAPI + static frontend + background worker.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

_backend = Path(__file__).resolve().parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


def _static_dir() -> Path | None:
    """Frontend build dir: frontend_dist (Docker) or ../frontend/dist (local)."""
    candidates = [
        _backend / "frontend_dist",  # Docker
        _backend.parent / "frontend" / "dist",  # local
    ]
    for p in candidates:
        if p.exists() and (p / "index.html").exists():
            return p
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.worker import start_worker

    start_worker(interval_minutes=60)
    yield


app = FastAPI(
    title="Trend Watching API",
    description="Monitors short videos from TikTok, Reels, Shorts",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.(railway\.app|vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])


@app.get("/health")
def health():
    """Healthcheck for Railway."""
    return {"status": "ok"}


static = _static_dir()
if static:
    app.mount("/", StaticFiles(directory=str(static), html=True), name="static")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "service": "trend-watching-api"}
