import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure "app" package is findable (app lives in backend/app)
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip background worker on Vercel (serverless)
    if not os.getenv("VERCEL"):
        from app.worker import start_worker
        start_worker(interval_minutes=60)
    yield
    # shutdown


app = FastAPI(
    title="Trend Watching API",
    description="Monitors short videos from TikTok, Reels, Shorts",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])


@app.get("/")
def root():
    return {"status": "ok", "service": "trend-watching-api"}
