"""
POST /api/query — RAG question answering with SSE streaming.

Request:  { "username": "torvalds", "question": "when does he ship?" }
Response: SSE stream of events per the protocol in CLAUDE.md
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.agent.graph import run_agent
from app.api.deps import DbSession
from app.core.config import settings
from app.models.profile import Developer, Repo
from app.services.health_score import compute_language_percentages, get_top_language

router = APIRouter()
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    username: str
    question: str


async def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _build_stats(repos) -> dict:
    """Build stats dict matching the agent prompt expectations."""
    total_repos = len(repos)

    scores = [r.health_score for r in repos if r.health_score is not None]
    avg_health = round(sum(scores) / len(scores), 1) if scores else 0.0

    merged_languages: dict[str, int] = {}
    for repo in repos:
        if repo.all_languages:
            for lang, bytes_ in repo.all_languages.items():
                merged_languages[lang] = merged_languages.get(lang, 0) + bytes_

    language_percentages = compute_language_percentages(merged_languages)
    top_language = get_top_language(merged_languages)

    grade_counts = {"A": 0, "B": 0, "C": 0}
    repos_with_tests = 0
    repos_with_ci = 0
    total_stars = 0
    total_commits = 0

    for repo in repos:
        if repo.health_grade and repo.health_grade.value in grade_counts:
            grade_counts[repo.health_grade.value] += 1
        if repo.has_tests:
            repos_with_tests += 1
        if repo.has_ci:
            repos_with_ci += 1
        total_stars += repo.stars or 0
        total_commits += repo.commit_count or 0

    return {
        "total_repos": total_repos,
        "total_stars": total_stars,
        "total_commits": total_commits,
        "avg_health_score": avg_health,
        "primary_language": top_language,
        "language_percentages": language_percentages,
        "grade_counts": grade_counts,
        "repos_with_tests": repos_with_tests,
        "repos_with_ci": repos_with_ci,
    }


@router.post("/query")
async def query(body: QueryRequest, db: DbSession) -> StreamingResponse:
    username = body.username.strip().lower()
    question = body.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # Load developer
    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail=f"Developer '{username}' not found")

    # Load repos
    repos_result = await db.execute(
        select(Repo).where(Repo.developer_id == developer.id).order_by(Repo.health_score.desc())
    )
    repos = repos_result.scalars().all()

    # Build plain dicts — avoid SQLAlchemy lazy load issues inside the generator
    developer_dict = {
        "id": str(developer.id),
        "github_username": developer.github_username,
        "display_name": developer.display_name,
        "bio": developer.bio,
        "peak_commit_day": developer.peak_commit_day,
        "commit_frequency_per_week": developer.commit_frequency_per_week,
    }

    repos_list = [
        {
            "name": r.name,
            "primary_language": r.primary_language,
            "health_score": r.health_score,
            "health_grade": r.health_grade.value if r.health_grade else None,
            "stars": r.stars,
            "forks": r.forks,
            "commit_count": r.commit_count,
            "has_tests": r.has_tests,
            "has_ci": r.has_ci,
            "has_docker": r.has_docker,
            "has_license": r.has_license,
            "has_readme": r.has_readme,
        }
        for r in repos
    ]

    stats_dict = _build_stats(repos)

    async def event_stream():
        try:
            async for event in run_agent(
                question=question,
                developer=developer_dict,
                repos=repos_list,
                stats=stats_dict,
                groq_api_key=settings.GROQ_API_KEY,
                db=db,
            ):
                yield await _sse_event(event["event"], event["data"])
        except Exception as exc:
            logger.exception(f"[query] stream error: {exc}")
            yield await _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
