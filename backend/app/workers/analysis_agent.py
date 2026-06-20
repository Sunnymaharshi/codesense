"""
Celery task — runs the Phase 4 LangGraph analysis agent for a developer.
Triggered by on_indexing_complete after repos are indexed and embedded.
"""

import json
import logging

from sqlalchemy import select

from app.ai.agent.graph import run_analysis
from app.core.config import settings
from app.db.sync_session import SyncSessionLocal
from app.models.profile import Developer, Repo
from app.workers.celery_app import celery_app
from app.workers.redis_client import redis_client

logger = logging.getLogger(__name__)

_PROGRESS_CHANNEL = "codesense:progress:{username}"


def _make_publish(username: str):
    channel = _PROGRESS_CHANNEL.format(username=username)

    def _pub(payload: dict) -> None:
        try:
            redis_client.publish(channel, json.dumps(payload))
        except Exception:
            pass  # never let a Redis hiccup abort the analysis

    return _pub


@celery_app.task(bind=True, max_retries=1, default_retry_delay=30)
def analyse_developer(self, developer_id: int) -> None:
    """Load developer + repos from DB, run LangGraph agent, persist results."""
    with SyncSessionLocal() as db:
        developer = db.get(Developer, developer_id)
        if not developer:
            logger.error(f"[analyse_developer] developer {developer_id} not found")
            return

        username = developer.github_username
        repos = db.execute(
            select(Repo).where(Repo.developer_id == developer_id)
        ).scalars().all()

        repos_list = [
            {
                "name": r.name,
                "full_name": r.full_name,
                "primary_language": r.primary_language,
                "health_score": r.health_score,
                "stars": r.stars,
                "commit_count": r.commit_count,
                "has_tests": r.has_tests,
                "has_ci": r.has_ci,
                "last_commit_at": str(r.last_commit_at) if r.last_commit_at else None,
            }
            for r in repos
        ]

    if not repos_list:
        logger.warning(f"[analyse_developer] @{username} has no repos, skipping")
        return

    try:
        ai_persona, skill_scores = run_analysis(
            username=username,
            developer_id=developer_id,
            repos=repos_list,
            github_token=settings.GITHUB_TOKEN,
            groq_api_key=settings.GROQ_API_KEY,
            publish=_make_publish(username),
        )
    except Exception as exc:
        logger.exception(f"[analyse_developer] agent raised for @{username}: {exc}")
        raise self.retry(exc=exc)

    if not ai_persona and not skill_scores:
        logger.warning(f"[analyse_developer] @{username}: agent returned no results")
        return

    with SyncSessionLocal() as db:
        developer = db.get(Developer, developer_id)
        if developer:
            if ai_persona:
                developer.ai_persona = ai_persona
            if skill_scores:
                developer.skill_scores = skill_scores
            db.commit()
            logger.info(f"[analyse_developer] @{username}: persona + scores saved")
