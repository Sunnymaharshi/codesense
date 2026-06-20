"""
GET /api/profile/{username}/agent-trace

Returns LangSmith project URL + persisted analysis results for a developer.
Returns has_analysis: false if the Phase 4 agent hasn't run yet.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import settings
from app.models.profile import Developer

router = APIRouter()


@router.get("/profile/{username}/agent-trace")
async def agent_trace(username: str, db: DbSession):
    result = await db.execute(
        select(Developer).where(Developer.github_username == username.strip().lower())
    )
    developer = result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail=f"Developer '{username}' not found")

    if not developer.skill_scores and not developer.ai_persona:
        return {"has_analysis": False, "trace_url": None, "skill_scores": None, "ai_persona": None}

    trace_url = None
    if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
        project = settings.LANGCHAIN_PROJECT or "codesense"
        trace_url = f"https://smith.langchain.com/projects/{project}"

    return {
        "has_analysis": True,
        "trace_url": trace_url,
        "skill_scores": developer.skill_scores,
        "ai_persona": developer.ai_persona,
    }
