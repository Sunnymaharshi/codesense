"""
GET /api/compare/{user1}/{user2}

Returns two full profiles side by side. Reuses the exact same
fetch + stats logic as profile.py — just runs it twice.

Both usernames must already have been analyzed (POST /analyze)
before this works — we do NOT auto-trigger indexing here.
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.profile import Developer, Repo
from app.schemas.profile import (
    CompareResponse,
    DeveloperResponse,
    ProfileResponse,
    ProfileStatsResponse,
    RepoResponse,
)
from app.services.health_score import compute_language_percentages, get_top_language

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
            detail=f"Developer '{username}' not found. POST /api/analyze first.",
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
        avg_health_score=avg_health,
        top_language=top_language,
        language_percentages=language_percentages,
        grade_counts=grade_counts,
    )

    return ProfileResponse(
        developer=DeveloperResponse.model_validate(developer),
        repos=[RepoResponse.model_validate(r) for r in repos],
        stats=stats,
    )


@router.get("/compare/{user1}/{user2}", response_model=CompareResponse)
async def compare_developers(user1: str, user2: str, db: DbSession) -> CompareResponse:
    if user1.lower().strip() == user2.lower().strip():
        raise HTTPException(status_code=400, detail="Cannot compare a developer with themselves")

    left = await _load_profile(user1, db)
    right = await _load_profile(user2, db)

    return CompareResponse(left=left, right=right)
