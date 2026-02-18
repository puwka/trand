"""
Serverless-safe FastAPI app. No startup side effects.
Routes are included; heavy deps load only when endpoints are called.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Lazy: router imports are lightweight (DB/client init happens in handlers)
from app.api.routes import router

app = FastAPI(
    title="Trend Watching API",
    description="Monitors short videos from TikTok, Reels, Shorts",
    version="1.0.0",
    lifespan=None,  # No lifespan = no startup/shutdown
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


@app.get("/health")
def health():
    """Healthcheck. No DB, no external APIs."""
    return {"status": "ok"}
