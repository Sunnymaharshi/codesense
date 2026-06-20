"""
app/api/routes/analyze.py — Phase 4 update

Adds staleness check: if developer was indexed less than 1 hour ago,
return the existing data instead of re-triggering a full Celery fan-out.
Protects the free Groq/GitHub rate limits on a public demo from being
exhausted by repeated re-indexing of the same popular username.

Pass ?force=true to bypass and re-index anyway (used by the "Re-index"
button in SnapshotInfo on the frontend).
"""
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, GitHubDep
from app.models.profile import Developer, IndexingJob, IndexStatus
from app.schemas.profile import AnalyzeRequest, AnalyzeResponse
from app.workers.index_repo import index_developer

router = APIRouter()
logger = logging.getLogger(__name__)

STALENESS_WINDOW = timedelta(hours=1)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_user(
    body: AnalyzeRequest,
    db: DbSession,
    github: GitHubDep,
    force: bool = False,
) -> AnalyzeResponse:
    username = body.github_username.strip().lower()

    result = await db.execute(
        select(Developer).where(Developer.github_username == username)
    )
    developer = result.scalar_one_or_none()

    # ── In-progress guard ────────────────────────────────────────────────
    if developer and developer.index_status in (IndexStatus.pending, IndexStatus.running):
        logger.info(f"[analyze] @{username} indexing already in progress, skipping")
        return AnalyzeResponse(
            developer_id=developer.id,
            job_id=None,
            github_username=username,
            status=developer.index_status,
            message=f"@{username} is already being indexed. Please wait.",
        )

    # ── Staleness check ──────────────────────────────────────────────────
    if (
        not force
        and developer
        and developer.index_status == IndexStatus.done
        and developer.indexed_at
        and datetime.now(UTC) - developer.indexed_at < STALENESS_WINDOW
    ):
        logger.info(f"[analyze] @{username} indexed recently, skipping re-index")
        return AnalyzeResponse(
            developer_id=developer.id,
            job_id=None,
            github_username=username,
            status=IndexStatus.done,
            message=f"@{username} was indexed recently. Showing cached profile.",
        )

    # Validate user exists on GitHub
    gh_user = await github.get_user(username)
    if not gh_user:
        raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found")

    if developer:
        developer.display_name = gh_user.get("name")
        developer.avatar_url = gh_user.get("avatar_url")
        developer.bio = gh_user.get("bio")
        developer.index_status = IndexStatus.pending
    else:
        developer = Developer(
            github_username=username,
            display_name=gh_user.get("name"),
            avatar_url=gh_user.get("avatar_url"),
            bio=gh_user.get("bio"),
            index_status=IndexStatus.pending,
        )
        db.add(developer)

    await db.flush()

    job = IndexingJob(
        developer_id=developer.id,
        status=IndexStatus.pending,
        repos_done=0,
        repos_total=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(developer)
    await db.refresh(job)

    index_developer.delay(str(developer.id), str(job.id))
    logger.info(f"[analyze] enqueued index_developer for @{username}, job={job.id}, force={force}")

    return AnalyzeResponse(
        developer_id=str(developer.id),
        job_id=str(job.id),
        github_username=username,
        status=IndexStatus.pending,
        message=f"Indexing started for @{username}. Connect to /ws/{username} for progress.",
    )
