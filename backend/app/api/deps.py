"""
Shared FastAPI dependencies.
Inject these via Depends() in route functions.
"""

from typing import Annotated

from app.services.github import GitHubClient
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

# ── Database ─────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]

# ── GitHub client ─────────────────────────────────────────


def get_github_client() -> GitHubClient:
    return GitHubClient(token=settings.GITHUB_TOKEN)


GitHubDep = Annotated[GitHubClient, Depends(get_github_client)]
