"""
CodeChunk model — stores code file chunks with pgvector embeddings.
Populated in Phase 3 when RAG pipeline is added.
"""

from datetime import datetime
from typing import Optional

from app.models.base import Base, utcnow
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# pgvector type — safe to import; the column won't be created
# until alembic migration runs on a postgres instance with the extension
try:
    from pgvector.sqlalchemy import Vector

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Source location
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # position within file

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    # The vector embedding (1536 dims for text-embedding-3-small)
    # This column is added in Phase 3 migration — safe to define here now
    if VECTOR_AVAILABLE:
        embedding: Mapped[Optional[object]] = mapped_column(Vector(1536))

    # Metadata for retrieval context
    language: Mapped[Optional[str]] = mapped_column(String(50))  # python, typescript…
    chunk_type: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # function, class, module

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    repo: Mapped["Repo"] = relationship("Repo", back_populates="code_chunks")

    def __repr__(self) -> str:
        return f"<CodeChunk repo={self.repo_id} file={self.file_path} chunk={self.chunk_index}>"
