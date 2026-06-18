"""
Celery tasks for indexing GitHub repos.

Phase 1: stub tasks — the logic already runs synchronously in analyze.py.
          These tasks exist so the worker starts cleanly without errors.

Phase 2: analyze.py will dispatch these tasks instead of doing the work
          inline, enabling real background processing + WebSocket progress.

Task chain:
    index_developer      → fans out to index_single_repo for each repo
    index_single_repo    → fetches code, signals, health score, saves to DB
"""

import logging
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.index_repo.index_developer")
def index_developer(self, developer_id: int, github_username: str) -> dict:
    """
    Entry point task — triggered by POST /analyze in Phase 2.

    Phase 1: stub that logs and returns immediately.
    Phase 2: will fetch all repos and fan out index_single_repo tasks
             using celery.group for parallel execution.

    Args:
        developer_id:    DB id of the Developer row
        github_username: GitHub username string
    """
    logger.info(
        "index_developer called — developer_id=%s username=%s "
        "(Phase 1 stub: work runs synchronously in analyze.py)",
        developer_id,
        github_username,
    )
    return {
        "developer_id": developer_id,
        "github_username": github_username,
        "status": "stub — Phase 2 will implement async fan-out",
    }


@celery_app.task(bind=True, name="app.workers.index_repo.index_single_repo")
def index_single_repo(self, repo_id: int, owner: str, repo_name: str) -> dict:
    """
    Per-repo task — Phase 2 will run one of these per repo in parallel.

    Phase 1: stub.
    Phase 2: will call GitHubClient, health scorer, embedder, and push
             progress updates over Redis pub/sub → WebSocket.

    Args:
        repo_id:   DB id of the Repo row
        owner:     GitHub username (repo owner)
        repo_name: repo name (not full_name)
    """
    logger.info(
        "index_single_repo called — repo_id=%s owner=%s repo=%s (Phase 1 stub)",
        repo_id,
        owner,
        repo_name,
    )
    return {
        "repo_id": repo_id,
        "full_name": f"{owner}/{repo_name}",
        "status": "stub — Phase 2 will implement",
    }


@celery_app.task(name="app.workers.index_repo.health_check")
def health_check() -> dict:
    """
    Simple task to verify the worker is alive.
    Call via: celery_app.send_task("app.workers.index_repo.health_check")
    Or: make shell-api → python -c "from app.workers.index_repo import health_check; print(health_check.delay().get())"
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
