"""
Phase 2 — real Celery fan-out implementation.
Replaces Phase 1 stubs.

Flow:
  index_developer (entry)
    → fan-out: celery.group of index_single_repo per repo
    → chord callback: on_indexing_complete
    → Redis PUBLISH at every step → WebSocket picks it up
"""

import json
import logging
from datetime import UTC, datetime

from celery import chord, group
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.sync_session import SyncSessionLocal
from app.models.profile import Developer, IndexingJob, IndexStatus, Repo
from app.services.github import GitHubClient
from app.services.health_score import (
    compute_health_score,
    compute_language_percentages,
    get_top_language,
)
from app.models.profile import ProfileSnapshot
from app.workers.celery_app import celery_app
from app.workers.redis_client import redis_client

logger = logging.getLogger(__name__)

PROGRESS_CHANNEL = "codesense:progress:{username}"


def _publish(username: str, payload: dict) -> None:
    channel = PROGRESS_CHANNEL.format(username=username)
    redis_client.publish(channel, json.dumps(payload))


# ─── Entry task ───────────────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def index_developer(self, developer_id: str, job_id: str) -> None:
    with SyncSessionLocal() as db:
        developer = db.get(Developer, developer_id)
        job = db.get(IndexingJob, job_id)
        if not developer or not job:
            logger.error("index_developer: developer or job not found")
            return

        username = developer.github_username
        logger.info(f"[index_developer] starting for @{username}")

        job.status = IndexStatus.running
        job.started_at = datetime.now(UTC)
        db.commit()

        _publish(username, {"type": "started", "message": f"Fetching repos for @{username}…"})

        try:
            github = GitHubClient(settings.GITHUB_TOKEN)
            repos_data = github.get_repos_sync(username)
        except Exception as exc:
            logger.exception(f"[index_developer] GitHub fetch failed: {exc}")
            job.status = IndexStatus.error
            job.error_message = str(exc)
            db.commit()
            _publish(username, {"type": "error", "message": str(exc)})
            raise self.retry(exc=exc)

        total = len(repos_data)
        job.repos_total = total
        db.commit()

        _publish(
            username,
            {
                "type": "progress",
                "repos_done": 0,
                "repos_total": total,
                "message": f"Indexing {total} repositories…",
            },
        )

        if total == 0:
            job.status = IndexStatus.done
            job.completed_at = datetime.now(UTC)
            db.commit()
            _publish(username, {"type": "done", "repos_done": 0, "repos_total": 0})
            return

        tasks = group(
            index_single_repo.s(developer_id, job_id, username, repo_data)
            for repo_data in repos_data
        )
        callback = on_indexing_complete.s(developer_id, job_id, username, total)
        chord(tasks)(callback)


