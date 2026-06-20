"""
POST /api/snapshot/{username}  — save current profile state as a snapshot
GET  /api/snapshots/{username} — list snapshots, newest first

Uses the profile_snapshots table (existed since Phase 1 migration,
unused until now).
"""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.profile import Developer, ProfileSnapshot, Repo
from app.services.health_score import compute_language_percentages, get_top_language

router = APIRouter()
logger = logging.getLogger(__name__)


class SnapshotResponse(BaseModel):
    id: str
    taken_at: str
    total_repos: int
    avg_health_score: float
    total_stars: int


class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotResponse]


async def create_snapshot(developer_id: str, db: DbSession) -> ProfileSnapshot:
    """
    Shared helper — called both by the manual POST endpoint and
    automatically from on_indexing_complete after a successful index run.
    """
    result = await db.execute(select(Repo).where(Repo.developer_id == developer_id))
    repos = result.scalars().all()

    scores = [r.health_score for r in repos if r.health_score is not None]
    avg_health = round(sum(scores) / len(scores), 1) if scores else 0.0
    total_stars = sum(r.stars or 0 for r in repos)
    total_commits = sum(r.commit_count or 0 for r in repos)

    merged_languages: dict[str, int] = {}
    for repo in repos:
        if repo.all_languages:
            for lang, bytes_ in repo.all_languages.items():
                merged_languages[lang] = merged_languages.get(lang, 0) + bytes_

    snapshot_data = {
        "total_repos": len(repos),
        "avg_health_score": avg_health,
        "total_stars": total_stars,
        "total_commits": total_commits,
        "top_language": get_top_language(merged_languages),
        "language_percentages": compute_language_percentages(merged_languages),
        "repos": [
            {
                "name": r.name,
                "health_score": r.health_score,
                "health_grade": r.health_grade.value if r.health_grade else None,
                "stars": r.stars,
            }
            for r in repos
        ],
    }

    snapshot = ProfileSnapshot(
        developer_id=developer_id,
        snapshot_data=snapshot_data,
        taken_at=datetime.now(UTC),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    logger.info(f"[snapshot] created for developer_id={developer_id}, repos={len(repos)}")
    return snapshot


@router.post("/snapshot/{username}", response_model=SnapshotResponse)
async def take_snapshot(username: str, db: DbSession) -> SnapshotResponse:
    username = username.lower().strip()

    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail=f"Developer '{username}' not found")

    snapshot = await create_snapshot(str(developer.id), db)

    return SnapshotResponse(
        id=str(snapshot.id),
        taken_at=snapshot.taken_at.isoformat(),
        total_repos=snapshot.snapshot_data["total_repos"],
        avg_health_score=snapshot.snapshot_data["avg_health_score"],
        total_stars=snapshot.snapshot_data["total_stars"],
    )


@router.get("/snapshots/{username}", response_model=SnapshotListResponse)
async def list_snapshots(username: str, db: DbSession) -> SnapshotListResponse:
    username = username.lower().strip()

    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail=f"Developer '{username}' not found")

    result = await db.execute(
        select(ProfileSnapshot)
        .where(ProfileSnapshot.developer_id == developer.id)
        .order_by(ProfileSnapshot.taken_at.desc())
        .limit(50)
    )
    snapshots = result.scalars().all()

    return SnapshotListResponse(
        snapshots=[
            SnapshotResponse(
                id=str(s.id),
                taken_at=s.taken_at.isoformat(),
                total_repos=s.snapshot_data.get("total_repos", 0),
                avg_health_score=s.snapshot_data.get("avg_health_score", 0.0),
                total_stars=s.snapshot_data.get("total_stars", 0),
            )
            for s in snapshots
        ]
    )
