"""
codesense — FastAPI application entry point.
"""

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, profile
from app.api.routes import ws as ws_routes
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

http_origins = [o.strip().rstrip("/") for o in settings.CORS_ORIGINS.split(",")]
ws_origins = [o.replace("http://", "ws://").replace("https://", "wss://") for o in http_origins]
all_origins = http_origins + ws_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(ws_routes.router)


# ── Health check ─────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
