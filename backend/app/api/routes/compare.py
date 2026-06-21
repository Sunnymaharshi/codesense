"""
GET /api/compare/{user1}/{user2}

Returns two full profiles side by side. Reuses the exact same
fetch + stats logic as profile.py — just runs it twice.

Both usernames must already have been analyzed (POST /analyze)
before this works — we do NOT auto-trigger indexing here.
"""
import logging

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import settings
from app.models.profile import Developer, IndexStatus, Repo
from app.schemas.profile import (
    CompareResponse,
    DeveloperResponse,
    ProfileResponse,
    ProfileStatsResponse,
    RepoResponse,
)
from app.services.health_score import compute_language_percentages, get_top_language

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_SUMMARY_MODEL = "llama-3.3-70b-versatile"

router = APIRouter()


async def _load_profile(username: str, db: DbSession) -> ProfileResponse:
    """Shared logic — identical to profile.py's get_profile, factored out
    so compare.py doesn't duplicate the stats computation."""
    username = username.lower().strip()

    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()

    if developer is None:
        raise HTTPException(
            status_code=404,
            detail=f"'{username}' hasn't been indexed yet. Search them first to index their profile.",
        )

    if developer.index_status != IndexStatus.done:
        raise HTTPException(
            status_code=409,
            detail=f"'{username}' is still being indexed. Try again in a moment.",
        )

    result = await db.execute(
        select(Repo)
        .where(Repo.developer_id == developer.id)
        .order_by(Repo.health_score.desc().nullslast(), Repo.stars.desc())
    )
    repos = result.scalars().all()

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
    for repo in repos:
        if repo.health_grade and repo.health_grade.value in grade_counts:
            grade_counts[repo.health_grade.value] += 1

    stats = ProfileStatsResponse(
        total_repos=total_repos,
        total_stars=sum(r.stars for r in repos),
        total_forks=sum(r.forks for r in repos),
        total_commits=sum(r.commit_count for r in repos),
        avg_health_score=avg_health,
        primary_language=top_language,
        language_percentages=language_percentages,
        grade_counts=grade_counts,
        repos_with_tests=sum(1 for r in repos if r.has_tests),
        repos_with_ci=sum(1 for r in repos if r.has_ci),
    )

    return ProfileResponse(
        developer=DeveloperResponse.model_validate(developer),
        repos=[RepoResponse.model_validate(r) for r in repos],
        stats=stats,
    )


async def _generate_summary(left: ProfileResponse, right: ProfileResponse) -> str:
    prompt = (
        f"Compare these two GitHub developers in exactly 2 sentences. Be specific and direct.\n\n"
        f"{left.developer.github_username}: {left.stats.total_repos} repos, "
        f"avg health {left.stats.avg_health_score:.0f}/100, "
        f"{left.stats.total_stars} stars, "
        f"primary language {left.stats.primary_language or 'unknown'}, "
        f"{left.stats.grade_counts.get('A', 0)} A-grade repos.\n"
        f"{right.developer.github_username}: {right.stats.total_repos} repos, "
        f"avg health {right.stats.avg_health_score:.0f}/100, "
        f"{right.stats.total_stars} stars, "
        f"primary language {right.stats.primary_language or 'unknown'}, "
        f"{right.stats.grade_counts.get('A', 0)} A-grade repos."
    )
    try:
        client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=GROQ_BASE_URL)
        resp = await client.chat.completions.create(
            model=_SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        logger.exception("[compare] summary generation failed")
        return ""


@router.get("/compare/{user1}/{user2}", response_model=CompareResponse)
async def compare_developers(user1: str, user2: str, db: DbSession) -> CompareResponse:
    if user1.lower().strip() == user2.lower().strip():
        raise HTTPException(status_code=400, detail="Cannot compare a developer with themselves")

    left = await _load_profile(user1, db)
    right = await _load_profile(user2, db)
    summary = await _generate_summary(left, right)

    return CompareResponse(left=left, right=right, summary=summary)
