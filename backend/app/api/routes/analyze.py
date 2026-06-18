"""
POST /api/analyze

Accepts a GitHub username, indexes all public repos synchronously
(Phase 2 will move the heavy work to Celery), and returns job info.

Flow:
  1. Upsert Developer row
  2. Create IndexingJob
  3. Fetch repos from GitHub API
  4. For each repo: get languages + signals → compute health score → upsert Repo
  5. Mark job as done
  6. Return { developer_id, job_id, github_username }
"""

import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, GitHubDep
from app.models.profile import Developer, IndexingJob, IndexStatus, Repo
from app.schemas.profile import AnalyzeRequest, AnalyzeResponse
from app.services.health_score import (
    compute_health_score,
    get_top_language,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    db: DbSession,
    github: GitHubDep,
) -> AnalyzeResponse:
    username = body.github_username.lower().strip()

    # ── 1. Fetch GitHub user profile ─────────────────────
    try:
        gh_user = await github.get_user(username)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found")
        raise HTTPException(status_code=502, detail="GitHub API error")

    # ── 2. Upsert Developer ──────────────────────────────
    result = await db.execute(select(Developer).where(Developer.github_username == username))
    developer = result.scalar_one_or_none()

    joined_at = None
    if gh_user.get("created_at"):
        joined_at = datetime.fromisoformat(gh_user["created_at"].replace("Z", "+00:00"))

    if developer is None:
        developer = Developer(
            github_username=username,
            display_name=gh_user.get("name"),
            avatar_url=gh_user.get("avatar_url"),
            bio=gh_user.get("bio"),
            github_url=gh_user.get("html_url"),
            location=gh_user.get("location"),
            company=gh_user.get("company"),
            followers=gh_user.get("followers", 0),
            following=gh_user.get("following", 0),
            public_repos=gh_user.get("public_repos", 0),
            github_joined_at=joined_at,
            index_status=IndexStatus.running,
        )
        db.add(developer)
        await db.flush()  # get developer.id without committing
    else:
        # Update profile fields in case they've changed
        developer.display_name = gh_user.get("name")
        developer.avatar_url = gh_user.get("avatar_url")
        developer.bio = gh_user.get("bio")
        developer.location = gh_user.get("location")
        developer.company = gh_user.get("company")
        developer.followers = gh_user.get("followers", 0)
        developer.following = gh_user.get("following", 0)
        developer.public_repos = gh_user.get("public_repos", 0)
        developer.github_joined_at = joined_at
        developer.index_status = IndexStatus.running

    # ── 3. Create IndexingJob ────────────────────────────
    job = IndexingJob(
        developer_id=developer.id,
        status=IndexStatus.running,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    # ── 4. Fetch + index repos ───────────────────────────
    try:
        gh_repos = await github.get_repos(username)
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Failed to fetch repos from GitHub")

    job.repos_total = len(gh_repos)

    for gh_repo in gh_repos:
        repo_name = gh_repo["name"]
        owner = gh_repo["owner"]["login"]

        # Fetch languages + signals concurrently for each repo
        languages, signals, commit_count = await asyncio.gather(
            github.get_languages(owner, repo_name),
            github.get_repo_signals(owner, repo_name),
            github.get_commit_count(owner, repo_name),
        )

        # Parse last commit date
        last_commit_at = None
        pushed_at = gh_repo.get("pushed_at")
        if pushed_at:
            last_commit_at = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))

        created_at_gh = None
        if gh_repo.get("created_at"):
            created_at_gh = datetime.fromisoformat(gh_repo["created_at"].replace("Z", "+00:00"))

        # Compute health
        score, grade = compute_health_score(
            signals=signals,
            last_commit_at=last_commit_at,
        )

        # Upsert Repo
        result = await db.execute(select(Repo).where(Repo.github_id == gh_repo["id"]))
        repo = result.scalar_one_or_none()

        repo_data = dict(
            developer_id=developer.id,
            github_id=gh_repo["id"],
            name=repo_name,
            full_name=gh_repo["full_name"],
            description=gh_repo.get("description"),
            github_url=gh_repo.get("html_url"),
            homepage_url=gh_repo.get("homepage") or None,
            is_fork=gh_repo.get("fork", False),
            is_archived=gh_repo.get("archived", False),
            primary_language=gh_repo.get("language") or get_top_language(languages),
            all_languages=languages,
            language_history=None,  # Phase 4 agent will populate this
            stars=gh_repo.get("stargazers_count", 0),
            forks=gh_repo.get("forks_count", 0),
            open_issues=gh_repo.get("open_issues_count", 0),
            commit_count=commit_count,
            last_commit_at=last_commit_at,
            github_created_at=created_at_gh,
            github_pushed_at=last_commit_at,
            topics=gh_repo.get("topics", []),
            health_score=score,
            health_grade=grade,
            **signals,
        )

        if repo is None:
            repo = Repo(**repo_data)
            db.add(repo)
        else:
            for key, value in repo_data.items():
                setattr(repo, key, value)

        job.repos_done += 1

    # ── 5. Mark done ─────────────────────────────────────
    job.status = IndexStatus.done
    job.completed_at = datetime.now(timezone.utc)
    developer.index_status = IndexStatus.done
    developer.indexed_at = datetime.now(timezone.utc)

    await db.commit()

    return AnalyzeResponse(
        developer_id=developer.id,
        job_id=job.id,
        github_username=username,
        message=f"Indexed {job.repos_done} repos successfully",
    )
