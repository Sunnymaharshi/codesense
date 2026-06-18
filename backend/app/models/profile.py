"""
Developer and Repo models.

Developer  — one row per GitHub username analyzed
Repo       — one row per public repo, linked to Developer
IndexingJob — tracks background indexing progress
"""

import enum
from datetime import datetime
from typing import Optional

from app.models.base import Base, utcnow
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ─────────────────────────────────────────
# Enums
# ─────────────────────────────────────────


class IndexStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class HealthGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


# ─────────────────────────────────────────
# Developer
# ─────────────────────────────────────────


class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # GitHub identity
    github_username: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    company: Mapped[Optional[str]] = mapped_column(String(255))
    followers: Mapped[Optional[int]] = mapped_column(Integer)
    following: Mapped[Optional[int]] = mapped_column(Integer)
    public_repos: Mapped[Optional[int]] = mapped_column(Integer)
    github_joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # AI-generated fields (populated by LangGraph agent in Phase 4)
    ai_persona: Mapped[Optional[str]] = mapped_column(Text)  # the generated paragraph
    skill_scores: Mapped[Optional[dict]] = mapped_column(
        JSON
    )  # { backend: 88, frontend: 62, ... }

    # Indexing state
    index_status: Mapped[IndexStatus] = mapped_column(
        Enum(IndexStatus), default=IndexStatus.pending, nullable=False
    )
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    repos: Mapped[list["Repo"]] = relationship(
        "Repo", back_populates="developer", cascade="all, delete-orphan"
    )
    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(
        "IndexingJob", back_populates="developer", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["ProfileSnapshot"]] = relationship(
        "ProfileSnapshot", back_populates="developer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Developer @{self.github_username} [{self.index_status}]>"


# ─────────────────────────────────────────
# Repo
# ─────────────────────────────────────────


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    developer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # GitHub identity
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)  # owner/repo
    description: Mapped[Optional[str]] = mapped_column(Text)
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    homepage_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Language info
    primary_language: Mapped[Optional[str]] = mapped_column(String(100))
    all_languages: Mapped[Optional[dict]] = mapped_column(
        JSON
    )  # { "Python": 14200, "TypeScript": 3400 }
    language_history: Mapped[Optional[dict]] = mapped_column(
        JSON
    )  # { "2023": "Python", "2024": "TypeScript" }

    # GitHub stats
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    closed_issues: Mapped[int] = mapped_column(Integer, default=0)
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    watcher_count: Mapped[int] = mapped_column(Integer, default=0)

    # Dates
    last_commit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    github_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    github_pushed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Health signals (detected by health_score.py)
    has_readme: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tests: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ci: Mapped[bool] = mapped_column(Boolean, default=False)
    has_docker: Mapped[bool] = mapped_column(Boolean, default=False)
    has_license: Mapped[bool] = mapped_column(Boolean, default=False)
    has_contributing: Mapped[bool] = mapped_column(Boolean, default=False)

    # Computed health (by health_score.py)
    health_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0–100
    health_grade: Mapped[Optional[HealthGrade]] = mapped_column(
        Enum(HealthGrade)
    )  # A/B/C

    # Topics / tags from GitHub
    topics: Mapped[Optional[list]] = mapped_column(
        JSON
    )  # ["fastapi", "python", "docker"]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    developer: Mapped["Developer"] = relationship("Developer", back_populates="repos")
    code_chunks: Mapped[list["CodeChunk"]] = relationship(
        "CodeChunk", back_populates="repo", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Repo {self.full_name} [{self.health_grade}]>"


# ─────────────────────────────────────────
# IndexingJob
# ─────────────────────────────────────────


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    developer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[IndexStatus] = mapped_column(
        Enum(IndexStatus), default=IndexStatus.pending
    )
    repos_total: Mapped[int] = mapped_column(Integer, default=0)
    repos_done: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    developer: Mapped["Developer"] = relationship(
        "Developer", back_populates="indexing_jobs"
    )

    def __repr__(self) -> str:
        return f"<IndexingJob dev={self.developer_id} {self.repos_done}/{self.repos_total} [{self.status}]>"


# ─────────────────────────────────────────
# ProfileSnapshot
# ─────────────────────────────────────────


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    developer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Full profile state at time of snapshot
    snapshot_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    developer: Mapped["Developer"] = relationship(
        "Developer", back_populates="snapshots"
    )

    def __repr__(self) -> str:
        return f"<ProfileSnapshot dev={self.developer_id} at={self.taken_at}>"
