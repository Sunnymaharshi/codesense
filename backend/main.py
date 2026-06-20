"""
codesense — FastAPI application entry point.
"""

import logging
import time

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.routes import admin as admin_routes
from app.api.routes import agent_trace as agent_trace_routes
from app.api.routes import analyze, profile
from app.api.routes import compare as compare_routes
from app.api.routes import query as query_routes
from app.api.routes import snapshot as snapshot_routes
from app.api.routes import ws as ws_routes
from app.core.config import settings

access_logger = logging.getLogger("codesense.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        access_logger.info(
            '{"method":"%s","path":"%s","status":%d,"duration_ms":%d}',
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

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
app.add_middleware(AccessLogMiddleware)

# ── Routers ──────────────────────────────────────────────
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(compare_routes.router, prefix="/api", tags=["compare"])
app.include_router(snapshot_routes.router, prefix="/api", tags=["snapshot"])
app.include_router(agent_trace_routes.router, prefix="/api", tags=["agent"])
app.include_router(admin_routes.router, prefix="/api", tags=["admin"])
app.include_router(ws_routes.router)
app.include_router(query_routes.router, prefix="/api")


# ── Health check ─────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
