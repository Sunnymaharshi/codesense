"""
GET /api/admin/stats — aggregate LLM call stats for the cost dashboard.
GET /api/admin/calls — recent LLM calls (last 50).
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.llm_call import LLMCall

router = APIRouter()
logger = logging.getLogger(__name__)


class AdminStats(BaseModel):
    total_calls: int
    total_cost_usd: float
    avg_duration_ms: float
    calls_last_24h: int
    tokens_in_total: int
    tokens_out_total: int


class CallRow(BaseModel):
    id: int
    endpoint: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_ms: int
    github_username: str | None
    created_at: str


class AdminCallsResponse(BaseModel):
    calls: list[CallRow]


@router.get("/admin/stats", response_model=AdminStats)
async def admin_stats(db: DbSession) -> AdminStats:
    result = await db.execute(
        select(
            func.count(LLMCall.id),
            func.coalesce(func.sum(LLMCall.cost_usd), 0.0),
            func.coalesce(func.avg(LLMCall.duration_ms), 0.0),
            func.coalesce(func.sum(LLMCall.tokens_in), 0),
            func.coalesce(func.sum(LLMCall.tokens_out), 0),
        )
    )
    row = result.one()
    total_calls, total_cost, avg_duration, tokens_in, tokens_out = row

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    count_24h = await db.execute(
        select(func.count(LLMCall.id)).where(LLMCall.created_at >= cutoff)
    )
    calls_last_24h = count_24h.scalar_one()

    return AdminStats(
        total_calls=total_calls or 0,
        total_cost_usd=round(float(total_cost), 6),
        avg_duration_ms=round(float(avg_duration), 1),
        calls_last_24h=calls_last_24h or 0,
        tokens_in_total=int(tokens_in),
        tokens_out_total=int(tokens_out),
    )


@router.get("/admin/calls", response_model=AdminCallsResponse)
async def admin_calls(db: DbSession) -> AdminCallsResponse:
    result = await db.execute(
        select(LLMCall).order_by(LLMCall.created_at.desc()).limit(50)
    )
    calls = result.scalars().all()
    return AdminCallsResponse(
        calls=[
            CallRow(
                id=c.id,
                endpoint=c.endpoint,
                model=c.model,
                tokens_in=c.tokens_in,
                tokens_out=c.tokens_out,
                cost_usd=c.cost_usd,
                duration_ms=c.duration_ms,
                github_username=c.github_username,
                created_at=c.created_at.isoformat(),
            )
            for c in calls
        ]
    )
