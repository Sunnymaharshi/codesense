"""
Pydantic request/response schemas for profile routes.
Separate from SQLAlchemy models — these are the API contract shapes.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.profile import HealthGrade, IndexStatus

# ── Request ───────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    github_username: str

    model_config = {"str_strip_whitespace": True}


# ── Response ──────────────────────────────────────────────


class DeveloperResponse(BaseModel):
    id: int
    github_username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    github_url: Optional[str]
    location: Optional[str]
    company: Optional[str]
    followers: Optional[int]
    following: Optional[int]
    public_repos: Optional[int]
    github_joined_at: Optional[datetime]
    ai_persona: Optional[str]
    skill_scores: Optional[dict]
    index_status: str
    indexed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class RepoResponse(BaseModel):
    id: int
    github_id: int
    name: str
    full_name: str
    description: Optional[str]
    github_url: Optional[str]
    primary_language: Optional[str]
    all_languages: Optional[dict]
    stars: int
    forks: int
    open_issues: int
    commit_count: int
    last_commit_at: Optional[datetime]
    has_readme: bool
    has_tests: bool
    has_ci: bool
    has_docker: bool
    has_license: bool
    health_score: Optional[int]
    health_grade: HealthGrade
    topics: Optional[list]
    is_fork: bool
    is_archived: bool

    model_config = {"from_attributes": True}


class ProfileStatsResponse(BaseModel):
    total_repos: int
    avg_health_score: float
    top_language: Optional[str]
    language_percentages: dict[str, float]  # { "Python": 58.3, "TypeScript": 22.1 }
    grade_counts: dict[str, int]  # { "A": 8, "B": 14, "C": 12 }


class AnalyzeResponse(BaseModel):
    developer_id: int
    job_id: int
    github_username: str
    status: IndexStatus
    message: str


class ProfileResponse(BaseModel):
    developer: DeveloperResponse
    repos: list[RepoResponse]
    stats: ProfileStatsResponse


class CompareResponse(BaseModel):
    left: ProfileResponse
    right: ProfileResponse
