"""
GET /api/profile/{username}

Returns the full developer profile: developer info, all repos
sorted by health score, and aggregated stats.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.profile import Developer, Repo
from app.schemas.profile import (
    DeveloperResponse,
    ProfileResponse,
    ProfileStatsResponse,
    RepoResponse,
)
from app.services.health_score import compute_language_percentages, get_top_language

router = APIRouter()


@router.get("/profile/{username}", response_model=ProfileResponse)
async def get_profile(username: str, db: DbSession) -> ProfileResponse:
    username = username.lower().strip()

    # ── Fetch developer ──────────────────────────────────
    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()

    if developer is None:
        raise HTTPException(
            status_code=404,
            detail=f"Developer '{username}' not found. POST /api/analyze first.",
        )

    # ── Fetch repos ──────────────────────────────────────
    result = await db.execute(
        select(Repo)
        .where(Repo.developer_id == developer.id)
        .order_by(Repo.health_score.desc().nullslast(), Repo.stars.desc())
    )
    repos = result.scalars().all()

    # ── Compute stats ────────────────────────────────────
    total_repos = len(repos)

    # Average health score (exclude None)
    scores = [r.health_score for r in repos if r.health_score is not None]
    avg_health = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Merge all language byte counts across all repos
    merged_languages: dict[str, int] = {}
    for repo in repos:
        if repo.all_languages:
            for lang, bytes_ in repo.all_languages.items():
                merged_languages[lang] = merged_languages.get(lang, 0) + bytes_

    language_percentages = compute_language_percentages(merged_languages)
    top_language = get_top_language(merged_languages)

    # Grade distribution
    grade_counts = {"A": 0, "B": 0, "C": 0}
    for repo in repos:
        if repo.health_grade and repo.health_grade in grade_counts:
            grade_counts[repo.health_grade] += 1

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