# ─── Per-repo task ────────────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def index_single_repo(self, developer_id: str, job_id: str, username: str, repo_data: dict) -> dict:
    repo_name = repo_data.get("name", "unknown")
    logger.info(f"[index_single_repo] {username}/{repo_name}")

    try:
        github = GitHubClient(settings.GITHUB_TOKEN)

        languages = github.get_languages_sync(username, repo_name)
        commit_count = github.get_commit_count_sync(username, repo_name)
        signals = github.get_repo_signals_sync(username, repo_name)

        health_score, health_grade = compute_health_score(
            signals={
                "has_readme": signals["has_readme"],
                "has_tests": signals["has_tests"],
                "has_ci": signals["has_ci"],
                "has_docker": signals["has_docker"],
                "has_license": signals["has_license"],
                "has_contributing": signals.get("has_contributing", False),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "commit_count": commit_count,
            },
            last_commit_at=repo_data.get("pushed_at"),
        )

        language_percentages = compute_language_percentages(languages)
        primary_language = get_top_language(language_percentages) or repo_data.get("language")

        with SyncSessionLocal() as db:
            existing = db.execute(
                select(Repo).where(Repo.github_id == repo_data["id"])
            ).scalar_one_or_none()

            if existing:
                existing.description = repo_data.get("description")
                existing.primary_language = primary_language
                existing.all_languages = language_percentages
                existing.stars = repo_data.get("stargazers_count", 0)
                existing.forks = repo_data.get("forks_count", 0)
                existing.last_commit_at = repo_data.get("pushed_at")
                existing.health_score = health_score
                existing.health_grade = health_grade
                existing.has_readme = signals["has_readme"]
                existing.has_tests = signals["has_tests"]
                existing.has_ci = signals["has_ci"]
                existing.has_docker = signals["has_docker"]
                existing.has_license = signals["has_license"]
                existing.commit_count = commit_count
                existing.open_issues = repo_data.get("open_issues_count", 0)
                existing.name = repo_data["name"]
                existing.full_name = repo_data["full_name"]

                existing.github_url = repo_data.get("html_url")
                existing.homepage_url = repo_data.get("homepage")

                existing.is_fork = repo_data.get("fork", False)
                existing.is_archived = repo_data.get("archived", False)

                existing.github_created_at = repo_data.get("created_at")
                existing.github_pushed_at = repo_data.get("pushed_at")

                existing.watcher_count = repo_data.get("watchers_count", 0)
                existing.topics = repo_data.get("topics", [])
            else:
                repo = Repo(
                    developer_id=developer_id,
                    github_id=repo_data["id"],
                    name=repo_data["name"],
                    full_name=repo_data["full_name"],
                    description=repo_data.get("description"),
                    primary_language=primary_language,
                    all_languages=language_percentages,
                    stars=repo_data.get("stargazers_count", 0),
                    forks=repo_data.get("forks_count", 0),
                    last_commit_at=repo_data.get("pushed_at"),
                    health_score=health_score,
                    health_grade=health_grade,
                    has_readme=signals["has_readme"],
                    has_tests=signals["has_tests"],
                    has_ci=signals["has_ci"],
                    has_docker=signals["has_docker"],
                    has_license=signals["has_license"],
                    commit_count=commit_count,
                    open_issues=repo_data.get("open_issues_count", 0),
                    closed_issues=0,
                )
                db.add(repo)

            db.execute(
                update(IndexingJob)
                .where(IndexingJob.id == job_id)
                .values(repos_done=IndexingJob.repos_done + 1)
            )
            db.commit()

            job = db.get(IndexingJob, job_id)
            repos_done = job.repos_done if job else 0
            repos_total = job.repos_total if job else 0

        _publish(
            username,
            {
                "type": "progress",
                "repos_done": repos_done,
                "repos_total": repos_total,
                "repo": repo_name,
            },
        )

        return {"repo": repo_name, "health_score": health_score, "ok": True}
    except IntegrityError:
        logger.exception("Failed to save repo")
        raise
    except Exception as exc:
        logger.exception(f"[index_single_repo] failed for {repo_name}: {exc}")
        raise self.retry(exc=exc)


# ─── Chord callback ───────────────────────────────────────────────────────────


def _create_snapshot_sync(developer_id: str, db) -> None:
    from sqlalchemy import select

    repos = db.execute(select(Repo).where(Repo.developer_id == developer_id)).scalars().all()

    scores = [r.health_score for r in repos if r.health_score is not None]
    avg_health = round(sum(scores) / len(scores), 1) if scores else 0.0

    merged_languages: dict[str, int] = {}
    for repo in repos:
        if repo.all_languages:
            for lang, pct in repo.all_languages.items():
                merged_languages[lang] = merged_languages.get(lang, 0) + pct

    snapshot_data = {
        "total_repos": len(repos),
        "avg_health_score": avg_health,
        "total_stars": sum(r.stars or 0 for r in repos),
        "total_commits": sum(r.commit_count or 0 for r in repos),
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

    db.add(ProfileSnapshot(developer_id=developer_id, snapshot_data=snapshot_data, taken_at=datetime.now(UTC)))
    db.commit()


@celery_app.task
def on_indexing_complete(
    results: list, developer_id: str, job_id: str, username: str, total: int
) -> None:
    succeeded = sum(1 for r in results if r and r.get("ok"))
    logger.info(f"[on_indexing_complete] @{username}: {succeeded}/{total} repos indexed")

    with SyncSessionLocal() as db:
        job = db.get(IndexingJob, job_id)
        developer = db.get(Developer, developer_id)

        if job:
            job.status = IndexStatus.done
            job.completed_at = datetime.now(UTC)
            job.repos_done = succeeded

        if developer:
            developer.index_status = IndexStatus.done
            developer.indexed_at = datetime.now(UTC)

        db.commit()

        _create_snapshot_sync(developer_id, db)

    # Trigger Phase 4 analysis agent asynchronously — doesn't block indexing completion
    from app.workers.analysis_agent import analyse_developer
    analyse_developer.delay(developer_id)

    _publish(
        username,
        {
            "type": "done",
            "repos_done": succeeded,
            "repos_total": total,
        },
    )


# ─── Health check ─────────────────────────────────────────────────────────────


@celery_app.task
def health_check() -> str:
    return "ok"
