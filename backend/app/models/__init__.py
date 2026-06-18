# Import all models here so Alembic can discover them for autogenerate
from app.models.base import Base
from app.models.embedding import CodeChunk
from app.models.llm_call import LLMCall
from app.models.profile import (
    Developer,
    HealthGrade,
    IndexingJob,
    IndexStatus,
    ProfileSnapshot,
    Repo,
)

__all__ = [
    "Base",
    "Developer",
    "Repo",
    "IndexingJob",
    "ProfileSnapshot",
    "IndexStatus",
    "HealthGrade",
    "CodeChunk",
    "LLMCall",
]
