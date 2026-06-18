"""
codesense — FastAPI application entry point.
"""

import sentry_sdk
from app.api.routes import analyze, profile
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# ── Sentry (only in production) ──────────────────────────
if settings.SENTRY_DSN_BACKEND and settings.ENVIRONMENT == "production":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN_BACKEND,
        traces_sample_rate=0.2,
        environment=settings.ENVIRONMENT,
    )

# ── App ───────────────────────────────────────────────────
app = FastAPI(
    title="codesense API",
    description="AI-powered GitHub developer profile analyzer",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(profile.router, prefix="/api", tags=["profile"])


# ── Health check ─────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
