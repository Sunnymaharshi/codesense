"""
CodeChunk model — stores code file chunks with pgvector embeddings.
Populated in Phase 3 when RAG pipeline is added.

Note on the embedding column:
    Defined as Text for now. Phase 3 migration will ALTER it to vector(1536).
    The pgvector import is NOT done at model level to keep this file
    importable without the extension installed.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Source location
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    # Embedding stored as Text for Phase 1.
    # Phase 3 migration: ALTER COLUMN embedding TYPE vector(1536)
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata for retrieval context
    language: Mapped[Optional[str]] = mapped_column(String(50))
    chunk_type: Mapped[Optional[str]] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    repo: Mapped["Repo"] = relationship("Repo", back_populates="code_chunks")

    def __repr__(self) -> str:
        return f"<CodeChunk repo={self.repo_id} file={self.file_path} chunk={self.chunk_index}>"
