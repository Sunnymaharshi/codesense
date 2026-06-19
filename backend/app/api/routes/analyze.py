"""
Phase 2 version of analyze.py.

Key change from Phase 1:
  - Indexing is now ASYNC via Celery — we enqueue the task and return immediately.
  - The synchronous indexing loop is REMOVED.
  - Frontend connects to WS /ws/{username} to track real-time progress.
"""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, GitHubDep
from app.models.profile import Developer, IndexingJob, IndexStatus
from app.schemas.profile import AnalyzeRequest, AnalyzeResponse
from app.workers.index_repo import index_developer

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_user(
    body: AnalyzeRequest,
    db: DbSession,
    github: GitHubDep,
) -> AnalyzeResponse:
    username = body.github_username.strip().lower()

    # Validate user exists on GitHub
    gh_user = await github.get_user(username)
    if not gh_user:
        raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found")

    # Upsert Developer row
    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()

    if developer:
        # Update profile fields from fresh GitHub data
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

    await db.flush()  # get developer.id

    # Create a fresh IndexingJob
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

    # Enqueue Celery fan-out — returns immediately
    index_developer.delay(str(developer.id), str(job.id))
    logger.info(f"[analyze] enqueued index_developer for @{username}, job={job.id}")

    return AnalyzeResponse(
        developer_id=str(developer.id),
        job_id=str(job.id),
        github_username=username,
        status=IndexStatus.pending,
        message=f"Indexing started for @{username}. Connect to /ws/{username} for progress.",
    )
