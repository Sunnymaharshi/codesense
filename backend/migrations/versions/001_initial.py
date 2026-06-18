"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension first — required before any vector columns
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "developers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("github_username", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("bio", sa.Text()),
        sa.Column("github_url", sa.String(500)),
        sa.Column("location", sa.String(255)),
        sa.Column("company", sa.String(255)),
        sa.Column("followers", sa.Integer()),
        sa.Column("following", sa.Integer()),
        sa.Column("public_repos", sa.Integer()),
        sa.Column("github_joined_at", sa.DateTime(timezone=True)),
        sa.Column("ai_persona", sa.Text()),
        sa.Column("skill_scores", sa.JSON()),
        sa.Column(
            "index_status",
            sa.Enum("pending", "running", "done", "error", name="indexstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_username"),
    )
    op.create_index("ix_developers_github_username", "developers", ["github_username"])

    op.create_table(
        "repos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("github_url", sa.String(500)),
        sa.Column("homepage_url", sa.String(500)),
        sa.Column("is_fork", sa.Boolean(), server_default="false"),
        sa.Column("is_archived", sa.Boolean(), server_default="false"),
        sa.Column("primary_language", sa.String(100)),
        sa.Column("all_languages", sa.JSON()),
        sa.Column("language_history", sa.JSON()),
        sa.Column("stars", sa.Integer(), server_default="0"),
        sa.Column("forks", sa.Integer(), server_default="0"),
        sa.Column("open_issues", sa.Integer(), server_default="0"),
        sa.Column("closed_issues", sa.Integer(), server_default="0"),
        sa.Column("commit_count", sa.Integer(), server_default="0"),
        sa.Column("watcher_count", sa.Integer(), server_default="0"),
        sa.Column("last_commit_at", sa.DateTime(timezone=True)),
        sa.Column("github_created_at", sa.DateTime(timezone=True)),
        sa.Column("github_pushed_at", sa.DateTime(timezone=True)),
        sa.Column("has_readme", sa.Boolean(), server_default="false"),
        sa.Column("has_tests", sa.Boolean(), server_default="false"),
        sa.Column("has_ci", sa.Boolean(), server_default="false"),
        sa.Column("has_docker", sa.Boolean(), server_default="false"),
        sa.Column("has_license", sa.Boolean(), server_default="false"),
        sa.Column("has_contributing", sa.Boolean(), server_default="false"),
        sa.Column("health_score", sa.Integer()),
        sa.Column("health_grade", sa.Enum("A", "B", "C", name="healthgrade")),
        sa.Column("topics", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["developer_id"], ["developers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_id"),
    )
    op.create_index("ix_repos_developer_id", "repos", ["developer_id"])

    op.create_table(
        "indexing_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "error", name="indexstatus"),
            server_default="pending",
        ),
        sa.Column("repos_total", sa.Integer(), server_default="0"),
        sa.Column("repos_done", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["developer_id"], ["developers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indexing_jobs_developer_id", "indexing_jobs", ["developer_id"])

    op.create_table(
        "profile_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["developer_id"], ["developers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_profile_snapshots_developer_id", "profile_snapshots", ["developer_id"]
    )

    op.create_table(
        "code_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default="0"),
        sa.Column(
            "embedding", sa.Text()
        ),  # placeholder — Phase 3 migration replaces with vector(1536)
        sa.Column("language", sa.String(50)),
        sa.Column("chunk_type", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_chunks_repo_id", "code_chunks", ["repo_id"])

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default="0"),
        sa.Column("tokens_out", sa.Integer(), server_default="0"),
        sa.Column("cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("duration_ms", sa.Integer(), server_default="0"),
        sa.Column("langsmith_run_id", sa.String(255)),
        sa.Column("github_username", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("llm_calls")
    op.drop_table("code_chunks")
    op.drop_table("profile_snapshots")
    op.drop_table("indexing_jobs")
    op.drop_table("repos")
    op.drop_table("developers")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP TYPE IF EXISTS indexstatus")
    op.execute("DROP TYPE IF EXISTS healthgrade")
